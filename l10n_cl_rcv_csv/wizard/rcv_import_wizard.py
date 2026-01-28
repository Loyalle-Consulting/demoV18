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
    # UTILIDADES ROBUSTAS CSV SII
    # ---------------------------------------------------------
    def _clean_header(self, value):
        if not value:
            return None

        # 🔴 FIX CLAVE: eliminar BOM invisible del SII
        value = value.lstrip("\ufeff")

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
        return str(value).strip()

    def _to_float(self, value):
        if not value:
            return 0.0
        try:
            return float(
                value.replace(".", "")
                .replace(",", ".")
                .replace("$", "")
                .strip()
            )
        except Exception:
            return 0.0

    def _to_date(self, value):
        if not value:
            return False
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
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

        book = self.env["rcv.book"].create({
            "company_id": self.company_id.id,
            "year": self.year,
            "month": self.month,
            "rcv_type": self.rcv_type,
            "state": "imported",
        })

        decoded = base64.b64decode(self.csv_file)
        content = decoded.decode("latin-1", errors="ignore")

        reader = csv.DictReader(StringIO(content), delimiter=";")

        if not reader.fieldnames:
            raise UserError(_("El archivo CSV no contiene encabezados válidos."))

        Line = self.env["rcv.line"]

        for raw_row in reader:
            row = {}
            for key, value in raw_row.items():
                clean_key = self._clean_header(key)
                if clean_key:
                    row[clean_key] = self._clean_value(value)

            Line.create({
                "book_id": book.id,

                # Documento
                "tipo_dte": (
                    row.get("tipodte")
                    or row.get("tipodoc")
                    or row.get("tipo_doc")
                ),

                "folio": row.get("folio"),

                "partner_vat": (
                    row.get("rutdoc")
                    or row.get("rut_emisor")
                ),

                "partner_name": (
                    row.get("rznsoc")
                    or row.get("razon_social")
                ),

                # 🔑 FECHAS SII (YA FUNCIONAN)
                "invoice_date": self._to_date(row.get("fchdoc")),
                "accounting_date": self._to_date(row.get("fchrecep")),

                # Montos
                "net_amount": self._to_float(row.get("mntneto")),
                "tax_amount": self._to_float(row.get("iva")),
                "total_amount": self._to_float(row.get("mnttotal")),

                "match_state": "not_found",
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("Libro RCV"),
            "res_model": "rcv.book",
            "view_mode": "form",
            "res_id": book.id,
            "target": "current",
        }
