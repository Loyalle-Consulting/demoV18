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
        """Importación MOCK de datos RCV (sin SII real)"""

        self.ensure_one()

        RcvImport = self.env["l10n_cl.rcv.import"]
        RcvLine = self.env["l10n_cl.rcv.line"]

        # Buscar si ya existe una importación para el período
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

        mock_lines = []

        # Compras simuladas
        if self.import_type in ("purchase", "both"):
            mock_lines.append(
                {
                    "import_id": rcv_import.id,
                    "rcv_type": "purchase",
                    "document_type": "33",
                    "folio": "1234",
                    "partner_vat": "76.123.456-7",
                    "net_amount": 100000,
                    "tax_amount": 19000,
                    "total_amount": 119000,
                    "sii_status": "Aceptado",
                }
            )

        # Ventas simuladas
        if self.import_type in ("sale", "both"):
            mock_lines.append(
                {
                    "import_id": rcv_import.id,
                    "rcv_type": "sale",
                    "document_type": "33",
                    "folio": "5678",
                    "partner_vat": "96.654.321-0",
                    "net_amount": 200000,
                    "tax_amount": 38000,
                    "total_amount": 238000,
                    "sii_status": "Aceptado",
                }
            )

        # Crear líneas
        for line_vals in mock_lines:
            RcvLine.create(line_vals)

        # Marcar como importado
        rcv_import.state = "imported"

        # Cerrar wizard y volver al registro
        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n_cl.rcv.import",
            "res_id": rcv_import.id,
            "view_mode": "form",
            "target": "current",
        }
