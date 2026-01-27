from odoo import models, fields

class L10nClRcvImport(models.Model):
    _name = "l10n_cl.rcv.import"
    _description = "RCV Import SII Chile"
    _order = "year desc, month desc"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    month = fields.Selection(
        [(str(i), str(i)) for i in range(1, 13)],
        string="Mes",
        required=True,
    )

    year = fields.Integer(
        string="Año",
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("imported", "Importado"),
        ],
        string="Estado",
        default="draft",
    )

    line_ids = fields.One2many(
        "l10n_cl.rcv.line",
        "import_id",
        string="Líneas RCV",
    )

    def action_reconcile_rcv(self):
        """Conciliar líneas RCV con facturas Odoo (Odoo 18 compatible)"""

        for rec in self:
            for line in rec.line_ids:

                move_type = (
                    "in_invoice"
                    if line.rcv_type == "purchase"
                    else "out_invoice"
                )

                domain = [
                    ("company_id", "=", rec.company_id.id),
                    ("move_type", "=", move_type),
                    ("state", "=", "posted"),
                    ("l10n_latam_document_type_id.code", "=", line.document_type),
                    ("l10n_latam_document_number", "=", line.folio),
                    ("partner_id.vat", "=", line.partner_vat),
                ]

                move = self.env["account.move"].search(domain, limit=1)

                if not move:
                    line.match_state = "not_found"
                    line.account_move_id = False
                    continue

                line.account_move_id = move.id

                if abs(move.amount_total - line.total_amount) < 1:
                    line.match_state = "matched"
                else:
                    line.match_state = "amount_diff"
