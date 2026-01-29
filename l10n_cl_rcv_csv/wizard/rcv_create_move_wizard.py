# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvCreateMoveWizard(models.TransientModel):
    _name = "rcv.create.move.wizard"
    _description = "Crear facturas desde líneas RCV"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        readonly=True,
        default=lambda self: self.env.company,
    )

    line_ids = fields.Many2many(
        "rcv.line",
        string="Líneas RCV",
        readonly=True,
    )

    # ---------------------------------------------------------
    # DEFAULT_GET (CLAVE DE LA SOLUCIÓN)
    # ---------------------------------------------------------
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        ctx = self.env.context
        Line = self.env["rcv.line"]

        active_ids = ctx.get("active_ids")
        active_domain = ctx.get("active_domain")

        lines = Line.browse(active_ids) if active_ids else Line.search(active_domain or [])

        if not lines:
            return res

        res["line_ids"] = [(6, 0, lines.ids)]
        return res

    # ---------------------------------------------------------
    # ACCIÓN PRINCIPAL
    # ---------------------------------------------------------
    def action_create_moves(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("No hay líneas RCV seleccionadas."))

        created_moves = self.env["account.move"]

        for line in self.line_ids:
            if line.account_move_id:
                continue

            try:
                line.action_create_invoice()
            except Exception as e:
                line.match_state = "amount_diff"
                continue

            if line.account_move_id:
                created_moves |= line.account_move_id

        if not created_moves:
            raise UserError(_("No se creó ninguna factura nueva."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Facturas creadas desde RCV"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("id", "in", created_moves.ids)],
            "context": {"create": False},
        }
