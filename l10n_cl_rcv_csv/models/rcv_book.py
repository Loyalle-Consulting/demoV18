# -*- coding: utf-8 -*-

from odoo import models, fields, _


class RcvBook(models.Model):
    _name = "rcv.book"
    _description = "Libro RCV CSV SII"
    _order = "year desc, month desc"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    year = fields.Integer(
        string="Año",
        required=True,
    )

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
        string="Tipo RCV",
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("imported", "Importado"),
            ("compared", "Conciliado"),
            ("posted", "Facturas creadas"),
        ],
        string="Estado",
        default="imported",
        tracking=True,
    )

    line_ids = fields.One2many(
        "rcv.line",
        "book_id",
        string="Líneas RCV",
    )

    # ======================================================
    # ACCIÓN: Conciliar con Contabilidad
    # (stub inicial, lógica real se agrega después)
    # ======================================================
    def action_reconcile_with_accounting(self):
        """
        Conciliación RCV vs contabilidad Odoo.
        Por ahora solo cambia estado para permitir instalación.
        """
        for book in self:
            book.state = "compared"
