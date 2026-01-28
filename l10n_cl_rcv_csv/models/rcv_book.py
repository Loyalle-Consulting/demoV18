from odoo import models, fields


class RcvBook(models.Model):
    _name = "rcv.book"
    _description = "Libro RCV SII"
    _order = "year desc, month desc"

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
