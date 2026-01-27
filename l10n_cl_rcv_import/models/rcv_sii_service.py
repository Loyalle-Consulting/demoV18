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
    _description = "Servicio SII RCV Chile (PFX automático, sin PEM manual)"


    # =========================================================
    # PUBLIC API
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        Flujo REAL RCV SII:
        1) Login TLS con certificado PFX
        2) Consulta endpoint RCV
        3) Parseo de respuesta
        """

        session = self._login_sii(company)

        html = self._fetch_rcv_html(session, company, year, month, import_type)

        documents = self._parse_rcv_html(html)

        # CHECKPOINT CONTROLADO (se elimina en 3B.6)
        raise UserError(_(
            "RCV REAL consultado correctamente desde el SII.\n\n"
            "Documentos detectados: %s\n\n"
            "Autenticación PFX automática OK.\n"
            "Siguiente paso: persistencia en Odoo (3B.6)."
        ) % len(documents))


    # =========================================================
    # LOGIN SII REAL (PFX AUTOMÁTICO)
    # =========================================================
    def _login_sii(self, company):
        """
        Usa certificado .pfx desde certificate.certificate
        Convierte a PEM/KEY en runtime (servidor Odoo.sh)
        """

        certificate = self.env["certificate.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("date_start", "<=", fields.Date.today()),
                ("date_end", ">=", fields.Date.today()),
            ],
            limit=1,
        )

        if not certificate:
            raise UserError(_("No existe un certificado SII vigente para la empresa."))

        if not certificate.content or not certificate.pkcs12_password:
            raise UserError(_("El certificado SII no tiene contenido o contraseña."))

        # Archivos temporales
        pfx_path = tempfile.mktemp(suffix=".pfx")
        cert_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Extraer certificado PEM
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-clcerts",
                "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            # Extraer llave privada KEY
            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts",
                "-nodes",
                "-out", key_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            # Sesión HTTPS con certificado cliente
            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII"
            })

            # Login inicial SII (establece sesión)
            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(_("Error HTTP en login SII: %s") % response.status_code)

            return session

        except subprocess.CalledProcessError:
            raise UserError(_(
                "Error al procesar el certificado PFX.\n"
                "Verifique que la contraseña sea correcta y que el archivo sea válido."
            ))

        finally:
            # Limpieza segura
            for path in (pfx_path, cert_path, key_path):
                if path and os.path.exists(path):
                    os.unlink(path)


    # =========================================================
    # CONSULTA RCV REAL
    # =========================================================
    def _fetch_rcv_html(self, session, company, year, month, import_type):

        if not company.vat:
            raise UserError(_("La empresa no tiene RUT configurado."))

        rut = company.vat.replace(".", "").replace("-", "")

        tipo = {
            "compras": "COMPRA",
            "ventas": "VENTA",
            "ambos": "AMBOS",
        }.get(import_type.lower())

        if not tipo:
            raise UserError(_("Tipo de importación inválido."))

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

        response = session.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            raise UserError(_("Error HTTP RCV SII: %s") % response.status_code)

        if not response.text:
            raise UserError(_("Respuesta vacía del SII."))

        return response.text


    # =========================================================
    # PARSEO RCV
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
