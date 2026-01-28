# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvLine(models.Model):
    _name = "rcv.line"
    _description = "Línea RCV SII"

    # 🔴 AJUSTE CLAVE: evitar pérdida de fechas al crear
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
    )

    folio = fields.Char(
        string="Folio",
        required=True,
    )

    partner_vat = fields.Char(
        string="RUT",
    )

    partner_name = fields.Char(
        string="Razón Social",
    )

    # 🔴 AJUSTE CLAVE: forzar persistencia explícita
    invoice_date = fields.Date(
        string="Fecha Documento",
        help="Fecha Docto proveniente del CSV del SII",
        store=True,
        index=True,
    )

    accounting_date = fields.Date(
        string="Fecha Contable",
        help="Fecha Recepción (fecha contable) del CSV del SII",
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
        string="Moneda",
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
            ("created", "Factura creada"),
        ],
        string="Estado Conciliación",
        default="not_found",
        required=True,
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
        readonly=True,
    )

    # =====================================================
    # ACCIÓN: CREAR FACTURA (UNA LÍNEA)
    # =====================================================
    def action_create_invoice(self):
        self.ensure_one()

        if self.account_move_id:
            return

        partner = False
        if self.partner_vat:
            partner = self.env["res.partner"].search(
                [("vat", "=", self.partner_vat)],
                limit=1,
            )

        if not partner:
            return self._open_create_invoice_wizard()

        if self.book_id.rcv_type == "sale":
            move_type = "out_invoice"
            journal_type = "sale"
        else:
            move_type = "in_invoice"
            journal_type = "purchase"

        journal = self.env["account.journal"].search(
            [
                ("type", "=", journal_type),
                ("company_id", "=", self.book_id.company_id.id),
            ],
            limit=1,
        )

        if not journal:
            raise UserError(
                _("No existe un diario contable configurado para %s.")
                % ("Ventas" if journal_type == "sale" else "Compras")
            )

        move = self.env["account.move"].create({
            "move_type": move_type,
            "company_id": self.book_id.company_id.id,
            "partner_id": partner.id,
            "invoice_date": self.invoice_date,
            "date": self.accounting_date,
            "journal_id": journal.id,
            "ref": f"RCV DTE {self.tipo_dte} Folio {self.folio}",
            "invoice_line_ids": [
                (0, 0, {
                    "name": f"DTE {self.tipo_dte or ''} Folio {self.folio}",
                    "quantity": 1,
                    "price_unit": self.net_amount or 0.0,
                })
            ],
        })

        move.action_post()

        self.account_move_id = move.id
        self.match_state = "created"

    # =====================================================
    # WIZARD ASISTIDO
    # =====================================================
    def _open_create_invoice_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Crear facturas desde RCV"),
            "res_model": "rcv.create.move.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_ids": self.ids,
                "active_model": "rcv.line",
            },
        }
