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
        help="Código DTE según SII (33, 34, 61, etc.)",
        required=True,
    )

    folio = fields.Char(
        string="Folio",
        required=True,
    )

    partner_vat = fields.Char(string="RUT")
    partner_name = fields.Char(string="Razón Social")

    invoice_date = fields.Date(
        string="Fecha Documento",
        store=True,
        index=True,
    )

    accounting_date = fields.Date(
        string="Fecha Contable",
        store=True,
        index=True,
    )

    # =====================================================
    # MONTOS
    # =====================================================
    net_amount = fields.Monetary(
        string="Neto",
        currency_field="currency_id",
    )

    tax_amount = fields.Monetary(
        string="IVA",
        currency_field="currency_id",
    )

    total_amount = fields.Monetary(
        string="Total",
        currency_field="currency_id",
    )

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
    # MÉTODO OFICIAL DE FACTURACIÓN (OPCIÓN A)
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
            raise UserError(
                _("No existe el contacto con RUT %s.") % self.partner_vat
            )

        # -------------------------------------------------
        # DETERMINAR TIPO DE MOVIMIENTO SEGÚN DTE
        # -------------------------------------------------
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

        # -------------------------------------------------
        # DIARIO
        # -------------------------------------------------
        journal_type = "sale" if move_type in ("out_invoice", "out_refund") else "purchase"
        journal = self.env["account.journal"].search(
            [
                ("type", "=", journal_type),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        if not journal:
            raise UserError(_("No existe diario contable válido."))

        # -------------------------------------------------
        # TIPO DOCUMENTO LATAM
        # -------------------------------------------------
        latam_doc_type = self._get_latam_document_type()
        if not latam_doc_type:
            raise UserError(
                _("No se encontró el tipo de documento LATAM para DTE %s.")
                % self.tipo_dte
            )

        # -------------------------------------------------
        # IMPUESTOS
        # -------------------------------------------------
        tax_ids = self._get_tax_ids()

        # -------------------------------------------------
        # CREAR DOCUMENTO CONTABLE
        # -------------------------------------------------
        move = self.env["account.move"].create({
            "move_type": move_type,
            "company_id": self.company_id.id,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": self.invoice_date,
            "date": self.accounting_date or self.invoice_date,
            "l10n_latam_document_type_id": latam_doc_type.id,
            # ⚠️ NO se fuerza el número legal
            "ref": f"RCV DTE {self.tipo_dte} Folio {self.folio}",
            "invoice_line_ids": [
                (0, 0, {
                    "name": f"RCV DTE {self.tipo_dte} Folio {self.folio}",
                    "quantity": 1,
                    "price_unit": self.net_amount or 0.0,
                    "tax_ids": [(6, 0, tax_ids.ids)],
                })
            ],
        })

        move.action_post()

        self.account_move_id = move.id
        self.match_state = "created"

        return move

    # =====================================================
    # HELPERS CHILE
    # =====================================================
    def _get_latam_document_type(self):
        return self.env["l10n_latam.document.type"].search(
            [
                ("code", "=", self.tipo_dte),
                ("country_id.code", "=", "CL"),
            ],
            limit=1,
        )

    def _get_tax_ids(self):
        if self.tipo_dte in ("34", "61"):
            return self.env["account.tax"]

        return self.env["account.tax"].search(
            [
                ("name", "ilike", "IVA"),
                ("type_tax_use", "=", "sale"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

    # =====================================================
    # COMPATIBILIDAD
    # =====================================================
    def action_create_invoice(self):
        self.ensure_one()
        return self._create_account_move_from_rcv()
