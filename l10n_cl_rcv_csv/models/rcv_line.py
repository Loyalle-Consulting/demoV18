# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvLine(models.Model):
    _name = "rcv.line"
    _description = "Línea RCV SII"
    _order = "invoice_date, folio"

    # =====================================================
    # RELACIÓN CON LIBRO
    # =====================================================
    book_id = fields.Many2one(
        "rcv.book",
        string="Libro RCV",
        required=True,
        ondelete="cascade",
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

    invoice_date = fields.Date(
        string="Fecha Documento",
        help="Fecha del documento informada en el RCV",
    )

    reception_date = fields.Date(
        string="Fecha Recepción SII",
        help="Fecha de recepción informada por el SII",
    )

    # =====================================================
    # MONTOS
    # =====================================================
    net_amount = fields.Monetary(
        string="Neto",
    )

    tax_amount = fields.Monetary(
        string="IVA",
    )

    total_amount = fields.Monetary(
        string="Total",
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
        """
        Crea una factura desde una línea RCV.
        Si falta información crítica (partner), abre el wizard asistido.
        """
        self.ensure_one()

        # Ya conciliado
        if self.account_move_id:
            return

        # -------------------------------------------------
        # Partner
        # -------------------------------------------------
        partner = False
        if self.partner_vat:
            partner = self.env["res.partner"].search(
                [("vat", "=", self.partner_vat)],
                limit=1,
            )

        if not partner:
            return self._open_create_invoice_wizard()

        # -------------------------------------------------
        # Tipo de factura según libro
        # -------------------------------------------------
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

        # -------------------------------------------------
        # Crear factura (línea única, RCV no trae detalle)
        # -------------------------------------------------
        move = self.env["account.move"].create({
            "move_type": move_type,
            "company_id": self.book_id.company_id.id,
            "partner_id": partner.id,
            "invoice_date": self.invoice_date,
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

        # Publicar
        move.action_post()

        # Vincular
        self.account_move_id = move.id
        self.match_state = "created"

    # =====================================================
    # WIZARD ASISTIDO (MASIVO / FALTA INFO)
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
