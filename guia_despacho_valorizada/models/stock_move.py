from odoo import api, fields, models

class StockMove(models.Model):
    _inherit = "stock.move"

    price_unit = fields.Float(string="Precio Unitario")

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for m in moves:
            if m.sale_line_id and not m.price_unit:
                m.price_unit = m.sale_line_id.price_unit
        return moves

    def write(self, vals):
        res = super().write(vals)
        if "sale_line_id" in vals:
            for m in self:
                if m.sale_line_id and not m.price_unit:
                    m.price_unit = m.sale_line_id.price_unit
        return res