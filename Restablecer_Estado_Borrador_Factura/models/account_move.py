from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    x_from_editar_factura_reset = fields.Boolean(default=False)

    def action_editar_factura_reset_draft(self):
        allowed_types = ("out_invoice","out_refund","in_invoice","in_refund")
        for move in self:
            if move.state != "posted":
                continue
            if move.move_type not in allowed_types:
                continue
            original_state = move.l10n_cl_dte_status
            move.edi_document_ids.unlink()
            move.write({
                "state": "draft",
                "x_from_editar_factura_reset": True,
                "l10n_cl_dte_status": original_state,
                "posted_before": False,
                "edi_state": False,
            })
            if move.reversed_entry_id:
                move.reversed_entry_id = False

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.x_from_editar_factura_reset:
                move.x_from_editar_factura_reset = False
        return res
