# -*- coding: utf-8 -*-

import base64
import csv
import io
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile - CSV oficial (Compras y Ventas)"


    # =========================================================
    # ENTRY POINT
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        Flujo REAL:
        1) Login TLS con PFX
        2) Descarga CSV RCV
        3) Parseo CSV
        """

        session, cert_files = self._login_sii_tls(company)

        try:
            csv_content = self._download_rcv_csv(
                session=session,
                company=company,
                year=year,
                month=month,
                import_type=import_type,
            )

            rows = self._parse_rcv_csv(csv_content)

            # CHECKPOINT CONTROLADO
            raise UserError(_(
                "RCV REAL descargado correctamente desde el SII.\n\n"
                "Tipo: %s\n"
                "Documentos detectados: %s\n\n"
                "Flujo CSV oficial OK.\n"
                "Siguiente paso: persistencia (3B.6)."
            ) % (import_type, len(rows)))

        finally:
            for f in cert_files:
                if f and os.path.exists(f):
                    os.unlink(f)


    # =========================================================
    # LOGIN TLS SII (PFX → PEM/KEY)
    # =========================================================
    def _login_sii_tls(self, company):

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

        pfx_path = tempfile.mktemp(suffix=".pfx")
        pem_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
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

            # Login TLS base
            resp = session.get(
                "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi",
                timeout=30
            )

            if resp.status_code != 200:
                raise UserError(_("Login SII falló (HTTP %s)") % resp.status_code)

            return session, (pfx_path, pem_path, key_path)

        except subprocess.CalledProcessError:
            raise UserError(_(
                "Error al procesar certificado PFX.\n"
                "OpenSSL 3 requiere -legacy.\n"
                "Verifique contraseña."
            ))


    # =========================================================
    # DESCARGA CSV RCV (OFICIAL)
    # =========================================================
    def _download_rcv_csv(self, session, company, year, month, import_type):

        if not company.vat:
            raise UserError(_("La empresa no tiene RUT configurado."))

        rut = company.vat.replace(".", "").replace("-", "")

        tipo_map = {
            "purchase": "COMPRA",
            "compras": "COMPRA",
            "sale": "VENTA",
            "ventas": "VENTA",
        }

        tipo = tipo_map.get((import_type or "").lower())
        if not tipo:
            raise UserError(_("Tipo de importación inválido: %s") % import_type)

        url = "https://www.sii.cl/servicios_online/rcv/descargar_rcv.csv"

        payload = {
            "rutEmisor": rut[:-1],
            "dvEmisor": rut[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
            "tipo": tipo,
        }

        resp = session.post(url, data=payload, timeout=60)

        if resp.status_code != 200:
            raise UserError(_("Error HTTP RCV: %s") % resp.status_code)

        if b";" not in resp.content:
            raise UserError(_("El SII no retornó un CSV válido."))

        return resp.content


    # =========================================================
    # PARSEO CSV RCV
    # =========================================================
    def _parse_rcv_csv(self, content):

        decoded = content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(decoded), delimiter=";")

        rows = []
        for row in reader:
            rows.append(row)

        return rows
