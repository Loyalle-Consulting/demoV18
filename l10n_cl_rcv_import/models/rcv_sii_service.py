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
    _description = "Servicio SII RCV Chile (PFX automático OpenSSL 3 LEGACY)"


    # =========================================================
    # PASO 3B.4 + 3B.5
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):

        session, cert_files = self._login_sii(company)

        try:
            html = self._fetch_rcv_html(session, company, year, month, import_type)
            documents = self._parse_rcv_html(html)

            # CHECKPOINT CONTROLADO
            raise UserError(_(
                "RCV REAL consultado correctamente desde el SII.\n\n"
                "Documentos detectados: %s\n\n"
                "PFX → PEM/KEY automático OK.\n"
                "OPENSSL 3 LEGACY OK.\n\n"
                "Siguiente paso: persistencia (3B.6)."
            ) % len(documents))

        finally:
            # 🔥 Borrado seguro SOLO al final
            for f in cert_files:
                if f and os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # LOGIN SII REAL (OPENSSL 3 + PFX LEGACY)
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

        if not cert:
            raise UserError(_("No existe certificado SII vigente."))

        if not cert.content or not cert.pkcs12_password:
            raise UserError(_("Certificado sin archivo o contraseña."))

        pfx_path = tempfile.mktemp(suffix=".pfx")
        pem_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(cert.content))

            # Certificado público
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-clcerts",
                "-nokeys",
                "-out", pem_path,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            # Llave privada
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
                raise UserError(_("Login SII falló (HTTP %s)") % resp.status_code)

            # ⚠️ IMPORTANTE: NO borrar aquí
            return session, (pfx_path, pem_path, key_path)

        except subprocess.CalledProcessError:
            raise UserError(_(
                "Error al procesar el certificado PFX.\n\n"
                "Este certificado utiliza algoritmos legacy.\n"
                "OpenSSL 3 con -legacy es obligatorio.\n\n"
                "Verifique la contraseña."
            ))


    # =========================================================
    # CONSULTA RCV REAL
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        if not company.vat:
            raise UserError(_("La empresa no tiene RUT configurado."))

        rut = company.vat.replace(".", "").replace("-", "")

        tipo_map = {
            "purchase": "COMPRA",
            "sale": "VENTA",
            "both": "AMBOS",
            "compras": "COMPRA",
            "ventas": "VENTA",
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
    # PARSEO HTML RCV
    # =========================================================
    def _parse_rcv_html(self, html):

        soup = BeautifulSoup(html, "lxml")
        documents = []

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) < 6:
                    continue

                documents.append({
                    "tipo_dte": cols[0],
                    "folio": cols[1],
                    "rut": cols[2],
                    "fecha": cols[3],
                    "neto": cols[4],
                    "total": cols[5],
                })

        return documents
