from odoo import models, fields


class RcvBook(models.Model):
    _name = "rcv.book"
    _description = "Libro RCV SII"
    _order = "year desc, month desc"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    year = fields.Integer(required=True)
    month = fields.Integer(required=True)

    rcv_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
        ],
        required=True,
    )

    state = fields.Selection(
        [
            ("imported", "Importado"),
            ("compared", "Comparado"),
            ("posted", "Facturas creadas"),
        ],
        default="imported",
    )

    line_ids = fields.One2many(
        "rcv.line",
        "book_id",
        string="Líneas RCV",
    )