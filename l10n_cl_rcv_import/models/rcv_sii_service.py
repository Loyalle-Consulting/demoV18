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
    _description = "Servicio SII RCV Chile (PFX automático OpenSSL 3)"


    def fetch_rcv(self, company, year, month, import_type):

        session = self._login_sii(company)
        html = self._fetch_rcv_html(session, company, year, month, import_type)
        documents = self._parse_rcv_html(html)

        raise UserError(_(
            "RCV REAL consultado correctamente desde el SII.\n\n"
            "Documentos detectados: %s\n\n"
            "OPENSSL 3 + PFX LEGACY OK.\n"
            "Siguiente paso: persistencia (3B.6)."
        ) % len(documents))


    # =========================================================
    # LOGIN SII REAL (OPENSSL 3 FIX)
    # =========================================================
    def _login_sii(self, company):

        cert = self.env["certificate.certificate"].search([
            ("company_id", "=", company.id),
            ("date_start", "<=", fields.Date.today()),
            ("date_end", ">=", fields.Date.today()),
        ], limit=1)

        if not cert:
            raise UserError(_("No existe certificado SII vigente."))

        if not cert.content or not cert.pkcs12_password:
            raise UserError(_("Certificado sin archivo o contraseña."))

        pfx_path = tempfile.mktemp(".pfx")
        pem_path = tempfile.mktemp(".pem")
        key_path = tempfile.mktemp(".key")

        try:
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(cert.content))

            # 🔥 OPENSSL 3 + LEGACY (CLAVE)
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-clcerts",
                "-nokeys",
                "-out", pem_path,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-nocerts",
                "-nodes",
                "-out", key_path,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            session = requests.Session()
            session.cert = (pem_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-SII-RCV"
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            resp = session.get(login_url, timeout=30)

            if resp.status_code != 200:
                raise UserError(_("Login SII falló (%s)") % resp.status_code)

            return session

        except subprocess.CalledProcessError as e:
            raise UserError(_(
                "Error al abrir certificado PFX con OpenSSL.\n\n"
                "Este certificado requiere modo LEGACY (OpenSSL 3).\n"
                "La contraseña es correcta, pero el algoritmo es antiguo."
            ))

        finally:
            for f in (pfx_path, pem_path, key_path):
                if f and os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # CONSULTA RCV
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        rut = company.vat.replace(".", "").replace("-", "")
        tipo = {"compras": "COMPRA", "ventas": "VENTA", "ambos": "AMBOS"}[import_type.lower()]

        url = "https://www4.sii.cl/consdcvinternetui/services/data/facadeService/getDetalleCompraVenta"

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
