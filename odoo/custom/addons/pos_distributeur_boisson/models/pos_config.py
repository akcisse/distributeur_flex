# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_available_product_domain(self):
        """
        Étend le domaine des produits disponibles pour inclure les boissons du distributeur
        sans toucher au module POS d'Odoo
        """
        domain = super()._get_available_product_domain()
        
        # Ajouter les boissons du distributeur au domaine
        distributeur_domain = [
            ('is_distributeur_boisson', '=', True),
            ('available_in_pos', '=', True),
            ('is_ingredient_only', '=', False),  # Exclure les ingrédients
        ]
        
        # Combiner les domaines avec OR
        from odoo.osv.expression import OR
        return OR([domain, distributeur_domain])

    def _get_available_products(self):
        """
        Étend la méthode pour inclure les boissons du distributeur
        """
        products = super()._get_available_products()
        
        # Ajouter les boissons du distributeur
        distributeur_products = self.env['product.product'].search([
            ('is_distributeur_boisson', '=', True),
            ('available_in_pos', '=', True),
            ('is_ingredient_only', '=', False),
        ])
        
        return products | distributeur_products 