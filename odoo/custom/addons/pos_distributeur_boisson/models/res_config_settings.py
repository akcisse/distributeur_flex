# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Champ pour activer/désactiver le module
    module_pos_distributeur_boisson = fields.Boolean(
        string="Activer le distributeur de boissons",
        help="Active le module de distributeur automatique de boissons"
    )

    pos_distributeur_middleware_url = fields.Char(
        string="URL du Middleware",
        config_parameter='pos_distributeur.middleware_url',
        default='http://192.168.1.58:5000',
        help="URL du middleware pour la communication avec l'appareil distributeur (ex: http://192.168.1.58:5000)"
    )
    
    pos_distributeur_middleware_token = fields.Char(
        string="Token d'authentification",
        config_parameter='pos_distributeur.middleware_token',
        default='',
        help="Token de sécurité pour authentifier les requêtes vers le middleware (optionnel)"
    )
    
    pos_distributeur_server_no = fields.Integer(
        string="Numéro du Serveur",
        config_parameter='pos_distributeur.server_no',
        default=1,
        help="Numéro d'identification du serveur/distributeur de boissons (ex: 1, 2, 3...)"
    )

    def set_values(self):
        """Sauvegarde les valeurs de configuration"""
        super().set_values()
        # Ici vous pouvez ajouter une logique de validation si nécessaire
        if self.pos_distributeur_middleware_url and not self.pos_distributeur_middleware_url.startswith(('http://', 'https://')):
            self.pos_distributeur_middleware_url = f"http://{self.pos_distributeur_middleware_url}"

    def get_values(self):
        """Récupère les valeurs de configuration"""
        res = super().get_values()
        # Récupérer les valeurs depuis les paramètres système
        config_param = self.env['ir.config_parameter'].sudo()
        res.update({
            'pos_distributeur_middleware_url': config_param.get_param('pos_distributeur.middleware_url', 'http://192.168.1.58:5000'),
            'pos_distributeur_middleware_token': config_param.get_param('pos_distributeur.middleware_token', ''),
            'pos_distributeur_server_no': int(config_param.get_param('pos_distributeur.server_no', '1')),
        })
        return res