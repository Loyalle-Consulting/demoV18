from odoo import models, fields

class L10nClRcvLine(models.Model):
    _name = "l10n_cl.rcv.line"
    _description = "RCV Line"

    import_id = fields.Many2one(
        "l10n_cl.rcv.import",
        string="Importación",
        required=True,
        ondelete="cascade",
    )

    rcv_type = fields.Selection(
        [
            ("purchase", "Compra"),
            ("sale", "Venta"),
        ],
        string="Tipo",
        required=True,
    )

    document_type = fields.Char(string="Tipo Documento")
    folio = fields.Char(string="Folio")
    partner_vat = fields.Char(string="RUT")

    net_amount = fields.Monetary(string="Neto")
    tax_amount = fields.Monetary(string="IVA")
    total_amount = fields.Monetary(string="Total")

    currency_id = fields.Many2one(
        "res.currency",
        related="import_id.company_id.currency_id",
        store=True,
    )

    sii_status = fields.Char(string="Estado SII")

    account_move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
    )
