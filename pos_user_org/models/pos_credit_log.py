# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosCreditLog(models.Model):
    _name = 'pos.credit.log'
    _description = 'Journal des crédits POS envoyés au middleware'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='Utilisateur', required=True, index=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', string='Employé', index=True, compute='_compute_employee', store=True)
    session_id = fields.Many2one('pos.session', string='Session POS', index=True)
    order_ref = fields.Char(string='Référence commande')
    product_name = fields.Char(string='Produit')
    plu_no = fields.Char(string='PLU')
    quantity = fields.Integer(string='Quantité', default=1)
    server_no = fields.Integer(string='Server No')
    success = fields.Boolean(string='Succès', default=False)
    message = fields.Char(string='Message')
    response_payload = fields.Text(string='Réponse middleware')
    
    # ✨ NOUVEAUX CHAMPS pour gestion annulation
    order_line_id = fields.Many2one(
        'pos.order.line', 
        string='Ligne de commande',
        help='Lien vers la ligne de commande POS',
        index=True,
        ondelete='set null'
    )
    
    status = fields.Selection([
        ('sent', 'Envoyé'),
        ('served', 'Servi'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
    ], string='Statut', default='sent', required=True, index=True)
    
    cancelled_at = fields.Datetime(
        string='Annulé le',
        help='Date et heure d\'annulation du crédit'
    )
    
    cancelled_by = fields.Many2one(
        'res.users',
        string='Annulé par',
        help='Utilisateur qui a annulé ce crédit'
    )
    
    cancellation_response = fields.Text(
        string='Réponse annulation',
        help='Réponse du middleware lors de l\'annulation'
    )
    
    credit_id = fields.Char(
        string='ID Crédit',
        help='Identifiant unique du crédit pour traçabilité',
        index=True
    )
    
    is_cancellation = fields.Boolean(
        string='Est une annulation',
        help='Indique si cette ligne représente une annulation de crédit',
        default=False
    )
    
    # Champ calculé pour affichage coloré dans les vues
    status_display = fields.Char(
        string='Statut Visuel',
        compute='_compute_status_display',
        store=False
    )

    @api.depends('status', 'is_cancellation')
    def _compute_status_display(self):
        """Calcule l'affichage visuel du statut"""
        for rec in self:
            if rec.is_cancellation:
                rec.status_display = '🔄 Annulation'
            elif rec.status == 'sent':
                rec.status_display = '📤 Envoyé'
            elif rec.status == 'served':
                rec.status_display = '✅ Servi'
            elif rec.status == 'cancelled':
                rec.status_display = '❌ Annulé'
            elif rec.status == 'refunded':
                rec.status_display = '💰 Remboursé'
            else:
                rec.status_display = '❓ Inconnu'

    @api.depends('user_id')
    def _compute_employee(self):
        for rec in self:
            rec.employee_id = rec.user_id.employee_id if hasattr(rec.user_id, 'employee_id') else False
