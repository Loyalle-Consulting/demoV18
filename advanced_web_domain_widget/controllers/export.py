from odoo import http
from odoo.exceptions import UserError
from odoo.addons.web.controllers.export import Export
from odoo.http import request

class Export(Export):

    # def fields_get(self, model):
    #     fields=super().fields_get(model)
    #     invisible_field_ids = request.env['hide.field'].search(
    #                     [('access_management_id.company_ids', 'in', request.env.company.id),
    #                      ('model_id.model', '=', model), ('access_management_id.active', '=', True),
    #                     ('access_management_id.user_ids', 'in', request.env.user.id),
    #                      ('invisible','=',True)])
    #     if not invisible_field_ids:
    #         return fields
    #     else :
    #         for key, value in list(fields.items()):
    #             for invisible_field in invisible_field_ids.field_id:
    #                 if key == invisible_field.name and key != "id":
    #                     del fields[key]
    #         return fields


    @http.route('/web/export/get_fields', type='json', auth='user', readonly=True)
    def get_fields(self, model, domain, prefix='', parent_name='',
                   import_compat=True, parent_field_type=None,
                   parent_field=None, exclude=None):
        result = super(Export,self).get_fields(model, domain, prefix=prefix, parent_name=parent_name,
                   import_compat=import_compat, parent_field_type=parent_field_type,
                   parent_field=parent_field, exclude=exclude)
        
        invisible_field_ids = request.env['hide.field'].sudo().search(
                        [('model_id.model', '=', request.params.get('model')),
                         ('access_management_id.active', '=', True),
                         ('access_management_id.user_ids', 'in', request.env.user.id),
                         ('invisible','=',True)])
        
        invisible_field_ids -= invisible_field_ids.filtered(lambda x: x.access_management_id.is_apply_on_without_company == False and request.env.company.id not in x.access_management_id.company_ids.ids)
        
        invisible_field_list = invisible_field_ids.mapped('field_id.name')

        for fields in result:
            if fields.get('id') in invisible_field_list:
                result.remove(fields)

        return result        