# -*- coding: utf-8 -*-

import base64
import csv
from io import StringIO
from datetime import datetime

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvImportWizard(models.TransientModel):
    _name = "rcv.import.wizard"
    _description = "Importar Libro RCV desde CSV SII"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    year = fields.Integer(required=True)
    month = fields.Integer(required=True)

    rcv_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
        ],
        required=True,
    )

    csv_file = fields.Binary(
        string="Archivo CSV RCV",
        required=True,
    )

    filename = fields.Char()

    # ---------------------------------------------------------
    # UTILIDADES ROBUSTAS PARA CSV SII
    # ---------------------------------------------------------
    def _clean_header(self, value):
        if not value:
            return None
        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

    def _clean_value(self, value):
        if value is None:
            return ""
        if isinstance(value, list):
            return " ".join([str(v) for v in value if v]).strip()
        return str(value).strip()

    def _to_float(self, value):
        if not value:
            return 0.0
        return float(
            value.replace(".", "")
            .replace(",", ".")
            .replace("$", "")
            .strip()
        )

    def _to_date(self, value):
        if not value:
            return False
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except Exception:
                continue
        return False

    # ---------------------------------------------------------
    # ACCIÓN PRINCIPAL
    # ---------------------------------------------------------
    def action_import(self):
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_("Debe seleccionar un archivo CSV del SII."))

        # -----------------------------------------------------
        # Crear libro RCV
        # -----------------------------------------------------
        book = self.env["rcv.book"].create({
            "company_id": self.company_id.id,
            "year": self.year,
            "month": self.month,
            "rcv_type": self.rcv_type,
            "state": "imported",
        })

        # -----------------------------------------------------
        # Leer CSV
        # -----------------------------------------------------
        decoded = base64.b64decode(self.csv_file)
        content = decoded.decode("utf-8", errors="ignore")

        reader = csv.DictReader(
            StringIO(content),
            delimiter=";"
        )

        if not reader.fieldnames:
            raise UserError(_("El archivo CSV no contiene encabezados válidos."))

        Line = self.env["rcv.line"]

        # -----------------------------------------------------
        # Procesar líneas (ANTI CSV SII)
        # -----------------------------------------------------
        for raw_row in reader:
            row = {}

            for key, value in raw_row.items():
                # 🔴 CLAVE: ignorar columnas inválidas del SII
                if not key:
                    continue

                clean_key = self._clean_header(key)
                if not clean_key:
                    continue

                row[clean_key] = self._clean_value(value)

            # -------------------------------------------------
            # Crear línea RCV
            # -------------------------------------------------
            Line.create({
                "book_id": book.id,

                "tipo_dte": (
                    row.get("tipo_doc")
                    or row.get("tipo_documento")
                ),
                "folio": row.get("folio"),

                "partner_vat": (
                    row.get("rut_emisor")
                    or row.get("rut_proveedor")
                    or row.get("rut_cliente")
                ),
                "partner_name": (
                    row.get("razon_social")
                    or row.get("razon_social_emisor")
                ),

                "invoice_date": self._to_date(
                    row.get("fecha_emision")
                    or row.get("fecha_documento")
                ),

                "net_amount": self._to_float(row.get("monto_neto")),
                "tax_amount": self._to_float(row.get("iva")),
                "total_amount": self._to_float(row.get("monto_total")),

                "match_state": "not_found",
            })

        # -----------------------------------------------------
        # Abrir libro creado
        # -----------------------------------------------------
        return {
            "type": "ir.actions.act_window",
            "name": _("Libro RCV"),
            "res_model": "rcv.book",
            "view_mode": "form",
            "res_id": book.id,
            "target": "current",
        }
