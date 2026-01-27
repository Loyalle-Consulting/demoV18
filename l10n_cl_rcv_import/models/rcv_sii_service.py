import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Flujo REAL definitivo"


    def fetch_rcv(self, company, year, month, import_type):
        session = self._login_and_prepare_session(company)

        if import_type in ("compras", "ambos"):
            self._fetch_rcv_compras(session, company, year, month)

        if import_type in ("ventas", "ambos"):
            self._fetch_rcv_ventas(session, company, year, month)

        raise UserError(_("RCV REAL consultado correctamente desde el SII."))


    # =========================================================
    # LOGIN + SESIÓN + SELECCIÓN EMPRESA (CRÍTICO)
    # =========================================================
    def _login_and_prepare_session(self, company):

        cert = self.env["certificate.certificate"].search([
            ("company_id", "=", company.id),
            ("date_start", "<=", fields.Date.today()),
            ("date_end", ">=", fields.Date.today()),
        ], limit=1)

        if not cert or not cert.content or not cert.pkcs12_password:
            raise UserError(_("Certificado SII inválido o incompleto."))

        pfx = tempfile.mktemp(".pfx")
        pem = tempfile.mktemp(".pem")
        key = tempfile.mktemp(".key")

        try:
            with open(pfx, "wb") as f:
                f.write(base64.b64decode(cert.content))

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx,
                "-clcerts", "-nokeys",
                "-out", pem,
                "-passin", f"pass:{cert.pkcs12_password}",
                "-legacy",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx,
                "-nocerts", "-nodes",
                "-out", key,
                "-passin", f"pass:{cert.pkcs12_password}",
                "-legacy",
            ])

            session = requests.Session()
            session.cert = (pem, key)
            session.verify = True

            # HEADERS OBLIGATORIOS PARA SII
            session.headers.update({
                "User-Agent": "Mozilla/5.0",
                "Host": "palena.sii.cl",
                "Origin": "https://palena.sii.cl",
                "Referer": "https://palena.sii.cl/",
            })

            # 1️⃣ LOGIN
            session.get(
                "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi",
                timeout=30
            )

            # 2️⃣ INICIAR SESIÓN
            session.get(
                "https://palena.sii.cl/cgi_AUT2000/CAutIniSesion.cgi",
                timeout=30
            )

            # 3️⃣ SELECCIONAR EMPRESA (ESTE ERA EL PASO FALTANTE)
            rut = company.vat.replace(".", "").replace("-", "")
            session.post(
                "https://palena.sii.cl/rcv/rcvSelEmpresa.cgi",
                data={
                    "rutEmisor": rut[:-1],
                    "dvEmisor": rut[-1],
                },
                timeout=30
            )

            return session

        finally:
            for f in (pfx, pem, key):
                if os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # RCV COMPRAS
    # =========================================================
    def _fetch_rcv_compras(self, session, company, year, month):
        url = "https://palena.sii.cl/rcv/rcvConsultaCompraInternet.do"
        periodo = f"{year}{str(month).zfill(2)}"

        r = session.post(url, data={"periodo": periodo}, timeout=60)

        if r.status_code != 200 or "RCV" not in r.text:
            raise UserError(_("RCV Compras: respuesta inválida del SII."))

        return r.text


    # =========================================================
    # RCV VENTAS
    # =========================================================
    def _fetch_rcv_ventas(self, session, company, year, month):
        url = "https://palena.sii.cl/rcv/rcvConsultaVentaInternet.do"
        periodo = f"{year}{str(month).zfill(2)}"

        r = session.post(url, data={"periodo": periodo}, timeout=60)

        if r.status_code != 200 or "RCV" not in r.text:
            raise UserError(_("RCV Ventas: respuesta inválida del SII."))

        return r.text
