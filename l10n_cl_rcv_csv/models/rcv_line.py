# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvLine(models.Model):
    _name = "rcv.line"
    _description = "Línea RCV SII"
    _order = "invoice_date asc nulls last, folio"

    # =====================================================
    # RELACIÓN CON LIBRO
    # =====================================================
    book_id = fields.Many2one(
        "rcv.book",
        string="Libro RCV",
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        related="book_id.company_id",
        store=True,
        readonly=True,
    )

    # =====================================================
    # DATOS DOCUMENTO SII
    # =====================================================
    tipo_dte = fields.Char(
        string="DTE",
        required=True,
    )

    folio = fields.Char(
        string="Folio",
        required=True,
    )

    partner_vat = fields.Char(string="RUT")
    partner_name = fields.Char(string="Razón Social")

    invoice_date = fields.Date(string="Fecha Documento", store=True)
    accounting_date = fields.Date(string="Fecha Contable", store=True)

    # =====================================================
    # MONTOS
    # =====================================================
    net_amount = fields.Monetary(string="Neto", currency_field="currency_id")
    tax_amount = fields.Monetary(string="IVA", currency_field="currency_id")
    total_amount = fields.Monetary(string="Total", currency_field="currency_id")

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # =====================================================
    # CONCILIACIÓN
    # =====================================================
    match_state = fields.Selection(
        [
            ("not_found", "No existe en Odoo"),
            ("matched", "Cuadra"),
            ("amount_diff", "Diferencia de monto"),
            ("created", "Documento creado"),
        ],
        default="not_found",
        required=True,
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Documento Odoo",
        readonly=True,
    )

    # =====================================================
    # CREACIÓN DOCUMENTO CONTABLE
    # =====================================================
    def _create_account_move_from_rcv(self):
        self.ensure_one()

        if self.account_move_id:
            return self.account_move_id

        if not self.partner_vat:
            raise UserError(_("La línea RCV no tiene RUT."))

        partner = self.env["res.partner"].search(
            [("vat", "=", self.partner_vat)],
            limit=1,
        )

        if not partner:
            raise UserError(_("No existe el contacto con RUT %s.") % self.partner_vat)

        # ---------------------------------------------
        # TIPO DE MOVIMIENTO SEGÚN DTE
        # ---------------------------------------------
        if self.tipo_dte == "61":
            move_type = (
                "out_refund"
                if self.book_id.rcv_type == "sale"
                else "in_refund"
            )
        else:
            move_type = (
                "out_invoice"
                if self.book_id.rcv_type == "sale"
                else "in_invoice"
            )

        # ---------------------------------------------
        # DIARIO
        # ---------------------------------------------
        journal_type = "sale" if move_type.startswith("out_") else "purchase"
        journal = self.env["account.journal"].search(
            [
                ("type", "=", journal_type),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        if not journal:
            raise UserError(_("No existe diario contable válido."))

        # ---------------------------------------------
        # TIPO DOCUMENTO LATAM
        # ---------------------------------------------
        latam_doc_type = self.env["l10n_latam.document.type"].search(
            [
                ("code", "=", self.tipo_dte),
                ("country_id.code", "=", "CL"),
            ],
            limit=1,
        )

        if not latam_doc_type:
            raise UserError(
                _("No se encontró tipo de documento LATAM para DTE %s.") % self.tipo_dte
            )

        # ---------------------------------------------
        # IMPUESTOS (REGLA CORRECTA)
        # ---------------------------------------------
        tax_ids = []
        if self.tax_amount and self.tax_amount > 0:
            tax = self.env["account.tax"].search(
                [
                    ("name", "ilike", "IVA"),
                    ("type_tax_use", "=", "sale" if move_type.startswith("out_") else "purchase"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if tax:
                tax_ids = [(6, 0, tax.ids)]

        # ---------------------------------------------
        # CREAR DOCUMENTO
        # ---------------------------------------------
        move = self.env["account.move"].create({
            "move_type": move_type,
            "company_id": self.company_id.id,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": self.invoice_date,
            "date": self.accounting_date or self.invoice_date,
            # 🔴 FOLIO REAL SII (ESTE ES EL IMPORTANTE)
            "l10n_latam_document_type_id": latam_doc_type.id,
            "l10n_latam_document_number": self.folio,
            "ref": f"RCV DTE {self.tipo_dte} Folio {self.folio}",
            "invoice_line_ids": [
                (0, 0, {
                    "name": f"RCV DTE {self.tipo_dte} Folio {self.folio}",
                    "quantity": 1,
                    "price_unit": self.net_amount or 0.0,
                    "tax_ids": tax_ids,
                })
            ],
        })

        move.action_post()

        self.account_move_id = move.id
        self.match_state = "created"

        return move

    # =====================================================
    # COMPATIBILIDAD
    # =====================================================
    def action_create_invoice(self):
        self.ensure_one()
        return self._create_account_move_from_rcv()
