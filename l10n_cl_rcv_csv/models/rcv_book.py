from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvBook(models.Model):
    _name = "rcv.book"
    _description = "Libro RCV SII"
    _order = "year desc, month desc"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )

    year = fields.Integer(
        string="Año",
        required=True,
    )

    month = fields.Integer(
        string="Mes",
        required=True,
    )

    rcv_type = fields.Selection(
        [
            ("purchase", "Compras"),
            ("sale", "Ventas"),
        ],
        string="Tipo Libro",
        required=True,
    )

    state = fields.Selection(
        [
            ("imported", "Importado"),
            ("compared", "Comparado"),
            ("posted", "Facturas creadas"),
        ],
        string="Estado",
        default="imported",
        required=True,
    )

    line_ids = fields.One2many(
        "rcv.line",
        "book_id",
        string="Líneas RCV",
    )

    # =========================================================
    # ACCIÓN: Conciliar con Contabilidad
    # =========================================================
    def action_reconcile_with_accounting(self):
        """
        Placeholder inicial.
        En el siguiente paso aquí se implementará:
        - búsqueda de account.move
        - comparación por RUT / folio / monto
        - actualización de match_state
        """
        for book in self:
            if not book.line_ids:
                raise UserError(_("Este libro no tiene líneas para conciliar."))

            # Por ahora solo marcamos estado como "compared"
            book.state = "compared"

        return True
