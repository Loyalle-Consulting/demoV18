from odoo import models, fields


class L10nClRcvImport(models.Model):
    _name = "l10n_cl.rcv.import"
    _description = "RCV Import SII Chile"
    _order = "year desc, month desc"

    # =====================
    # Campos principales
    # =====================

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

    # =====================
    # Utilidades
    # =====================

    def _normalize_rut(self, rut):
        """
        Normaliza RUT chileno para comparación:
        - elimina prefijo CL
        - elimina puntos
        - conserva formato XXXXXXXX-X
        NO valida dígito verificador (eso lo hace Odoo en res.partner)
        """
        if not rut:
            return False

        rut = rut.upper().replace("CL", "")
        rut = rut.replace(".", "").strip()

        return rut

    # =====================
    # Conciliación contable
    # =====================

    def action_reconcile_rcv(self):
        """
        Conciliar líneas RCV con facturas Odoo
        Compatible con Odoo 18 + localización chilena
        """

        AccountMove = self.env["account.move"]

        for rec in self:
            for line in rec.line_ids:

                # Tipo de documento contable
                move_type = (
                    "in_invoice"
                    if line.rcv_type == "purchase"
                    else "out_invoice"
                )

                normalized_rut = self._normalize_rut(line.partner_vat)

                domain = [
                    ("company_id", "=", rec.company_id.id),
                    ("move_type", "=", move_type),
                    ("state", "=", "posted"),
                    ("l10n_latam_document_type_id.code", "=", line.document_type),
                    ("l10n_latam_document_number", "=", line.folio),
                ]

                # Comparación por RUT solo si viene informado
                if normalized_rut:
                    domain.append(
                        ("partner_id.vat", "ilike", normalized_rut)
                    )

                move = AccountMove.search(domain, limit=1)

                if not move:
                    line.match_state = "not_found"
                    line.account_move_id = False
                    continue

                line.account_move_id = move.id

                # Comparación de montos
                if abs(move.amount_total - line.total_amount) < 1:
                    line.match_state = "matched"
                else:
                    line.match_state = "amount_diff"
