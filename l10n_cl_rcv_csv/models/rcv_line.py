from odoo import models, fields


class RcvLine(models.Model):
    _name = "rcv.line"
    _description = "Línea RCV SII"
    _order = "document_date, folio"

    # =====================================================
    # RELACIONES
    # =====================================================

    book_id = fields.Many2one(
        "rcv.book",
        string="Libro RCV",
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        related="book_id.company_id",
        store=True,
        readonly=True,
    )

    # =====================================================
    # IDENTIFICACIÓN DOCUMENTO
    # =====================================================

    rcv_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
        ],
        string="Tipo Libro",
        required=True,
        index=True,
    )

    document_type = fields.Char(
        string="Tipo Documento",
        required=True,
    )

    folio = fields.Char(
        string="Folio",
        required=True,
    )

    partner_vat = fields.Char(
        string="RUT",
        index=True,
    )

    partner_name = fields.Char(
        string="Razón Social",
    )

    document_date = fields.Date(
        string="Fecha Documento",
    )

    # =====================================================
    # MONTOS
    # =====================================================

    net_amount = fields.Monetary(
        string="Neto",
    )

    tax_amount = fields.Monetary(
        string="IVA",
    )

    total_amount = fields.Monetary(
        string="Total",
        required=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    # =====================================================
    # CONCILIACIÓN CONTABLE
    # =====================================================

    match_state = fields.Selection(
        [
            ("not_found", "No existe en Odoo"),
            ("matched", "Cuadra"),
            ("amount_diff", "Diferencia de monto"),
            ("created", "Factura creada"),
        ],
        string="Estado Conciliación",
        default="not_found",
        index=True,
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
        readonly=True,
        ondelete="set null",
    )
