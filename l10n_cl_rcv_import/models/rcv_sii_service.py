import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Login estable Odoo 18"


    # =========================================================
    # ENTRY POINT DESDE EL WIZARD
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        Punto único de entrada.
        NO ramifica flujos → evita loops infinitos.
        """

        self._login_sii(company)

        raise UserError(
            _(
                "✔ Certificado SII validado correctamente\n"
                "✔ Certificado vigente\n"
                "✔ Contraseña correcta\n"
                "✔ Autenticación TLS exitosa\n\n"
                "El consumo REAL del RCV se implementa en el PASO 3B.5\n"
                "(consulta directa al endpoint oficial del SII RCV)."
            )
        )


    # =========================================================
    # LOGIN REAL SII (CAMPO CORRECTO pkcs12_password)
    # =========================================================
    def _login_sii(self, company):

        certificate = self.env["certificate.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("date_start", "<=", fields.Date.today()),
                ("date_end", ">=", fields.Date.today()),
            ],
            limit=1,
        )

        if not certificate:
            raise UserError(_("No existe certificado SII vigente."))

        if not certificate.content:
            raise UserError(_("El certificado no tiene contenido PFX."))

        if not certificate.pkcs12_password:
            raise UserError(_("El certificado no tiene contraseña definida."))

        pfx_path = tempfile.mktemp(suffix=".pfx")
        cert_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            # Guardar archivo PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Extraer certificado público
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-clcerts", "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            # Extraer clave privada
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts", "-nodes",
                "-out", key_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            # Crear sesión TLS
            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII"
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(
                    _("Error HTTP al conectar con el SII: %s")
                    % response.status_code
                )

            if "SII" not in response.text:
                raise UserError(_("La respuesta del SII no es válida."))

            return session

        except subprocess.CalledProcessError:
            raise UserError(
                _("Error al convertir el certificado PFX. "
                  "Verifique la contraseña del certificado.")
            )

        finally:
            for path in (pfx_path, cert_path, key_path):
                if os.path.exists(path):
                    os.unlink(path)
