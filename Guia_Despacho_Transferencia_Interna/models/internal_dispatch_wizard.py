from odoo import api, fields, models, _
from odoo.exceptions import UserError

class InternalDispatchWizard(models.TransientModel):
    _name = 'l10n_cl.internal.dispatch.wizard'
    _description = 'Wizard Guía de Despacho para Traslado Interno'

    picking_id = fields.Many2one('stock.picking', required=True)
    receptor_partner_id = fields.Many2one('res.partner', string='Receptor (Sucursal/Empresa destino)', required=True, help="Receptor de la mercadería. Puede ser tu propia empresa/sucursal.")

    vehicle_plate = fields.Char(string='Patente Vehículo')
    driver_name = fields.Char(string='Conductor')
    driver_vat = fields.Char(string='RUT Conductor')
    dispatch_reason = fields.Char(string='Motivo', default='Traslado Interno')

    def action_confirm(self):
        self.ensure_one()
        if self.picking_id.state not in ('assigned', 'done', 'confirmed'):
            raise UserError(_("Primero reserva/valida la transferencia o deja las cantidades listas para enviar."))

        transport_vals = {}
        for f in ('vehicle_plate', 'driver_name', 'driver_vat'):
            if self[f] and f in self.picking_id._fields:
                transport_vals[f] = self[f]
        return self.picking_id.action_create_internal_delivery_guide(
            receptor_partner_id=self.receptor_partner_id.id,
            transport_vals=transport_vals,
            reference_reason=self.dispatch_reason or 'Traslado Interno',
        )