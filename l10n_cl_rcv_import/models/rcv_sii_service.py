import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Compras (RCV)"


    # =========================================================
    # API PRINCIPAL – RCV COMPRAS
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        Punto de entrada llamado desde el wizard.
        Implementación REAL para RCV COMPRAS.
        """

        if import_type != "purchase":
            raise UserError(_("Este servicio solo maneja RCV COMPRAS."))

        session = self._login_sii(company)

        # Endpoint REAL RCV Compras (SII)
        url = (
            "https://palena.sii.cl/cgi_dte/UPL/RCV/"
            "ConsultaRCVCompra.cgi"
        )

        payload = {
            "rutEmisor": company.vat.replace(".", "").replace("-", "")[:-1],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
        }

        response = session.post(url, data=payload, timeout=60)

        if response.status_code != 200:
            raise UserError(
                _("Error HTTP al consultar RCV Compras: %s")
                % response.status_code
            )

        if not response.text or "html" in response.text.lower():
            raise UserError(
                _("La respuesta del SII no es válida.")
            )

        # 🔴 PUNTO CONTROLADO: aquí el SII YA responde datos reales
        raise UserError(
            _(
                "RCV COMPRAS consultado correctamente.\n\n"
                "✔ Login SII exitoso\n"
                "✔ Certificado válido\n"
                "✔ Respuesta REAL del SII recibida\n\n"
                "Siguiente paso: PASO 3B.5 – Parseo y creación "
                "de líneas RCV en Odoo."
            )
        )


    # =========================================================
    # LOGIN REAL SII (TLS + CERTIFICADO)
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

        if not certificate.content or not certificate.pkcs12_password:
            raise UserError(_("Certificado sin contenido o contraseña."))

        # Archivos temporales
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
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            # Clave privada
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts", "-nodes",
                "-out", key_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
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
                _("Error al convertir certificado PFX. Verifique la contraseña.")
            )

        finally:
            for path in (pfx_path, cert_path, key_path):
                if os.path.exists(path):
                    os.unlink(path)
