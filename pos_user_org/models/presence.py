# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta

class UserPresence(models.Model):
    _name = 'user.presence'
    _description = 'Présence utilisateurs (heartbeat)'
    _order = 'last_seen desc'

    user_id = fields.Many2one('res.users', string='Utilisateur', required=True, index=True)
    last_seen = fields.Datetime(string='Dernière activité', required=True, default=fields.Datetime.now)
    is_online = fields.Boolean(string='En ligne', compute='_compute_is_online', store=False)

    @api.depends('last_seen')
    def _compute_is_online(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_online = bool(rec.last_seen and (now - rec.last_seen) <= timedelta(minutes=2))

    @api.model
    def heartbeat(self):
        now = fields.Datetime.now()
        rec = self.search([('user_id', '=', self.env.user.id)], limit=1)
        if rec:
            rec.write({'last_seen': now})
        else:
            rec = self.create({'user_id': self.env.user.id, 'last_seen': now})
        # log historique
        self.env['user.presence.log'].sudo().create({'user_id': self.env.user.id, 'seen_at': now})
        return {'success': True, 'last_seen': rec.last_seen}
