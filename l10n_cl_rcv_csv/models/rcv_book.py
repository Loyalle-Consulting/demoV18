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

    year = fields.Integer(string="Año", required=True)
    month = fields.Integer(string="Mes", required=True)

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
    # ACCIÓN: CREAR FACTURAS (PROCESO PURO – SIN VISTAS)
    # =========================================================
    def action_create_invoices(self):
        """
        Crea facturas / notas de crédito desde las líneas RCV
        que aún no tengan documento contable asociado.
        """
        self.ensure_one()

        lines_to_invoice = self.line_ids.filtered(
            lambda l: not l.account_move_id
        )

        if not lines_to_invoice:
            raise UserError(
                _("No existen líneas RCV pendientes de facturar.")
            )

        created = False

        for line in lines_to_invoice:
            move = line._create_account_move_from_rcv()
            if move:
                created = True

        if not created:
            raise UserError(
                _("No se creó ningún documento nuevo.")
            )

        # Estado final del libro
        self.state = "posted"

        # 🔑 IMPORTANTE:
        # No retornamos acciones de vista para evitar errores JS
        return True

    # =========================================================
    # ACCIÓN: CONCILIAR / REESTABLECER ESTADO
    # =========================================================
    def action_reconcile_with_accounting(self):
        """
        - Si NO existen documentos contables → vuelve a IMPORTADO
        - Si existen → estado COMPARADO
        """
        for book in self:
            if not book.line_ids:
                raise UserError(
                    _("Este libro no tiene líneas para conciliar.")
                )

            existing_moves = book.line_ids.mapped(
                "account_move_id"
            ).filtered(lambda m: m.exists())

            if not existing_moves:
                # 🔁 Reproceso completo permitido
                book.line_ids.write({
                    "account_move_id": False,
                    "match_state": "not_found",
                })
                book.state = "imported"
            else:
                book.state = "compared"

        return True
