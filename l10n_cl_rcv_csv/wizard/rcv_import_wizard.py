# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvImportWizard(models.TransientModel):
    _name = "rcv.import.wizard"
    _description = "Importar CSV RCV SII"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    year = fields.Integer(string="Año", required=True)
    month = fields.Selection(
        [(str(i), str(i)) for i in range(1, 13)],
        string="Mes",
        required=True,
    )

    rcv_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
        ],
        string="Tipo de libro",
        required=True,
    )

    csv_file = fields.Binary(
        string="Archivo CSV SII",
        required=True,
    )

    filename = fields.Char(string="Nombre archivo")

    # ---------------------------------------------------------
    # ACCIÓN
    # ---------------------------------------------------------
    def action_import(self):
        self.ensure_one()

        Book = self.env["rcv.book"]
        Line = self.env["rcv.line"]
        parser = self.env["rcv.csv.parser"]

        # Crear libro RCV
        book = Book.create({
            "company_id": self.company_id.id,
            "year": self.year,
            "month": self.month,
            "rcv_type": self.rcv_type,
            "state": "imported",
        })

        rows = parser.parse(self.csv_file, self.rcv_type)

        for row in rows:
            Line.create({
                "book_id": book.id,
                "rcv_type": row["rcv_type"],
                "document_type": row["tipo_dte"],
                "folio": row["folio"],
                "partner_vat": row["rut"],
                "partner_name": row["razon_social"],
                "document_date": row["fecha"],
                "net_amount": row["neto"],
                "tax_amount": row["iva"],
                "total_amount": row["total"],
                "match_state": "not_checked",
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("Libro RCV importado"),
            "res_model": "rcv.book",
            "view_mode": "form",
            "res_id": book.id,
        }