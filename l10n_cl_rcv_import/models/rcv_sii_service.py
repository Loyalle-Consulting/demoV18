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
    _description = "Servicio SII RCV Chile – Login y Consumo REAL"


    # =========================================================
    # PASO PRINCIPAL
    # =========================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.4.A
        - Login TLS real (ya validado)
        - Consumo REAL endpoint RCV
        - Mostrar respuesta cruda del SII
        """

        session = self._login_sii(company)

        # Endpoint REAL RCV (usado por SII)
        rcv_url = "https://palena.sii.cl/recursos/vistas/rcv/rcv_consulta_periodo.html"

        payload = {
            "rutEmisor": company.vat.replace(".", "").replace("-", "")[:-1],
            "dvEmisor": company.vat[-1],
            "periodo": f"{year}{str(month).zfill(2)}",
            "tipoOperacion": "VENTA" if import_type == "sales" else "COMPRA",
        }

        response = session.post(rcv_url, data=payload, timeout=30)

        if response.status_code != 200:
            raise UserError(
                _("Error HTTP al consultar RCV SII: %s") % response.status_code
            )

        # MOSTRAR RESPUESTA CRUDA (DEBUG CONTROLADO)
        preview = response.text[:1500]

        raise UserError(
            _(
                "RCV SII – RESPUESTA RECIBIDA (DEBUG)\n\n"
                "Status HTTP: %s\n\n"
                "Primeros caracteres de la respuesta:\n\n%s\n\n"
                "El parseo y creación de líneas se implementa en el PASO 3B.4.B."
            )
            % (response.status_code, preview)
        )


    # =========================================================
    # LOGIN REAL SII (TLS + CERTIFICADO)
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

        try:
            # Guardar PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Certificado público
            subprocess.check_call(
                [
                    "openssl",
                    "pkcs12",
                    "-in",
                    pfx_path,
                    "-clcerts",
                    "-nokeys",
                    "-out",
                    cert_path,
                    "-passin",
                    f"pass:{certificate.pkcs12_password}",
                ]
            )

            # Clave privada
            subprocess.check_call(
                [
                    "openssl",
                    "pkcs12",
                    "-in",
                    pfx_path,
                    "-nocerts",
                    "-nodes",
                    "-out",
                    key_path,
                    "-passin",
                    f"pass:{certificate.pkcs12_password}",
                ]
            )

            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update(
                {
                    "User-Agent": "Odoo-18-RCV-SII",
                    "Accept": "text/html,application/xhtml+xml",
                }
            )

            # Login SII
            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            login_response = session.get(login_url, timeout=30)

            if login_response.status_code != 200:
                raise UserError(_("Error de autenticación SII."))

            return session

        except subprocess.CalledProcessError:
            raise UserError(
                _("Error al convertir certificado PFX. Verifique contraseña.")
            )

        finally:
            for path in (pfx_path, cert_path, key_path):
                if path and os.path.exists(path):
                    os.unlink(path)
