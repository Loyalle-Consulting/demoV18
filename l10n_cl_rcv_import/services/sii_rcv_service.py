# -*- coding: utf-8 -*-
"""
Servicio SII RCV - Solo lectura
Compatible con Odoo 18 + l10n_cl
Reutiliza certificado digital cargado en Odoo
"""

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class SiiRcvService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV (Lectura)"

    # =====================================================
    # API PUBLICA
    # =====================================================

    def fetch_rcv(self, company, year, month, import_type="both"):
        """
        Obtiene RCV real desde SII (Compras / Ventas)

        :param company: res.company
        :param year: int (YYYY)
        :param month: int (1-12)
        :param import_type: 'purchase', 'sale', 'both'
        :return: lista de dict normalizados
        """

        _logger.info(
            "RCV SII | Empresa=%s Año=%s Mes=%s Tipo=%s",
            company.name,
            year,
            month,
            import_type,
        )

        certificate = self._get_company_certificate(company)

        # 🔐 Aquí más adelante se hará la autenticación real SII
        # Por ahora dejamos el esqueleto funcional

        rcv_data = []

        if import_type in ("purchase", "both"):
            rcv_data += self._fetch_purchase_rcv(
                company, certificate, year, month
            )

        if import_type in ("sale", "both"):
            rcv_data += self._fetch_sale_rcv(
                company, certificate, year, month
            )

        return rcv_data

    # =====================================================
    # IMPLEMENTACIONES INTERNAS
    # =====================================================

    def _get_company_certificate(self, company):
        """
        Obtiene el certificado digital activo de la empresa
        """
        certificate = self.env["l10n_cl.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "valid"),
            ],
            limit=1,
        )

        if not certificate:
            raise ValueError(
                "La empresa no tiene certificado digital válido para SII."
            )

        return certificate

    def _fetch_purchase_rcv(self, company, certificate, year, month):
        """
        Obtiene RCV Compras desde SII
        (Implementación real en siguiente etapa)
        """
        _logger.info("RCV SII | Descargando COMPRAS")

        # ⚠️ Aquí irá:
        # - Login SII
        # - POST HTTPS
        # - Parse XML / HTML
        # - Normalización

        return []

    def _fetch_sale_rcv(self, company, certificate, year, month):
        """
        Obtiene RCV Ventas desde SII
        (Implementación real en siguiente etapa)
        """
        _logger.info("RCV SII | Descargando VENTAS")

        return []
