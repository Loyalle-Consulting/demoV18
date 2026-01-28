from odoo import models, fields


class RcvLine(models.Model):
    _name = "rcv.line"
    _description = "Línea RCV SII"
    _order = "invoice_date, folio"

    book_id = fields.Many2one(
        "rcv.book",
        string="Libro RCV",
        required=True,
        ondelete="cascade",
    )

    # ===============================
    # Datos documento SII
    # ===============================
    tipo_dte = fields.Char(
        string="Tipo DTE",
        help="Código DTE según SII (33, 34, 61, etc.)",
    )

    folio = fields.Char(
        string="Folio",
        required=True,
    )

    partner_vat = fields.Char(
        string="RUT",
    )

    partner_name = fields.Char(
        string="Razón Social",
    )

    invoice_date = fields.Date(
        string="Fecha Documento",
    )

    # ===============================
    # Montos
    # ===============================
    net_amount = fields.Monetary(
        string="Neto",
    )

    tax_amount = fields.Monetary(
        string="IVA",
    )

    total_amount = fields.Monetary(
        string="Total",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # ===============================
    # Conciliación
    # ===============================
    match_state = fields.Selection(
        [
            ("not_found", "No existe en Odoo"),
            ("matched", "Cuadra"),
            ("amount_diff", "Diferencia de monto"),
            ("created", "Factura creada"),
        ],
        string="Estado Conciliación",
        default="not_found",
        required=True,
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
        readonly=True,
    )
