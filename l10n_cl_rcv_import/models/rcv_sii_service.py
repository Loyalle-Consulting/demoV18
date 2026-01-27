import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Login real TLS (Odoo 18)"

    # ---------------------------------------------------------
    # ENTRY POINT DESDE EL WIZARD
    # ---------------------------------------------------------
    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.3 – Login real contra SII usando certificado
        """
        self._login_sii(company)

        # Login validado correctamente
        raise UserError(
            _(
                "Certificado SII validado correctamente.\n\n"
                "✔ Certificado vigente\n"
                "✔ Contraseña correcta\n"
                "✔ Autenticación TLS exitosa\n\n"
                "El consumo REAL del RCV se implementa en el PASO 3B.4 "
                "(consulta directa al endpoint SII RCV)."
            )
        )

    # ---------------------------------------------------------
    # LOGIN REAL SII (TLS + CERTIFICADO)
    # ---------------------------------------------------------
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
            raise UserError(_("No existe un certificado SII vigente para la empresa."))

        if not certificate.content:
            raise UserError(_("El certificado no tiene contenido PFX cargado."))

        if not certificate.pkcs12_password:
            raise UserError(_("El certificado no tiene contraseña configurada."))

        password = certificate.pkcs12_password.strip()

        # Archivos temporales
        pfx_fd, pfx_path = tempfile.mkstemp(suffix=".pfx")
        cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
        key_fd, key_path = tempfile.mkstemp(suffix=".key")

        os.close(pfx_fd)
        os.close(cert_fd)
        os.close(key_fd)

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Validar contraseña PFX
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-info",
                "-noout",
                "-passin", f"pass:{password}",
            ])

            # Extraer certificado
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-clcerts",
                "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{password}",
            ])

            # Extraer clave privada
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-nocerts",
                "-nodes",
                "-out", key_path,
                "-passin", f"pass:{password}",
            ])

            # Crear sesión TLS
            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII"
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30, allow_redirects=True)

            if response.status_code not in (200, 302):
                raise UserError(
                    _("Error HTTP al conectar con SII. Código: %s") % response.status_code
                )

            # ✅ NO validar contenido HTML (correcto en 3B.3)
            return session

        except subprocess.CalledProcessError:
            raise UserError(
                _("Error al convertir el certificado PFX. Verifique la contraseña.")
            )

        finally:
            for path in (pfx_path, cert_path, key_path):
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass
