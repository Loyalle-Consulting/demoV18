# -*- coding: utf-8 -*-

import base64
import csv
import io
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
    # ACCIÓN PRINCIPAL
    # ---------------------------------------------------------
    def action_import(self):
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_("Debe seleccionar un archivo CSV."))

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
        data = io.StringIO(decoded.decode("utf-8", errors="ignore"))
        reader = csv.DictReader(data, delimiter=";")

        Line = self.env["rcv.line"]

        for row in reader:
            # --- Conversión de montos ---
            def _to_float(val):
                if not val:
                    return 0.0
                return float(val.replace(".", "").replace(",", "."))

            net = _to_float(row.get("Monto Neto"))
            tax = _to_float(row.get("IVA"))
            total = _to_float(row.get("Monto Total"))

            # --- Fecha ---
            date_str = row.get("Fecha Documento")
            invoice_date = False
            if date_str:
                try:
                    invoice_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                except Exception:
                    pass

            # -------------------------------------------------
            # CREAR LÍNEA RCV
            # -------------------------------------------------
            Line.create({
                "book_id": book.id,
                "tipo_dte": row.get("Tipo Documento"),
                "folio": row.get("Folio"),
                "partner_vat": row.get("RUT Proveedor") or row.get("RUT Cliente"),
                "partner_name": row.get("Razón Social"),
                "invoice_date": invoice_date,
                "net_amount": net,
                "tax_amount": tax,
                "total_amount": total,

                # 🔴 CLAVE: estado válido según el modelo
                "match_state": "not_found",
            })

        # -----------------------------------------------------
        # Volver al libro creado
        # -----------------------------------------------------
        return {
            "type": "ir.actions.act_window",
            "name": _("Libro RCV"),
            "res_model": "rcv.book",
            "view_mode": "form",
            "res_id": book.id,
            "target": "current",
        }
