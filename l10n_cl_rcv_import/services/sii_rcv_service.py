from odoo import fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SiiRcvService:
    """Servicio base para obtención de RCV desde SII (Odoo 18 Enterprise)"""

    def __init__(self, env, company):
        self.env = env
        self.company = company
        self.certificate = self._get_valid_certificate()

    # -------------------------------------------------------------------------
    # CERTIFICADO
    # -------------------------------------------------------------------------
    def _get_valid_certificate(self):
        """Obtiene certificado válido desde modelo estándar de Odoo"""

        cert = self.env["certificate.certificate"].search([
            ("company_id", "=", self.company.id),
            ("date_start", "<=", fields.Date.today()),
            ("date_end", ">=", fields.Date.today()),
        ], limit=1)

        if not cert:
            raise UserError(
                "La empresa no tiene un certificado digital SII válido cargado.\n"
                "Debe cargar un certificado vigente en Ajustes > Certificados."
            )

        _logger.info(
            "RCV SII: usando certificado %s (vigente hasta %s)",
            cert.name,
            cert.date_end,
        )

        return cert

    # -------------------------------------------------------------------------
    # LOGIN SII (PLACEHOLDER REAL)
    # -------------------------------------------------------------------------
    def login(self):
        """
        Login SII usando certificado.
        (Aquí se integrará requests + mutual TLS)
        """

        # EJEMPLO DE DATOS DISPONIBLES
        cert_content = self.certificate.content
        cert_password = self.certificate.pkcs12_password

        if not cert_content or not cert_password:
            raise UserError(
                "El certificado no contiene información completa "
                "(archivo o contraseña)."
            )

        _logger.info("RCV SII: login preparado correctamente")

        # Placeholder login real
        return True

    # -------------------------------------------------------------------------
    # OBTENER RCV
    # -------------------------------------------------------------------------
    def get_rcv(self, year, month):
        """
        Obtiene RCV desde SII (REAL en siguientes pasos)
        """

        self.login()

        _logger.info(
            "RCV SII: solicitando RCV %s/%s para empresa %s",
            month,
            year,
            self.company.name,
        )

        # 🔴 AQUÍ VA LA LLAMADA REAL A SII
        # Por ahora devolvemos estructura simulada
        return {
            "purchases": [],
            "sales": [],
        }
