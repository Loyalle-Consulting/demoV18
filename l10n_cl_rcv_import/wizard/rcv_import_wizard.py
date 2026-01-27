from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvImportWizard(models.TransientModel):
    _name = "l10n_cl.rcv.import.wizard"
    _description = "RCV Import Wizard"

    # =====================
    # Campos
    # =====================

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

    # =====================
    # Acción principal
    # =====================

    def action_import_rcv(self):
        """
        Importa RCV REAL desde SII (solo lectura)
        Reemplaza completamente el MOCK
        """

        self.ensure_one()

        RcvImport = self.env["l10n_cl.rcv.import"]
        RcvLine = self.env["l10n_cl.rcv.line"]
        SiiService = self.env["l10n_cl.rcv.sii.service"]

        # Buscar o crear importación para el período
        rcv_import = RcvImport.search(
            [
                ("company_id", "=", self.company_id.id),
                ("month", "=", self.month),
                ("year", "=", self.year),
            ],
            limit=1,
        )

        if not rcv_import:
            rcv_import = RcvImport.create(
                {
                    "company_id": self.company_id.id,
                    "month": self.month,
                    "year": self.year,
                }
            )

        # Limpiar líneas anteriores (reimportación)
        rcv_import.line_ids.unlink()

        # =====================
        # Llamada REAL al servicio SII
        # =====================

        try:
            rcv_data = SiiService.fetch_rcv(
                company=self.company_id,
                year=int(self.year),
                month=int(self.month),
                import_type=self.import_type,
            )
        except Exception as e:
            raise UserError(
                _("Error al obtener RCV desde SII:\n%s") % str(e)
            )

        # =====================
        # Creación de líneas RCV
        # =====================

        for line in rcv_data:
            RcvLine.create(
                {
                    "import_id": rcv_import.id,
                    "rcv_type": line.get("rcv_type"),
                    "document_type": line.get("document_type"),
                    "folio": line.get("folio"),
                    "partner_vat": line.get("partner_vat"),
                    "net_amount": line.get("net"),
                    "tax_amount": line.get("tax"),
                    "total_amount": line.get("total"),
                    "sii_status": line.get("sii_status"),
                }
            )

        rcv_import.state = "imported"

        # Volver al formulario
        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n_cl.rcv.import",
            "res_id": rcv_import.id,
            "view_mode": "form",
            "target": "current",
        }
