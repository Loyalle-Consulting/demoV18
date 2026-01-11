from odoo import models
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_reset_to_draft(self):
        for picking in self:
            if picking.state != 'done':
                raise UserError("El movimiento debe estar en estado 'Hecho' para restablecerlo.")

            # 🔓 Desbloquear si es necesario
            if picking.is_locked:
                picking.is_locked = False

            # ✅ Revertir cantidad procesada en move_line_ids (Odoo 18 usa 'quantity')
            picking.move_line_ids.filtered(lambda l: l.quantity > 0).write({'quantity': 0})

            # Volver a estado borrador
            picking.move_ids.write({'state': 'draft'})
            picking.write({'state': 'draft'})

            picking.message_post(body="Transferencia restablecida a borrador manualmente.")
