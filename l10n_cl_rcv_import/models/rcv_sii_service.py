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
    _description = "Servicio SII RCV Chile – Login y consulta REAL"


    # ---------------------------------------------------------
    # MÉTODO PRINCIPAL
    # ---------------------------------------------------------
    def fetch_rcv(self, company, year, month, import_type):
        """
        PASO 3B.4 REAL
        - Login SII
        - Consulta RCV real
        - Guarda HTML crudo para debug / parseo
        """

        session = self._login_sii(company)

        # Endpoint REAL RCV (SII)
        rcv_url = "https://www4.sii.cl/consdcvinternetui/services/data/facadeService/getDetalle"

        payload = {
            "rutEmisor": company.partner_id.vat.replace(".", "").replace("-", "")[:-1],
            "dvEmisor": company.partner_id.vat[-1],
            "ptributario": f"{year}{str(month).zfill(2)}",
            "estadoContab": "REGISTRO",
            "operacion": "COMPRA" if import_type == "compras" else "VENTA",
        }

        response = session.post(rcv_url, json=payload, timeout=60)

        if response.status_code != 200:
            raise UserError(_("Error HTTP al consultar RCV REAL: %s") % response.status_code)

        if not response.text:
            raise UserError(_("Respuesta vacía del SII al consultar RCV."))

        # -------------------------------------------------
        # GUARDAR HTML / JSON CRUDO (DEBUG / AUDITORÍA)
        # -------------------------------------------------
        self.env["ir.attachment"].create({
            "name": f"RCV_{company.id}_{year}_{month}.html",
            "type": "binary",
            "datas": base64.b64encode(response.text.encode("utf-8")),
            "res_model": "res.company",
            "res_id": company.id,
            "mimetype": "text/html",
        })

        # -------------------------------------------------
        # PASO 3B.5 (SIGUIENTE ETAPA)
        # Aquí se parsea el contenido y se crean líneas RCV
        # -------------------------------------------------
        # TODO:
        # - Detectar si viene HTML o JSON
        # - Extraer documentos
        # - Crear líneas RCV
        # -------------------------------------------------

        return True


    # ---------------------------------------------------------
    # LOGIN REAL SII CON CERTIFICADO DIGITAL
    # ---------------------------------------------------------
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
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-clcerts", "-nokeys",
                "-out", cert_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            subprocess.check_call([
                "openssl", "pkcs12",
                "-in", pfx_path,
                "-nocerts", "-nodes",
                "-out", key_path,
                "-passin", f"pass:{certificate.pkcs12_password}",
            ])

            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII",
                "Accept": "*/*",
            })

            login_url = "https://palena.sii.cl/cgi_AUT2000/CAutInicio.cgi"
            response = session.get(login_url, timeout=30)

            if response.status_code != 200:
                raise UserError(_("Error HTTP en login SII: %s") % response.status_code)

            if "SII" not in response.text:
                raise UserError(_("Login SII inválido."))

            return session

        except subprocess.CalledProcessError:
            raise UserError(_("Error al convertir certificado PFX. Verifique contraseña."))

        finally:
            for path in (pfx_path, cert_path, key_path):
                if os.path.exists(path):
                    os.unlink(path)
