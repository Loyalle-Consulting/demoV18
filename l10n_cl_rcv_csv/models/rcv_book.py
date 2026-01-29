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
    # ACCIÓN: CREAR FACTURAS (YA FUNCIONAL)
    # =========================================================
    def action_create_invoices(self):
        self.ensure_one()

        lines_to_invoice = self.line_ids.filtered(
            lambda l: not l.account_move_id
        )

        if not lines_to_invoice:
            raise UserError(
                _("No existen líneas RCV pendientes de facturar.")
            )

        created_moves = self.env["account.move"]

        for line in lines_to_invoice:
            move = line._create_account_move_from_rcv()
            if move:
                created_moves |= move

        if not created_moves:
            raise UserError(_("No se creó ninguna factura nueva."))

        self.state = "posted"

        return {
            "type": "ir.actions.act_window",
            "name": _("Documentos creados desde RCV"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "views": [
                (self.env.ref("account.view_move_tree").id, "tree"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
            "domain": [("id", "in", created_moves.ids)],
            "context": {"create": False},
        }

    # =========================================================
    # ACCIÓN: CONCILIAR / REESTABLECER ESTADO (AJUSTADA)
    # =========================================================
    def action_reconcile_with_accounting(self):
        """
        Si los documentos contables ya no existen,
        se restablece el libro y sus líneas a estado importado.
        """
        for book in self:
            if not book.line_ids:
                raise UserError(
                    _("Este libro no tiene líneas para conciliar.")
                )

            # ¿Existen documentos contables reales?
            existing_moves = book.line_ids.mapped("account_move_id").filtered(
                lambda m: m.exists()
            )

            if not existing_moves:
                # 🔁 RESTABLECER COMPLETAMENTE
                book.line_ids.write({
                    "account_move_id": False,
                    "match_state": "not_found",
                })
                book.state = "imported"
            else:
                # Estado normal de conciliación
                book.state = "compared"

        return True
