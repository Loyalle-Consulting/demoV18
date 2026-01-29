# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvBook(models.Model):
    _name = "rcv.book"
    _description = "Libro RCV SII"
    _order = "year desc, month desc"

    # =========================================================
    # CAMPOS
    # =========================================================

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )

    year = fields.Integer(
        string="Año",
        required=True,
    )

    month = fields.Integer(
        string="Mes",
        required=True,
    )

    rcv_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
        ],
        string="Tipo Libro",
        required=True,
    )

    state = fields.Selection(
        [
            ("imported", "Importado"),
            ("compared", "Comparado"),
            ("posted", "Facturas creadas"),
        ],
        string="Estado",
        default="imported",
        required=True,
    )

    line_ids = fields.One2many(
        "rcv.line",
        "book_id",
        string="Líneas RCV",
    )

    # =========================================================
    # ACCIÓN PRINCIPAL – OPCIÓN A DEFINITIVA
    # =========================================================
    def action_create_invoices(self):
        """
        Crea facturas en Contabilidad Odoo desde las líneas RCV
        que aún no tengan una factura asociada.
        """
        self.ensure_one()

        # Líneas pendientes de facturar
        lines_to_invoice = self.line_ids.filtered(
            lambda l: not l.account_move_id
        )

        if not lines_to_invoice:
            raise UserError(
                _("No existen líneas RCV pendientes de facturar.")
            )

        created_moves = self.env["account.move"]

        for line in lines_to_invoice:
            try:
                move = line._create_account_move_from_rcv()
                if move:
                    created_moves |= move
            except UserError:
                # Error funcional explícito → se muestra al usuario
                raise
            except Exception as e:
                raise UserError(
                    _("Error al crear factura para el folio %s:\n%s")
                    % (line.folio, str(e))
                )

        if not created_moves:
            raise UserError(
                _("No se creó ninguna factura nueva.")
            )

        # Actualizar estado del libro
        self.state = "posted"

        # =====================================================
        # RETORNO CORRECTO (ODOO 18)
        # =====================================================
        return {
            "type": "ir.actions.act_window",
            "name": _("Facturas creadas desde RCV"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "views": [
                (self.env.ref("account.view_move_tree").id, "tree"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
            "domain": [("id", "in", created_moves.ids)],
            "context": {
                "create": False,
                "default_move_type": (
                    "out_invoice"
                    if self.rcv_type == "sale"
                    else "in_invoice"
                ),
            },
        }

    # =========================================================
    # ACCIÓN: Conciliar con Contabilidad (NO TOCAR)
    # =========================================================
    def action_reconcile_with_accounting(self):
        for book in self:
            if not book.line_ids:
                raise UserError(
                    _("Este libro no tiene líneas para conciliar.")
                )
            book.state = "compared"
        return True
