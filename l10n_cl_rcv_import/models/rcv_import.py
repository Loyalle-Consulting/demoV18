from odoo import models, fields
from odoo.exceptions import UserError
from ..services.sii_rcv_service import SiiRcvService


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

    # ---------------------------------------------------------------------
    # IMPORTAR DESDE SII (REAL)
    # ---------------------------------------------------------------------
    def action_import_rcv(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Este RCV ya fue importado.")

            service = SiiRcvService(self.env, rec.company_id)

            result = service.get_rcv(
                year=rec.year,
                month=int(rec.month),
            )

            # 🔴 En PASO 3B.3 se procesan datos reales
            # Por ahora solo marcamos estado
            rec.state = "imported"
