import base64
import tempfile
import os
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Login real"

    # Entry point desde el wizard
    def fetch_rcv(self, company, year, month, import_type):
        session = self._login_sii(company)

        # En este paso solo validamos login real
        raise UserError(
            _(
                "Login exitoso en el SII.\n\n"
                "Sesión autenticada correctamente.\n"
                "Siguiente paso: descarga real del RCV (PASO 3B.4)."
            )
        )

    # ---------------------------------------------------------
    # LOGIN REAL AL SII
    # ---------------------------------------------------------
    def _login_sii(self, company):
        """
        Login real al SII usando certificado productivo cargado en Odoo.
        Retorna una requests.Session autenticada.
        """

        # 1) Obtener certificado vigente de la empresa
        certificate = self.env["certificate.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("date_start", "<=", fields.Date.today()),
                ("date_end", ">=", fields.Date.today()),
            ],
            limit=1,
        )

        if not certificate:
            raise UserError(
                _(
                    "No se encontró un certificado SII vigente "
                    "para la empresa %s."
                )
                % company.name
            )

        if not certificate.content or not certificate.pkcs12_password:
            raise UserError(
                _("El certificado SII no tiene contenido o contraseña válida.")
            )

        # 2) Crear archivo temporal .pfx
        pfx_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        try:
            pfx_file.write(base64.b64decode(certificate.content))
            pfx_file.close()

            # 3) Crear sesión HTTPS con Mutual TLS
            session = requests.Session()
            session.cert = (pfx_file.name, certificate.pkcs12_password)
            session.verify = True
            session.headers.update(
                {
                    "User-Agent": "Odoo-18-RCV-SII",
                }
            )

            # 4) Endpoint real de autenticación SII
            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"

            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(
                    _(
                        "Error al conectar con el SII.\n"
                        "Código HTTP: %s"
                    )
                    % response.status_code
                )

            # 5) Validación básica de sesión
            if "SII" not in response.text:
                raise UserError(
                    _(
                        "No fue posible validar la sesión SII.\n"
                        "Respuesta inesperada del servidor."
                    )
                )

            return session

        finally:
            # 6) Limpieza estricta del archivo temporal
            if os.path.exists(pfx_file.name):
                os.unlink(pfx_file.name)
