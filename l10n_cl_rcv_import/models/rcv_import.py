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
            ("error", "Error"),
        ],
        string="Estado",
        default="draft",
    )

    line_ids = fields.One2many(
        "l10n_cl.rcv.line",
        "import_id",
        string="Líneas RCV",
    )