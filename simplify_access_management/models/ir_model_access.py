# -*- coding: utf-8 -*-
import logging
from odoo.http import request
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, AccessError
from odoo.tools import SQL, Query

_logger = logging.getLogger(__name__)


class ir_model_access(models.Model):
    _inherit = 'ir.model.access'


    @api.model
    def check(self, model, mode='read', raise_exception=True):
        if self.env.su:
            # User root have all accesses
            return True

        assert isinstance(model, str), 'Not a model name: %s' % (model,)
        is_model_exists = True
        if model not in self.env:
            _logger.error('Missing model %s', model)
            is_model_exists = False

        has_access = model in self._get_allowed_models(mode)
        
        
        """
            This part is writen to by pass base access rule and apply dynamic rule of access management rule,
            In case of any record found in access management.
        """
        try:
            value = self._cr.execute(SQL(
                """SELECT value from ir_config_parameter where key='uninstall_simplify_access_management' """))
            value = self._cr.fetchone()
            if not value:
                if is_model_exists:
                
                    self._cr.execute(SQL("SELECT id FROM ir_model WHERE model='%s'" % model))
                    model_numeric_id = self._cr.fetchone()[0]
                    if model_numeric_id and isinstance(model_numeric_id, int) and self.env.user:
                        self._cr.execute(SQL("""
                                        SELECT dm.id
                                        FROM access_domain_ah as dm
                                        WHERE dm.model_id=%s AND dm.apply_domain AND dm.access_management_id 
                                        IN (SELECT am.id 
                                            FROM access_management as am 
                                            WHERE active='t' AND am.id 
                                            IN (SELECT amusr.access_management_id
                                                FROM access_management_users_rel_ah as amusr
                                                WHERE amusr.user_id=%s))
                                        """% (model_numeric_id, self.env.user.id)))
                    
                        
                        access_domain_ah_ids = self.env['access.domain.ah'].sudo().browse(
                            row[0] for row in self._cr.fetchall())
                        access_domain_ah_ids -= access_domain_ah_ids.filtered(lambda x: x.access_management_id.is_apply_on_without_company == False and self.env.company.id not in x.access_management_id.company_ids.ids)
                        if mode == 'read':
                            access_domain_ah_ids = access_domain_ah_ids.filtered(lambda x: x.read_right)
                        elif mode == 'create':
                            access_domain_ah_ids = access_domain_ah_ids.filtered(lambda x: x.create_right)
                        elif mode == 'write':
                            access_domain_ah_ids = access_domain_ah_ids.filtered(lambda x: x.write_right)
                        elif mode == 'unlink':
                            access_domain_ah_ids = access_domain_ah_ids.filtered(lambda x: x.delete_right)
                        if access_domain_ah_ids:
                            has_access = bool(access_domain_ah_ids)
            
                    read_value = True
                    self._cr.execute(SQL("SELECT state FROM ir_module_module WHERE name='simplify_access_management'"))
                    data = self._cr.fetchone() or False
                    if data and data[0] != 'installed':
                        read_value = False
                    
                    cids = int(request.httprequest.cookies.get('cids') and request.httprequest.cookies.get('cids').split('-')[0] or request.env.company.id)
        
                    if self.env.user.id and read_value and cids:
                    
                        self._cr.execute(SQL("""SELECT access_management_id FROM access_management_comapnay_rel WHERE company_id = %s"""% cids))
                        a = self._cr.fetchall()
                        if a:
                            
                            self._cr.execute(SQL("""SELECT access_management_id FROM access_management_users_rel_ah WHERE user_id = %s AND access_management_id in %s""" % (self.env.user.id,tuple([i[0] for i in a] + [0]))))
                            a = self._cr.fetchall()
                            if a:
                                self._cr.execute(SQL("""SELECT id FROM access_management WHERE active='t' AND id in %s AND readonly = True""", (
                                    tuple([i[0] for i in a] + [0]))))
                                a = self._cr.fetchall()
                        if bool(a):
                            if mode != 'read':
                                return False

        except:
            pass

        if not has_access and raise_exception:
            raise self._make_access_error(model, mode) from None

        return has_access
