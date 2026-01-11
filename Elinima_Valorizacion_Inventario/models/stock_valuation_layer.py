
from odoo import models

class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    def unlink(self):
        return super().unlink()
