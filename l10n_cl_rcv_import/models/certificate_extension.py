# -*- coding: utf-8 -*-

from odoo import models, fields


class CertificateCertificate(models.Model):
    _inherit = "certificate.certificate"

    sii_cert_pem = fields.Binary(
        string="Certificado SII (PEM)",
        help="Certificado público en formato PEM para conexión SII",
    )

    sii_key_pem = fields.Binary(
        string="Llave privada SII (KEY)",
        help="Llave privada en formato PEM para conexión SII",
    )