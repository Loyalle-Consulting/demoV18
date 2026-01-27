import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Flujo REAL"


    # =========================================================
    # ENTRY POINT
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):

        session = self._login_and_init_rcv_session(company)

        if import_type in ("compras", "ambos"):
            self._fetch_rcv_compras(session, company, year, month)

        if import_type in ("ventas", "ambos"):
            self._fetch_rcv_ventas(session, company, year, month)

        raise UserError(
            _("RCV consultado correctamente desde el SII.\n"
              "Sesión válida.\n"
              "Listo para parseo.")
        )


    # =========================================================
    # LOGIN + INICIALIZACIÓN RCV (PASO CLAVE)
    # =========================================================
    def _login_and_init_rcv_session(self, company):

        certificate = self.env["certificate.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("date_start", "<=", fields.Date.today()),
                ("date_end", ">=", fields.Date.today()),
            ],
            limit=1,
        )

        if not certificate or not certificate.content or not certificate.pkcs12_password:
            raise UserError(_("Certificado SII no válido o incompleto."))

        pfx = tempfile.mktemp(".pfx")
        cert = tempfile.mktemp(".pem")
        key = tempfile.mktemp(".key")

        try:
            with open(pfx, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx,
                "-clcerts", "-nokeys",
                "-out", cert,
                "-passin", f"pass:{certificate.pkcs12_password}",
                "-legacy",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx,
                "-nocerts", "-nodes",
                "-out", key,
                "-passin", f"pass:{certificate.pkcs12_password}",
                "-legacy",
            ])

            session = requests.Session()
            session.cert = (cert, key)
            session.verify = True
            session.headers.update({"User-Agent": "Odoo-RCV-18"})

            # 1️⃣ LOGIN TLS
            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            r1 = session.get(login_url, timeout=30)

            if r1.status_code != 200 or "SII" not in r1.text:
                raise UserError(_("Login SII inválido."))

            # 2️⃣ INICIALIZAR SESIÓN RCV (ESTE ERA EL PASO FALTANTE)
            init_url = "https://palena.sii.cl/cgi_AUT2000/CAutIniSesion.cgi"
            r2 = session.get(init_url, timeout=30)

            if r2.status_code != 200:
                raise UserError(_("No se pudo inicializar sesión RCV."))

            return session

        finally:
            for f in (pfx, cert, key):
                if os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # RCV COMPRAS
    # =========================================================
    def _fetch_rcv_compras(self, session, company, year, month):

        url = "https://palena.sii.cl/rcv/rcvConsultaCompraInternet.do"
        data = {
            "rutEmisor": company.vat[:-2],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
        }

        r = session.post(url, data=data, timeout=60)

        if r.status_code != 200 or "RCV" not in r.text:
            raise UserError(_("RCV Compras: respuesta inválida del SII."))

        return r.text


    # =========================================================
    # RCV VENTAS
    # =========================================================
    def _fetch_rcv_ventas(self, session, company, year, month):

        url = "https://palena.sii.cl/rcv/rcvConsultaVentaInternet.do"
        data = {
            "rutEmisor": company.vat[:-2],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
        }

        r = session.post(url, data=data, timeout=60)

        if r.status_code != 200 or "RCV" not in r.text:
            raise UserError(_("RCV Ventas: respuesta inválida del SII."))

        return r.text
