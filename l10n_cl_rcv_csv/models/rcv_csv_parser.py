# -*- coding: utf-8 -*-

import base64
import csv
import io
from odoo import models, _
from odoo.exceptions import UserError


class RcvCsvParser(models.AbstractModel):
    _name = "rcv.csv.parser"
    _description = "Parser CSV RCV SII (Compras y Ventas)"

    def parse(self, file_binary, rcv_type):
        """
        rcv_type: 'purchase' | 'sale'
        """

        if not file_binary:
            raise UserError(_("No se ha cargado ningún archivo CSV."))

        try:
            content = base64.b64decode(file_binary)
            text = content.decode("latin-1")
        except Exception:
            raise UserError(_("No fue posible leer el archivo CSV (encoding inválido)."))

        reader = csv.DictReader(io.StringIO(text), delimiter=";")

        rows = []
        for row in reader:
            rows.append(self._normalize_row(row, rcv_type))

        if not rows:
            raise UserError(_("El archivo CSV no contiene registros válidos."))

        return rows

    # ---------------------------------------------------------
    # NORMALIZACIÓN SEGÚN CSV OFICIAL SII
    # ---------------------------------------------------------
    def _normalize_row(self, row, rcv_type):

        def clean(val):
            return (val or "").strip()

        def to_float(val):
            try:
                return float(val.replace(".", "").replace(",", "."))
            except Exception:
                return 0.0

        return {
            "rcv_type": rcv_type,
            "tipo_dte": clean(row.get("Tipo Doc")),
            "folio": clean(row.get("Folio")),
            "rut": clean(row.get("RUT Emisor") or row.get("RUT Receptor")),
            "razon_social": clean(row.get("Razón Social")),
            "fecha": clean(row.get("Fecha Emisión")),
            "neto": to_float(row.get("Monto Neto")),
            "iva": to_float(row.get("IVA")),
            "total": to_float(row.get("Monto Total")),
        }