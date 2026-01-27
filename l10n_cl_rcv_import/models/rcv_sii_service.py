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


    # =========================================================
    # PUBLIC
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):

        session = self._login_sii(company)

        html = self._fetch_rcv_html(
            session=session,
            company=company,
            year=year,
            month=month,
            import_type=import_type,
        )

        documents = self._parse_rcv_html(html)

        # CHECKPOINT VISUAL CONTROLADO
        raise UserError(_(
            "RCV REAL consultado correctamente desde el SII.\n\n"
            "Documentos detectados: %s\n\n"
            "PFX + OpenSSL 3 + Sesión RCV OK.\n"
            "Siguiente paso: persistencia en Odoo (3B.6)."
        ) % len(documents))


    # =========================================================
    # LOGIN SII REAL (PFX + OPENSSL 3 LEGACY)
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

        pfx_path = tempfile.mktemp(suffix=".pfx")
        pem_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(cert.content))

            # Extraer CERT (PEM)
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-clcerts",
                "-nokeys",
                "-out", pem_path,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            # Extraer KEY
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx_path,
                "-nocerts",
                "-nodes",
                "-out", key_path,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            # Crear sesión HTTPS con certificado
            session = requests.Session()
            session.cert = (pem_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-SII-RCV",
            })

            # LOGIN BASE SII
            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            resp = session.get(login_url, timeout=30)

            if resp.status_code != 200:
                raise UserError(_("Login SII falló (%s)") % resp.status_code)

            return session

        except subprocess.CalledProcessError:
            raise UserError(_(
                "Error al abrir certificado PFX.\n\n"
                "Este certificado requiere OpenSSL 3 en modo LEGACY.\n"
                "Verifique contraseña y validez del archivo."
            ))

        finally:
            # Limpieza segura
            for f in (pfx_path, pem_path, key_path):
                if f and os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # CONSULTA RCV REAL (CON ACTIVACIÓN DE SESIÓN)
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        rut = company.vat.replace(".", "").replace("-", "")

        tipo = {
            "compras": "COMPRA",
            "ventas": "VENTA",
            "ambos": "AMBOS",
        }.get(import_type.lower())

        if not tipo:
            raise UserError(_("Tipo de importación inválido: %s") % import_type)

        # 🔑 PASO CRÍTICO: ACTIVAR SESIÓN RCV (evita 401)
        session.get(
            "https://www4.sii.cl/consdcvinternetui/",
            timeout=30
        )

        url = (
            "https://www4.sii.cl/consdcvinternetui/"
            "services/data/facadeService/getDetalleCompraVenta"
        )

        payload = {
            "rutEmisor": rut[:-1],
            "dvEmisor": rut[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
            "tipoOperacion": tipo,
        }

        resp = session.post(url, json=payload, timeout=60)

        if resp.status_code == 401:
            raise UserError(_("RCV rechazado por SII (401). Sesión no válida."))

        if resp.status_code != 200:
            raise UserError(_("Error HTTP RCV: %s") % resp.status_code)

        return resp.text


    # =========================================================
    # PARSEO RCV
    # =========================================================
    def _parse_rcv_html(self, html):

        soup = BeautifulSoup(html, "lxml")
        documents = []

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows[1:]:
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
