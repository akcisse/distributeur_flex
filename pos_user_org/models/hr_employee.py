# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    server_no = fields.Integer(string='Server No (Distributeur)')
    is_barman = fields.Boolean(string='Barman', help='Si coché, ajoute le groupe Barmans à l’utilisateur associé')

    def _sync_barman_group(self):
        group = self.env.ref('pos_user_org.group_pos_barman', raise_if_not_found=False)
        if not group:
            return
        for emp in self:
            user = emp.user_id
            if not user:
                continue
            if emp.is_barman:
                user.write({'groups_id': [(4, group.id)]})
            else:
                user.write({'groups_id': [(3, group.id)]})

    @api.model
    def create(self, vals):
        # Si un server_no est fourni (>0), marquer automatiquement comme Barman
        if vals.get('server_no'):
            try:
                if int(vals.get('server_no')) > 0:
                    vals.setdefault('is_barman', True)
            except Exception:
                pass
        emp = super().create(vals)
        if emp.is_barman or emp.user_id:
            emp._sync_barman_group()
        return emp

    def write(self, vals):
        # Si on renseigne/ajuste server_no, basculer automatiquement is_barman à True si >0
        new_vals = dict(vals)
        if 'server_no' in new_vals and not new_vals.get('is_barman'):
            try:
                if int(new_vals.get('server_no') or 0) > 0:
                    new_vals['is_barman'] = True
            except Exception:
                pass
        res = super().write(new_vals)
        if any(k in new_vals for k in ('is_barman', 'user_id', 'server_no')):
            self._sync_barman_group()
        return res
