# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvCreateMoveWizard(models.TransientModel):
    _name = "rcv.create.move.wizard"
    _description = "Crear facturas desde líneas RCV"

    # ---------------------------------------------------------
    # CAMPOS
    # ---------------------------------------------------------

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )

    line_ids = fields.Many2many(
        "rcv.line",
        string="Líneas RCV",
        readonly=True,
    )

    # ---------------------------------------------------------
    # DEFAULTS
    # ---------------------------------------------------------

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            res["line_ids"] = [(6, 0, active_ids)]
        return res

    # ---------------------------------------------------------
    # ACCIÓN PRINCIPAL
    # ---------------------------------------------------------

    def action_create_moves(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("No hay líneas RCV seleccionadas."))

        AccountMove = self.env["account.move"]
        Partner = self.env["res.partner"]

        created_moves = AccountMove

        for line in self.line_ids:

            # -------------------------------------------------
            # Evitar duplicados
            # -------------------------------------------------
            if line.account_move_id:
                continue

            # -------------------------------------------------
            # Determinar tipo (venta / compra)
            # -------------------------------------------------
            if line.book_id.rcv_type == "sale":
                move_type = "out_refund" if line.tipo_dte == "61" else "out_invoice"
                journal_type = "sale"
            else:
                move_type = "in_refund" if line.tipo_dte == "61" else "in_invoice"
                journal_type = "purchase"

            # -------------------------------------------------
            # Obtener diario correcto
            # -------------------------------------------------
            journal = self.env["account.journal"].search([
                ("type", "=", journal_type),
                ("company_id", "=", self.company_id.id),
            ], limit=1)

            if not journal:
                raise UserError(_(
                    "No existe un diario de tipo %s para la empresa."
                ) % ("Ventas" if journal_type == "sale" else "Compras"))

            # -------------------------------------------------
            # Obtener o crear partner
            # -------------------------------------------------
            partner = Partner.search(
                [("vat", "=", line.partner_vat)],
                limit=1,
            )

            if not partner:
                partner = Partner.create({
                    "name": line.partner_name or _("Tercero RCV"),
                    "vat": line.partner_vat,
                    "company_type": "company",
                })

            # -------------------------------------------------
            # Crear factura
            # -------------------------------------------------
            move = AccountMove.create({
                "move_type": move_type,
                "company_id": self.company_id.id,
                "partner_id": partner.id,
                "journal_id": journal.id,
                "invoice_date": line.invoice_date,
                "date": line.accounting_date,
                "ref": f"RCV DTE {line.tipo_dte} Folio {line.folio}",
                "invoice_line_ids": [
                    (0, 0, {
                        "name": f"DTE {line.tipo_dte} Folio {line.folio}",
                        "quantity": 1,
                        "price_unit": line.net_amount or 0.0,
                    })
                ],
            })

            move.action_post()

            # -------------------------------------------------
            # Marcar línea RCV
            # -------------------------------------------------
            line.account_move_id = move.id
            line.match_state = "created"

            created_moves |= move

        if not created_moves:
            raise UserError(_("No se creó ninguna factura nueva."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Facturas creadas desde RCV"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("id", "in", created_moves.ids)],
            "context": {"create": False},
        }
