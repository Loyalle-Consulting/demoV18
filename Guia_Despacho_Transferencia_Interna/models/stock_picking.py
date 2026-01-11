from odoo import api, fields, models, _
from odoo.exceptions import UserError
import inspect

ALT_METHOD_CANDIDATES = [
    'action_create_delivery_guide',
    '_action_create_delivery_guide',
    'action_generate_delivery_guide',
    'button_create_delivery_guide',
    'button_generate_delivery_guide',
    'create_delivery_guide',
    'action_open_create_delivery_guide',
    'action_open_delivery_guide_wizard',
]

class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_cl_internal_dispatch = fields.Boolean(
        string="Guía de Traslado Interno",
        help="Marcar si esta transferencia interna requiere Guía de Despacho Electrónica (DTE 52).",
        default=False,
    )
    l10n_cl_internal_dispatch_created = fields.Boolean(
        string="Guía DTE creada",
        help="Marcado automáticamente cuando se genere la Guía de Despacho Electrónica para este traslado interno.",
        default=False,
        readonly=True,
    )

    def _l10n_cl_int_find_create_method(self):
        found_names = []
        try:
            for name, member in inspect.getmembers(type(self), predicate=inspect.isfunction):
                if 'guide' in name or 'delivery' in name:
                    found_names.append(name)
        except Exception:
            pass
        for name in ALT_METHOD_CANDIDATES:
            method = getattr(self, name, None)
            if callable(method):
                return method, name, found_names
        return None, None, found_names

    def action_open_internal_dispatch_wizard(self):
        self.ensure_one()
        if self.picking_type_code != "internal":
            raise UserError(_("Esta acción solo está disponible en transferencias internas."))
        if not self.move_ids_without_package:
            raise UserError(_("No hay líneas de movimiento para emitir una Guía."))
        if not self.env['ir.module.module'].sudo().search_count([('name', '=', 'l10n_cl_edi_stock'), ('state', '=', 'installed')]):
            raise UserError(_("Falta instalar el módulo enterprise 'l10n_cl_edi_stock'."))

        return {
            'name': _('Guía de Despacho (Traslado Interno)'),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_cl.internal.dispatch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_receptor_partner_id': self.company_id.partner_id.id,
            }
        }

    def _l10n_cl_get_doc_type_52(self):
        return self.env['l10n_latam.document.type'].search([
            ('code', '=', '52'),
            ('country_id', '=', self.company_id.country_id.id)
        ], limit=1)

    def action_create_internal_delivery_guide(self, receptor_partner_id=False, transport_vals=None, reference_reason="Traslado Interno"):
        self.ensure_one()
        if self.picking_type_code != 'internal':
            raise UserError(_("Solo disponible para transferencias internas."))

        doc_type_52 = self._l10n_cl_get_doc_type_52()
        if not doc_type_52:
            raise UserError(_("No existe definido el documento 52 (Guía) en l10n_latam.document.type para Chile."))

        if not receptor_partner_id:
            receptor_partner_id = self.company_id.partner_id.id

        partner = self.env['res.partner'].browse(receptor_partner_id)
        if not partner.vat:
            raise UserError(_("El receptor debe tener RUT (VAT) configurado."))

        vals = {'partner_id': partner.id, 'l10n_cl_internal_dispatch': True}
        for f in ('l10n_latam_document_type_id', 'l10n_cl_document_type_id'):
            if f in self._fields:
                vals[f] = doc_type_52.id
                break
        self.write(vals)

        if transport_vals:
            write_transport = {k: v for k, v in (transport_vals or {}).items() if k in self._fields}
            if write_transport:
                self.write(write_transport)

        create_method, method_name, suggestions = self._l10n_cl_int_find_create_method()
        if not create_method:
            self.message_post(body=_("No se encontró un método enterprise conocido para crear la Guía. Métodos detectados: %s") % (', '.join(suggestions) or '—'))
            raise UserError(_("No se encontró el método para crear Guía en 'l10n_cl_edi_stock'. Verifica la versión del módulo."))

        action = create_method()
        self.l10n_cl_internal_dispatch_created = True

        if hasattr(self, 'l10n_cl_add_reference') and reference_reason:
            try:
                self.l10n_cl_add_reference(reference_reason, code='6', origin=self.name or self.origin)
            except Exception:
                pass

        return action

    def button_validate(self):
        res = super().button_validate()
        for pick in self.filtered(lambda p: p.picking_type_code == 'internal' and p.l10n_cl_internal_dispatch and not p.l10n_cl_internal_dispatch_created):
            try:
                pick.action_create_internal_delivery_guide()
                pick.message_post(body=_("Guía de Despacho Electrónica creada automáticamente al validar el traslado interno."))
            except Exception as e:
                pick.message_post(body=_("No se pudo generar la Guía DTE automática: %s") % (e,))
        return res