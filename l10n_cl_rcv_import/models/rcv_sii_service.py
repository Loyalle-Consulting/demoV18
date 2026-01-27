# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile (Odoo 18 Enterprise)"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_company_certificate(self, company):
        """
        Obtiene certificado SII vigente según fechas (Odoo 18)
        """
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
                "La empresa no tiene un certificado SII vigente.\n\n"
                "Revise:\n"
                "Ajustes > Certificados\n"
                "- Empresa correcta\n"
                "- Fecha de validez\n"
                "- Contraseña correcta"
            ))

        if not certificate.content or not certificate.pkcs12_password:
            raise UserError(_(
                "El certificado SII no tiene contenido o contraseña.\n"
                "Revise la configuración del certificado."
            ))

        return certificate

    def _login_sii(self, company):
        """
        Login REAL SII usando stack oficial Odoo 18
        """
        certificate = self._get_company_certificate(company)

        try:
            session = certificate._get_sii_session()
        except Exception as e:
            _logger.exception("Error autenticando con SII")
            raise UserError(_(
                "No fue posible autenticar con el SII.\n\n%s"
            ) % str(e))

        return session

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.3 – Login SII REAL confirmado
        """
        session = self._login_sii(company)

        # Confirmación explícita (controlada)
        raise UserError(_(
            "Login exitoso en el SII.\n\n"
            "✔ Certificado válido\n"
            "✔ Contraseña correcta\n"
            "✔ Sesión TLS establecida\n\n"
            "Siguiente paso: descarga REAL del RCV (PASO 3B.4)."
        ))
