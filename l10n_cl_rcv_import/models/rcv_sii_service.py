import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Consumo REAL"


    # =========================================================
    # ENTRY POINT DESDE EL WIZARD
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.4 – CONSUMO REAL RCV
        """

        session = self._login_sii(company)

        if import_type in ("compras", "ambos"):
            self._fetch_rcv_compras(session, company, year, month)

        if import_type in ("ventas", "ambos"):
            self._fetch_rcv_ventas(session, company, year, month)

        raise UserError(
            _("RCV consultado correctamente desde el SII.\n"
              "Respuesta recibida.\n"
              "Siguiente paso: parseo y creación de líneas.")
        )


    # =========================================================
    # LOGIN REAL SII (YA VALIDADO)
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

        pfx_path = tempfile.mktemp(suffix=".pfx")
        cert_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-clcerts", "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
                "-legacy",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts", "-nodes",
                "-out", key_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
                "-legacy",
            ])

            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII",
                "Accept": "text/html",
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            resp = session.get(login_url, timeout=30)

            if resp.status_code != 200:
                raise UserError(_("Error HTTP autenticando en SII."))

            if "SII" not in resp.text:
                raise UserError(_("Login SII inválido."))

            return session

        except subprocess.CalledProcessError:
            raise UserError(_("Error al convertir certificado PFX."))

        finally:
            for p in (pfx_path, cert_path, key_path):
                if os.path.exists(p):
                    os.unlink(p)


    # =========================================================
    # RCV COMPRAS – ENDPOINT REAL
    # =========================================================
    def _fetch_rcv_compras(self, session, company, year, month):

        url = "https://palena.sii.cl/rcv/rcvConsultaCompraInternet.do"

        params = {
            "rutEmisor": company.vat.replace("-", "")[:-1],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
        }

        resp = session.post(url, data=params, timeout=60)

        if resp.status_code != 200:
            raise UserError(_("Error HTTP al consultar RCV Compras."))

        if "RCV" not in resp.text:
            raise UserError(_("Respuesta inválida RCV Compras."))

        # 👉 AQUÍ VA EL PARSEO REAL (PASO SIGUIENTE)
        return resp.text


    # =========================================================
    # RCV VENTAS – ENDPOINT REAL
    # =========================================================
    def _fetch_rcv_ventas(self, session, company, year, month):

        url = "https://palena.sii.cl/rcv/rcvConsultaVentaInternet.do"

        params = {
            "rutEmisor": company.vat.replace("-", "")[:-1],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
        }

        resp = session.post(url, data=params, timeout=60)

        if resp.status_code != 200:
            raise UserError(_("Error HTTP al consultar RCV Ventas."))

        if "RCV" not in resp.text:
            raise UserError(_("Respuesta inválida RCV Ventas."))

        # 👉 AQUÍ VA EL PARSEO REAL (PASO SIGUIENTE)
        return resp.text
