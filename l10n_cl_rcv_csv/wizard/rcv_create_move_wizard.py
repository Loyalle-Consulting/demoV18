# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RcvCreateMoveWizard(models.TransientModel):
    _name = "rcv.create.move.wizard"
    _description = "Crear facturas desde líneas RCV"

    company_id = fields.Many2one(
        "res.company",
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
    # ACCIÓN PRINCIPAL
    # ---------------------------------------------------------

    def action_create_moves(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("No hay líneas RCV seleccionadas."))

        AccountMove = self.env["account.move"]
        Partner = self.env["res.partner"]
        Tax = self.env["account.tax"]
        DocType = self.env["l10n_cl.document.type"]

        created_moves = AccountMove

        for line in self.line_ids:

            if line.account_move_id:
                continue

            # ---------------------------------------------
            # Tipo de documento / diario
            # ---------------------------------------------
            if line.book_id.rcv_type == "sale":
                move_type = "out_refund" if line.tipo_dte == "61" else "out_invoice"
                journal_type = "sale"
                tax_use = "sale"
            else:
                move_type = "in_refund" if line.tipo_dte == "61" else "in_invoice"
                journal_type = "purchase"
                tax_use = "purchase"

            journal = self.env["account.journal"].search([
                ("type", "=", journal_type),
                ("company_id", "=", self.company_id.id),
            ], limit=1)

            if not journal:
                raise UserError(_("No existe diario válido para %s.") % journal_type)

            # ---------------------------------------------
            # Partner
            # ---------------------------------------------
            partner = Partner.search(
                [("vat", "=", line.partner_vat)],
                limit=1,
            )

            if not partner:
                raise UserError(
                    _("El RUT %s no existe como contacto.") % line.partner_vat
                )

            # ---------------------------------------------
            # Tipo de documento SII
            # ---------------------------------------------
            doc_type = DocType.search([
                ("code", "=", line.tipo_dte),
                ("country_id.code", "=", "CL"),
            ], limit=1)

            if not doc_type:
                raise UserError(_("No existe tipo DTE %s en Odoo.") % line.tipo_dte)

            # ---------------------------------------------
            # Impuesto IVA
            # ---------------------------------------------
            taxes = False
            if line.tipo_dte != "34" and line.tax_amount:
                taxes = Tax.search([
                    ("type_tax_use", "=", tax_use),
                    ("amount", "=", 19),
                    ("company_id", "=", self.company_id.id),
                ], limit=1)

            # ---------------------------------------------
            # Crear factura
            # ---------------------------------------------
            move = AccountMove.create({
                "move_type": move_type,
                "company_id": self.company_id.id,
                "partner_id": partner.id,
                "journal_id": journal.id,
                "invoice_date": line.invoice_date,
                "date": line.accounting_date,
                "l10n_cl_document_type_id": doc_type.id,
                "ref": f"RCV DTE {line.tipo_dte} Folio {line.folio}",
                "invoice_line_ids": [
                    (0, 0, {
                        "name": f"DTE {line.tipo_dte} Folio {line.folio}",
                        "quantity": 1,
                        "price_unit": line.net_amount or 0.0,
                        "tax_ids": [(6, 0, taxes.ids)] if taxes else False,
                    })
                ],
            })

            move.action_post()

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
