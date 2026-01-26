from odoo import models, fields

class L10nClRcvLog(models.Model):
    _name = "l10n_cl.rcv.log"
    _description = "RCV SII Log"

    import_id = fields.Many2one(
        "l10n_cl.rcv.import",
        string="Importación",
        ondelete="cascade",
    )

    message = fields.Text(string="Mensaje")

    level = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Advertencia"),
            ("error", "Error"),
        ],
        default="info",
        string="Nivel",
    )