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
    _description = "Servicio SII RCV Chile – REAL"

    # =========================================================
    # PUBLIC
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.4 + 3B.5
        - Login real SII
        - Consulta RCV
        - Parseo HTML
        """

        session = self._login_sii(company)

        html = self._fetch_rcv_html(session, company, year, month, import_type)

        documents = self._parse_rcv_html(html)

        # CHECKPOINT VISUAL (temporal)
        raise UserError(_(
            "RCV REAL consultado correctamente desde el SII.\n\n"
            "Documentos detectados: %s\n\n"
            "PASO 3B.5 OK\n"
            "Siguiente: persistir en Odoo (3B.6)."
        ) % len(documents))

    # =========================================================
    # LOGIN REAL SII (ESTABLE – ODOO.SH SAFE)
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
        pass_path = tempfile.mktemp(suffix=".pass")

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Guardar contraseña en archivo (CRÍTICO para Odoo.sh)
            with open(pass_path, "w") as f:
                f.write(certificate.pkcs12_password)

            # Extraer certificado
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-clcerts", "-nokeys",
                "-out", cert_path,
                "-passin", f"file:{pass_path}",
            ])

            # Extraer clave privada
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts", "-nodes",
                "-out", key_path,
                "-passin", f"file:{pass_path}",
            ])

            # Crear sesión TLS
            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII"
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(_("Error HTTP SII: %s") % response.status_code)

            return session

        except subprocess.CalledProcessError as e:
            raise UserError(_(
                "Error al convertir certificado PFX.\n"
                "OpenSSL retornó error.\n"
                "Verifique contraseña y formato del certificado."
            ))

        finally:
            for path in (pfx_path, cert_path, key_path, pass_path):
                if os.path.exists(path):
                    os.unlink(path)

    # =========================================================
    # PASO 3B.4 – CONSULTA RCV REAL
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        rut = company.vat.replace(".", "").replace("-", "")

        tipo = {
            "compras": "COMPRA",
            "ventas": "VENTA",
            "ambos": "AMBOS",
        }.get(import_type.lower(), "COMPRA")

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

        response = session.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            raise UserError(_("Error HTTP RCV: %s") % response.status_code)

        return response.text

    # =========================================================
    # PASO 3B.5 – PARSEO HTML RCV
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
