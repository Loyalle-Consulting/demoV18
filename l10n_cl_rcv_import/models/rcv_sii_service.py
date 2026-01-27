# -*- coding: utf-8 -*-

import base64
import tempfile
import os
import subprocess
import requests

from bs4 import BeautifulSoup
from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile (flujo real Angular + PFX)"


    def fetch_rcv(self, company, year, month, import_type):

        session, cert_files = self._login_sii(company)

        try:
            # 🔥 PASO REAL OBLIGATORIO
            self._bootstrap_rcv_angular(session)

            html = self._fetch_rcv_html(session, company, year, month, import_type)
            documents = self._parse_rcv_html(html)

            raise UserError(_(
                "RCV REAL consultado correctamente desde el SII.\n\n"
                "Documentos detectados: %s\n\n"
                "TLS + Angular Session + XSRF OK.\n\n"
                "Siguiente paso: persistencia (3B.6)."
            ) % len(documents))

        finally:
            for f in cert_files:
                if f and os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # LOGIN TLS
    # =========================================================
    def _login_sii(self, company):

        cert = self.env["certificate.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("date_start", "<=", fields.Date.today()),
                ("date_end", ">=", fields.Date.today()),
            ],
            limit=1,
        )

        if not cert or not cert.content or not cert.pkcs12_password:
            raise UserError(_("Certificado SII inválido o incompleto."))

        pfx_path = tempfile.mktemp(".pfx")
        pem_path = tempfile.mktemp(".pem")
        key_path = tempfile.mktemp(".key")

        with open(pfx_path, "wb") as f:
            f.write(base64.b64decode(cert.content))

        subprocess.check_call([
            "openssl", "pkcs12", "-legacy",
            "-in", pfx_path,
            "-clcerts", "-nokeys",
            "-out", pem_path,
            "-passin", f"pass:{cert.pkcs12_password}",
        ])

        subprocess.check_call([
            "openssl", "pkcs12", "-legacy",
            "-in", pfx_path,
            "-nocerts", "-nodes",
            "-out", key_path,
            "-passin", f"pass:{cert.pkcs12_password}",
        ])

        session = requests.Session()
        session.cert = (pem_path, key_path)
        session.verify = True
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
        })

        resp = session.get(
            "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi",
            timeout=30
        )

        if resp.status_code != 200:
            raise UserError(_("Login SII falló (%s)") % resp.status_code)

        return session, (pfx_path, pem_path, key_path)


    # =========================================================
    # 🔥 BOOTSTRAP REAL ANGULAR RCV
    # =========================================================
    def _bootstrap_rcv_angular(self, session):

        url = (
            "https://www4.sii.cl/consdcvinternetui/"
            "app/rcv/index.html"
        )

        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            raise UserError(_("No se pudo inicializar RCV Angular (%s)") % resp.status_code)

        # Obtener XSRF desde cookies
        xsrf = session.cookies.get("XSRF-TOKEN")
        if not xsrf:
            raise UserError(_("SII no entregó XSRF-TOKEN (sesión inválida)."))

        # Header obligatorio para el backend
        session.headers.update({
            "X-XSRF-TOKEN": xsrf,
            "Referer": url,
            "Accept": "application/json",
        })


    # =========================================================
    # CONSULTA RCV REAL
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        rut = company.vat.replace(".", "").replace("-", "")

        tipo_map = {
            "purchase": "COMPRA",
            "compras": "COMPRA",
            "sale": "VENTA",
            "ventas": "VENTA",
            "both": "AMBOS",
            "ambos": "AMBOS",
        }

        tipo = tipo_map.get((import_type or "").lower())
        if not tipo:
            raise UserError(_("Tipo de importación inválido: %s") % import_type)

        url = (
            "https://www4.sii.cl/consdcvinternetui/services/data/"
            "facadeService/getDetalleCompraVenta"
        )

        payload = {
            "rutEmisor": rut[:-1],
            "dvEmisor": rut[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
            "tipoOperacion": tipo,
        }

        resp = session.post(url, json=payload, timeout=60)

        if resp.status_code != 200:
            raise UserError(_("Error HTTP RCV: %s") % resp.status_code)

        return resp.text


    # =========================================================
    # PARSEO
    # =========================================================
    def _parse_rcv_html(self, html):

        soup = BeautifulSoup(html, "lxml")
        documents = []

        for table in soup.find_all("table"):
            for row in table.find_all("tr")[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 6:
                    documents.append({
                        "tipo_dte": cols[0],
                        "folio": cols[1],
                        "rut": cols[2],
                        "fecha": cols[3],
                        "neto": cols[4],
                        "total": cols[5],
                    })

        return documents
