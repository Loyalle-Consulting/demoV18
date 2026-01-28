from odoo import models, fields


class RcvLine(models.Model):
    _name = "rcv.line"
    _description = "Línea RCV SII"
    _order = "invoice_date, folio"

    book_id = fields.Many2one(
        "rcv.book",
        required=True,
        ondelete="cascade",
    )

    tipo_dte = fields.Char()
    folio = fields.Char()

    partner_vat = fields.Char(string="RUT")
    partner_name = fields.Char(string="Razón Social")

    invoice_date = fields.Date()

    net_amount = fields.Monetary()
    tax_amount = fields.Monetary()
    total_amount = fields.Monetary()

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    # Conciliación
    match_state = fields.Selection(
        [
            ("not_found", "No existe en Odoo"),
            ("matched", "Cuadra"),
            ("amount_diff", "Diferencia de monto"),
            ("created", "Factura creada"),
        ],
        default="not_found",
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
        readonly=True,
    )