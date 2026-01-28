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

    create_type = fields.Selection(
        [
            ("invoice", "Factura"),
            ("refund", "Nota de Crédito"),
        ],
        string="Tipo de documento",
        required=True,
        default="invoice",
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Diario contable",
        required=True,
        domain="[('type', 'in', ('sale', 'purchase'))]",
    )

    invoice_date = fields.Date(
        string="Fecha de factura",
        required=True,
        default=fields.Date.context_today,
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

        active_ids = self.env.context.get("active_ids")
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

        created_moves = self.env["account.move"]

        for line in self.line_ids:

            if line.account_move_id:
                continue  # ya conciliado

            partner = self._get_or_create_partner(line)

            move_type = self._get_move_type(line)

            move_vals = {
                "move_type": move_type,
                "company_id": self.company_id.id,
                "partner_id": partner.id,
                "journal_id": self.journal_id.id,
                "invoice_date": self.invoice_date,
                "invoice_date_due": self.invoice_date,
                "ref": f"RCV DTE {line.tipo_dte} Folio {line.folio}",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": f"DTE {line.tipo_dte} Folio {line.folio}",
                            "quantity": 1,
                            "price_unit": line.net_amount or 0.0,
                        },
                    )
                ],
            }

            move = self.env["account.move"].create(move_vals)

            # Publicar factura
            move.action_post()

            # Vinculación RCV ↔ factura
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
        }

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def _get_move_type(self, line):
        rcv_type = line.book_id.rcv_type

        if rcv_type == "purchase":
            return "in_refund" if self.create_type == "refund" else "in_invoice"
        else:
            return "out_refund" if self.create_type == "refund" else "out_invoice"

    def _get_or_create_partner(self, line):
        Partner = self.env["res.partner"]

        partner = Partner.search(
            [("vat", "=", line.partner_vat)],
            limit=1,
        )

        if partner:
            return partner

        return Partner.create({
            "name": line.partner_name or _("Proveedor/Cliente RCV"),
            "vat": line.partner_vat,
            "company_type": "company",
        })
