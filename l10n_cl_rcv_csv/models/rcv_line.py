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

    company_id = fields.Many2one(
        related="book_id.company_id",
        store=True,
        readonly=True,
    )

    # =====================================================
    # DATOS DOCUMENTO SII
    # =====================================================
    tipo_dte = fields.Char(
        string="Tipo DTE",
        help="Código DTE según SII (33, 34, 61, etc.)",
    )

    folio = fields.Char(
        string="Folio",
    )

    invoice_date = fields.Date(
        string="Fecha Documento",
        help="Fecha del documento (FchDoc del CSV SII)",
    )

    accounting_date = fields.Date(
        string="Fecha Contable",
        help="Fecha contable Odoo (FchRecep del CSV SII)",
    )

    rut = fields.Char(
        string="RUT",
    )

    razon_social = fields.Char(
        string="Razón Social",
    )

    # =====================================================
    # MONTOS
    # =====================================================
    amount_net = fields.Monetary(
        string="Neto",
        currency_field="currency_id",
    )

    amount_tax = fields.Monetary(
        string="IVA",
        currency_field="currency_id",
    )

    amount_total = fields.Monetary(
        string="Total",
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id.id,
        readonly=True,
    )

    # =====================================================
    # COMPARACIÓN CONTABLE (SE USARÁ DESPUÉS)
    # =====================================================
    state = fields.Selection(
        [
            ("draft", "Importado"),
            ("matched", "Existe en Odoo"),
            ("difference", "Diferencia con Odoo"),
            ("not_found", "No existe en Odoo"),
        ],
        string="Estado",
        default="draft",
    )

    move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
        readonly=True,
    )

    # =====================================================
    # RESTRICCIONES BÁSICAS
    # =====================================================
    _sql_constraints = [
        (
            "unique_document_per_book",
            "unique(book_id, tipo_dte, folio)",
            "El documento ya existe en este libro RCV.",
        ),
    ]
