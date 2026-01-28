# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvCreateMoveWizard(models.TransientModel):
    _name = "rcv.create.move.wizard"
    _description = "Crear facturas desde líneas RCV"

    # ---------------------------------------------------------
    # CAMPOS
    # ---------------------------------------------------------

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )

    line_ids = fields.Many2many(
        "rcv.line",
        string="Líneas RCV",
        readonly=True,
    )

    # ---------------------------------------------------------
    # DEFAULTS
    # ---------------------------------------------------------

    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            res["line_ids"] = [(6, 0, active_ids)]

        return res

    # ---------------------------------------------------------
    # ACCIÓN PRINCIPAL
    # ---------------------------------------------------------

    def action_create_moves(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("No hay líneas RCV seleccionadas."))

        created_moves = self.env["account.move"]

        # ⚠️ Forzar compañía (crítico)
        lines = self.line_ids.with_company(self.company_id)

        for line in lines:

            # Evitar duplicados
            if line.account_move_id:
                continue

            try:
                line.action_create_invoice()
            except UserError:
                # Error funcional → marcar y continuar
                line.match_state = "amount_diff"
                continue
            except Exception:
                # Error técnico → no ocultar completamente
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
