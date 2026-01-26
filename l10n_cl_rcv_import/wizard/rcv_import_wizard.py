from odoo import models, fields

class L10nClRcvImportWizard(models.TransientModel):
    _name = "l10n_cl.rcv.import.wizard"
    _description = "RCV Import Wizard"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
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

    import_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
            ("both", "Ambos"),
        ],
        string="Tipo de Importación",
        default="both",
        required=True,
    )

    def action_import_rcv(self):
        # Placeholder seguro para Odoo 18
        return True