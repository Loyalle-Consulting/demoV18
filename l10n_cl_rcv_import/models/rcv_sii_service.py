# -*- coding: utf-8 -*-

import logging

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile (Odoo 18)"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_company_certificate(self, company):
        """
        Obtiene certificado SII válido desde Odoo
        """
        certificate = company.l10n_cl_certificate_ids.filtered(
            lambda c: c.state == "valid"
        )[:1]

        if not certificate:
            raise UserError(_(
                "La empresa no tiene un certificado SII válido.\n"
                "Configure uno en Ajustes > Certificados."
            ))

        return certificate

    def _login_sii(self, company):
        """
        Login REAL al SII usando stack oficial Odoo 18
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
        PASO 3B.3 – Login REAL confirmado
        PASO 3B.4 – Parseo se implementa después
        """
        session = self._login_sii(company)

        # Confirmación controlada
        raise UserError(_(
            "Login exitoso en el SII.\n\n"
            "Certificado y sesión TLS válidos.\n"
            "Siguiente paso: descarga real del RCV (PASO 3B.4)."
        ))
