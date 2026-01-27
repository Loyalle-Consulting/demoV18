# -*- coding: utf-8 -*-

import base64
import tempfile
import os
import requests
from bs4 import BeautifulSoup

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – REAL (PEM)"


    # =========================================================
    # PUBLIC
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B FINAL
        - Login real SII (PEM)
        - Consulta RCV
        - Parseo HTML
        """

        session = self._login_sii(company)

        html = self._fetch_rcv_html(session, company, year, month, import_type)

        documents = self._parse_rcv_html(html)

        # CHECKPOINT VISUAL CONTROLADO
        raise UserError(_(
            "RCV REAL consultado correctamente desde el SII.\n\n"
            "Documentos detectados: %s\n\n"
            "Conexión y consumo OK.\n"
            "Siguiente paso: persistencia en Odoo (3B.6)."
        ) % len(documents))


    # =========================================================
    # LOGIN REAL SII (PEM / KEY)
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

        if not certificate.sii_cert_pem or not certificate.sii_key_pem:
            raise UserError(_(
                "El certificado SII debe tener:\n"
                "- Certificado PEM\n"
                "- Llave privada KEY\n\n"
                "Extensión segura, sin usar PFX."
            ))

        cert_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            with open(cert_path, "wb") as f:
                f.write(base64.b64decode(certificate.sii_cert_pem))

            with open(key_path, "wb") as f:
                f.write(base64.b64decode(certificate.sii_key_pem))

            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII-REAL"
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(_("Error HTTP login SII: %s") % response.status_code)

            return session

        finally:
            for path in (cert_path, key_path):
                if os.path.exists(path):
                    os.unlink(path)


    # =========================================================
    # CONSULTA RCV REAL
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        rut = company.vat.replace(".", "").replace("-", "")

        tipo = {
            "compras": "COMPRA",
            "ventas": "VENTA",
            "ambos": "AMBOS",
        }.get(import_type.lower(), "COMPRA")

        url = (
            "https://www4.sii.cl/consdcvinternetui/services/"
            "data/facadeService/getDetalleCompraVenta"
        )

        payload = {
            "rutEmisor": rut[:-1],
            "dvEmisor": rut[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
            "tipoOperacion": tipo,
        }

        response = session.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            raise UserError(_("Error HTTP RCV: %s") % response.status_code)

        return response.text


    # =========================================================
    # PARSEO HTML RCV
    # =========================================================
    def _parse_rcv_html(self, html):

        soup = BeautifulSoup(html, "lxml")

        tables = soup.find_all("table")
        documents = []

        for table in tables:
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
