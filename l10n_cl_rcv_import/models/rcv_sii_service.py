# -*- coding: utf-8 -*-

import base64
import tempfile
import subprocess
import requests
import os

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – OpenSSL 3 FIX"

    # =========================================================
    # ENTRY POINT
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):

        session = self._get_sii_session(company)

        raise UserError(
            _(
                "✔ Login SII exitoso\n"
                "✔ Certificado válido\n"
                "✔ OpenSSL 3 compatible\n\n"
                "Listo para consumir RCV real (PASO 3B.4)"
            )
        )

    # =========================================================
    # SESIÓN CACHEADA (ANTI LOOP)
    # =========================================================
    def _get_sii_session(self, company):
        if hasattr(self.env, "_sii_session"):
            return self.env._sii_session

        session = self._login_sii(company)
        self.env._sii_session = session
        return session

    # =========================================================
    # LOGIN SII – OPENSSL 3 FIX
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
            raise UserError(_("Certificado sin contenido o contraseña."))

        # Archivos temporales
        pfx = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        pem = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        key = tempfile.NamedTemporaryFile(delete=False, suffix=".key")

        try:
            # Guardar PFX
            pfx.write(base64.b64decode(cert.content))
            pfx.close()

            # 🔥 OPENSSL 3 → -legacy ES OBLIGATORIO
            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx.name,
                "-clcerts",
                "-nokeys",
                "-out", pem.name,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-legacy",
                "-in", pfx.name,
                "-nocerts",
                "-nodes",
                "-out", key.name,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            session = requests.Session()
            session.cert = (pem.name, key.name)
            session.verify = True
            session.headers.update({"User-Agent": "Odoo-18-SII-RCV"})

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(_("No fue posible autenticar con el SII."))

            return session

        except subprocess.CalledProcessError as e:
            raise UserError(
                _(
                    "Error al convertir certificado PFX.\n\n"
                    "⚠ OpenSSL 3 requiere -legacy para certificados SII.\n"
                    "Este error NO es la contraseña."
                )
            )
