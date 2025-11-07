# -*- coding: utf-8 -*-
from odoo import models, fields

class UserPresenceLog(models.Model):
    _name = 'user.presence.log'
    _description = 'Historique de présence utilisateurs'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='Utilisateur', required=True, index=True)
    seen_at = fields.Datetime(string='Vu à', required=True, default=fields.Datetime.now, index=True)
