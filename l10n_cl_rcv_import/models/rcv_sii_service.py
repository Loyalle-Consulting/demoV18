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
    _description = "Servicio SII RCV Chile - Consumo REAL"


    # =====================================================
    # MÉTODO PRINCIPAL LLAMADO DESDE EL WIZARD
    # =====================================================
    def fetch_rcv(self, company, year, month, import_type):
        """
        Punto de entrada único.
        En este PASO 3B.4 solo implementamos RCV VENTAS REAL.
        """

        session = self._login_sii_tls(company)

        if import_type not in ("ventas", "ambos"):
            raise UserError(_("En este paso solo está habilitado RCV Ventas."))

        data = self._fetch_rcv_ventas(session, company, year, month)

        # En 3B.4 solo confirmamos recepción correcta
        raise UserError(
            _(
                "RCV Ventas obtenido correctamente desde el SII.\n\n"
                "Período: %s-%s\n"
                "Registros recibidos: %s\n\n"
                "Siguiente paso: PASO 3B.5 (parseo y guardado en Odoo)."
            )
            % (year, str(month).zfill(2), len(data))
        )


    # =====================================================
    # LOGIN REAL TLS SII (CERTIFICADO DIGITAL)
    # =====================================================
    def _login_sii_tls(self, company):
        """
        Autenticación REAL por TLS usando certificado PFX.
        NO usa login web.
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
            raise UserError(_("No existe certificado digital vigente para la empresa."))

        if not certificate.content or not certificate.pkcs12_password:
            raise UserError(_("El certificado no tiene contenido o contraseña."))

        pfx_path = tempfile.mktemp(suffix=".pfx")
        cert_path = tempfile.mktemp(suffix=".pem")
        key_path = tempfile.mktemp(suffix=".key")

        try:
            # Guardar archivo PFX
            with open(pfx_path, "wb") as f:
                f.write(base64.b64decode(certificate.content))

            # Extraer certificado público
            subprocess.check_call(
                [
                    "openssl", "pkcs12",
                    "-in", pfx_path,
                    "-clcerts", "-nokeys",
                    "-out", cert_path,
                    "-passin", f"pass:{certificate.pkcs12_password}",
                ]
            )

            # Extraer clave privada
            subprocess.check_call(
                [
                    "openssl", "pkcs12",
                    "-in", pfx_path,
                    "-nocerts", "-nodes",
                    "-out", key_path,
                    "-passin", f"pass:{certificate.pkcs12_password}",
                ]
            )

            session = requests.Session()
            session.cert = (cert_path, key_path)
            session.verify = True
            session.headers.update({
                "User-Agent": "Odoo-18-RCV-SII",
                "Accept": "*/*",
            })

            return session

        except subprocess.CalledProcessError:
            raise UserError(
                _("Error al convertir el certificado PFX. Verifique la contraseña.")
            )

        finally:
            for path in (pfx_path, cert_path, key_path):
                if os.path.exists(path):
                    os.unlink(path)


    # =====================================================
    # CONSUMO REAL RCV VENTAS
    # =====================================================
    def _fetch_rcv_ventas(self, session, company, year, month):
        """
        Consulta REAL RCV Ventas al SII.
        Devuelve datos en bruto (texto XML).
        """

        vat = (company.vat or "").replace(".", "").replace("-", "")
        if len(vat) < 2:
            raise UserError(_("La empresa no tiene RUT válido configurado."))

        rut = vat[:-1]
        dv = vat[-1]
        periodo = f"{year}{str(month).zfill(2)}"

        url = "https://palena.sii.cl/cgi_dte/VENTA/CONSULTA/VentasPeriodo.cgi"

        payload = {
            "rutEmisor": rut,
            "dvEmisor": dv,
            "periodo": periodo,
            "tipoConsulta": "VENTAS",
            "origen": "RCV",
        }

        response = session.post(url, data=payload, timeout=60)

        if response.status_code != 200:
            raise UserError(
                _("Error HTTP SII (%s) al consultar RCV Ventas.") % response.status_code
            )

        if not response.text:
            raise UserError(_("El SII no devolvió información para el período consultado."))

        # En este paso solo validamos que hay respuesta válida
        return response.text
