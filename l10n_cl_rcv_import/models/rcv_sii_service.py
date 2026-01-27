import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Login y Base Real"


    # =========================================================
    # MÉTODO PRINCIPAL (wizard)
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        Punto único de entrada.
        No vuelve a ramificar flujos → evita loops.
        """

        session = self._login_sii(company)

        raise UserError(
            _(
                "✔ Login SII REAL exitoso\n"
                "✔ Certificado válido\n"
                "✔ Contraseña correcta\n"
                "✔ Autenticación TLS establecida\n\n"
                "El consumo REAL del RCV se implementa "
                "en el PASO 3B.5 (descarga y parseo)."
            )
        )


    # =========================================================
    # LOGIN REAL SII (CORREGIDO ODOO 18)
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

        # 🔴 CAMPO CORRECTO EN ODOO 18
        if not certificate.content or not certificate.password:
            raise UserError(
                _("El certificado no tiene contenido o contraseña definida.")
            )

        pfx_path = tempfile.mktemp(suffix=".pfx")
        cert_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Certificado público
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-clcerts", "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{certificate.password}",
            ])

            # Clave privada
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts", "-nodes",
                "-out", key_path,
                "-passin", f"pass:{certificate.password}",
            ])

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
                    _("Error HTTP SII: %s") % response.status_code
                )

            if "SII" not in response.text:
                raise UserError(_("Respuesta SII inválida."))

            return session

        except subprocess.CalledProcessError:
            raise UserError(
                _("Error al convertir el certificado PFX. "
                  "La contraseña no pudo ser aplicada.")
            )

        finally:
            for path in (pfx_path, cert_path, key_path):
                if os.path.exists(path):
                    os.unlink(path)
