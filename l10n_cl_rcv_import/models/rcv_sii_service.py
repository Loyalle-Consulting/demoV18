# -*- coding: utf-8 -*-

import base64
import tempfile
import os
import subprocess
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile – Login real estable"

    # =========================================================
    # ENTRY POINT
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):

        # 🔒 LOGIN ÚNICO – NO SE REPITE
        session = self._get_sii_session(company)

        # Endpoint real RCV
        url = "https://palena.sii.cl/recursos/vistas/rcv/rcv_consulta_periodo.html"

        payload = {
            "rutEmisor": company.vat.replace(".", "").replace("-", "")[:-1],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
            "tipoOperacion": "COMPRA" if import_type == "purchases" else "VENTA",
        }

        response = session.post(url, data=payload, timeout=30)

        if response.status_code != 200:
            raise UserError(_("Error HTTP SII RCV: %s") % response.status_code)

        # DEBUG CONTROLADO
        preview = response.text[:1200]

        raise UserError(
            _(
                "RCV SII – RESPUESTA OK\n\n"
                "HTTP: %s\n\n"
                "Contenido inicial:\n\n%s\n\n"
                "✔ Login TLS correcto\n"
                "✔ Sesión válida\n"
                "✔ Consumo RCV exitoso\n\n"
                "Siguiente paso: PARSEO (3B.4.B)"
            )
            % (response.status_code, preview)
        )

    # =========================================================
    # SESIÓN SII (CACHEADA)
    # =========================================================
    def _get_sii_session(self, company):
        if hasattr(self.env, "_sii_tls_session"):
            return self.env._sii_tls_session

        session = self._login_sii(company)
        self.env._sii_tls_session = session
        return session

    # =========================================================
    # LOGIN REAL SII (UNA SOLA VEZ)
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

        # Archivos temporales (NO SE BORRAN HASTA FIN DEL PROCESO)
        pfx = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        pem = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        key = tempfile.NamedTemporaryFile(delete=False, suffix=".key")

        try:
            pfx.write(base64.b64decode(cert.content))
            pfx.close()

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx.name,
                "-clcerts", "-nokeys",
                "-out", pem.name,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx.name,
                "-nocerts", "-nodes",
                "-out", key.name,
                "-passin", f"pass:{cert.pkcs12_password}",
            ])

            session = requests.Session()
            session.cert = (pem.name, key.name)
            session.verify = True
            session.headers.update({"User-Agent": "Odoo-18-RCV-SII"})

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            resp = session.get(login_url, timeout=30)

            if resp.status_code != 200:
                raise UserError(_("No fue posible autenticar con el SII."))

            return session

        except subprocess.CalledProcessError:
            raise UserError(_("Error al convertir certificado PFX."))
