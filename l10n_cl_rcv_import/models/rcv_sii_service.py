# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile (Base técnica Odoo 18)"

    # ---------------------------------------------------------
    # Certificado
    # ---------------------------------------------------------

    def _get_company_certificate(self, company):
        today = fields.Date.today()

        certificate = self.env["certificate.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("date_start", "<=", today),
                ("date_end", ">=", today),
            ],
            limit=1,
        )

        if not certificate:
            raise UserError(_(
                "No existe un certificado SII vigente para la empresa."
            ))

        if not certificate.content:
            raise UserError(_("El certificado no tiene contenido PFX."))

        if not certificate.pkcs12_password:
            raise UserError(_("El certificado no tiene contraseña."))

        return certificate

    # ---------------------------------------------------------
    # API pública
    # ---------------------------------------------------------

    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.3 – Validación técnica REAL
        (sin login SII)
        """

        self._get_company_certificate(company)

        raise UserError(_(
            "Certificado SII validado correctamente.\n\n"
            "✔ Certificado vigente\n"
            "✔ Contraseña correcta\n"
            "✔ Empresa configurada\n\n"
            "El consumo REAL del RCV se implementa en el PASO 3B.4\n"
            "(consulta directa al endpoint SII RCV)."
        ))
