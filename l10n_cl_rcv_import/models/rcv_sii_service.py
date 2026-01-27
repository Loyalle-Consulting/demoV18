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
        Paso 3B.3 – Login real contra SII usando certificado PFX
        """
        session = self._login_sii(company)

        # Por ahora dejamos el login validado.
        # El consumo real del endpoint RCV se implementa en PASO 3B.4
        raise UserError(
            _(
                "Certificado SII validado correctamente.\n\n"
                "✔ Certificado vigente\n"
                "✔ Contraseña correcta\n"
                "✔ Empresa configurada\n\n"
                "El consumo REAL del RCV se implementa en el PASO 3B.4 "
                "(consulta directa al endpoint SII RCV)."
            )
        )

    # ---------------------------------------------------------
    # LOGIN REAL SII CON CERTIFICADO PFX (OPENSSL LEGACY)
    # ---------------------------------------------------------
    def _login_sii(self, company):

        # Buscar certificado vigente de la empresa
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
            raise UserError(_("El certificado no tiene contenido cargado (PFX)."))

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
            # Guardar archivo PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # -------------------------------------------------
            # VALIDACIÓN PREVIA DEL PFX (PASSWORD REAL)
            # -------------------------------------------------
            try:
                subprocess.check_call([
                    "openssl", "pkcs12",
                    "-legacy",
                    "-in", pfx_path,
                    "-info",
                    "-noout",
                    "-passin", f"pass:{password}",
                ])
            except subprocess.CalledProcessError:
                raise UserError(
                    _("La contraseña del certificado es incorrecta o el archivo PFX es inválido.")
                )

            # -------------------------------------------------
            # EXTRAER CERTIFICADO (PUBLIC CERT)
            # -------------------------------------------------
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-clcerts",
                "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{password}",
            ])

            # -------------------------------------------------
            # EXTRAER CLAVE PRIVADA
            # -------------------------------------------------
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-nocerts",
                "-nodes",
                "-out", key_path,
                "-passin", f"pass:{password}",
            ])

            # -------------------------------------------------
            # SESIÓN TLS CONTRA SII
            # -------------------------------------------------
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
                    _("Error HTTP al conectar con SII. Código: %s") % response.status_code
                )

            if "SII" not in response.text:
                raise UserError(_("La respuesta del SII no es válida."))

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
