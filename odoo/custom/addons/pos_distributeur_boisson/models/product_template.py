# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Champ pour indiquer si c'est une boisson du distributeur
    is_distributeur_boisson = fields.Boolean(
        string="Boisson du distributeur",
        help="Cochez cette case si ce produit est disponible via le distributeur automatique",
        default=False
    )
    
    # Nouveau champ pour différencier les types de boissons
    needs_distributor = fields.Boolean(
        string="Nécessite le distributeur",
        help="Cochez cette case si cette boisson doit être servie via le distributeur (verres). "
             "Décochez pour les boissons directes (canettes, bouteilles)",
        default=True
    )
    
    # Champ pour le volume/contenance
    volume_distributeur = fields.Char(
        string="Volume Distributeur",
        help="Volume de la boisson (ex: 25cl, 50cl, 15cl)",
        default="25cl"
    )
    
    # Champ pour le nombre de crédits par service
    credits_per_serving = fields.Integer(
        string="Crédits par service",
        help="Nombre de crédits à envoyer au distributeur pour servir cette boisson",
        default=1,
        required=True
    )

    # Champ PLU pour identifier les boissons du distributeur (hérité par les variantes)
    plu_code = fields.Char(
        string="Code PLU",
        help="Code PLU (Price Look Up) utilisé par le distributeur automatique de boissons",
        index=True,
        copy=False
    )

    # Champs pour les produits combo
    is_combo_product = fields.Boolean(
        string="Produit Combo",
        help="Indique si ce produit est un produit combo avec sélection de composants",
        default=False
    )

    # Champ pour identifier les ingrédients uniquement (pas de vente directe)
    is_ingredient_only = fields.Boolean(
        string="Ingrédient uniquement",
        help="Cochez cette case si ce produit est un ingrédient qui ne doit pas être vendu directement en POS",
        default=False
    )
    


    # Lignes de combo pour ce produit template
    combo_line_ids = fields.One2many(
        'product.combo.line',
        'product_tmpl_id',
        string="Lignes de Combo",
        help="Configuration des lignes de combo pour ce produit"
    )

    @api.onchange('is_distributeur_boisson')
    def _onchange_is_distributeur_boisson(self):
        """Active automatiquement la disponibilité en POS quand c'est une boisson du distributeur (sauf ingrédients)"""
        if self.is_distributeur_boisson and not self.is_ingredient_only:
            self.available_in_pos = True
        elif self.is_ingredient_only:
            self.available_in_pos = False

    @api.onchange('is_ingredient_only')
    def _onchange_is_ingredient_only(self):
        """Désactive automatiquement la disponibilité en POS pour les ingrédients uniquement"""
        if self.is_ingredient_only:
            self.available_in_pos = False

    @api.onchange('is_combo_product')
    def _onchange_is_combo_product(self):
        """Active automatiquement la disponibilité en POS et les propriétés distributeur pour les combos"""
        if self.is_combo_product:
            self.is_distributeur_boisson = True
            self.needs_distributor = True
            self.available_in_pos = True

    @api.constrains('credits_per_serving')
    def _check_credits_per_serving(self):
        """
        Vérifie que le nombre de crédits par service est positif
        """
        for record in self:
            if record.is_distributeur_boisson and record.credits_per_serving <= 0:
                raise ValidationError(
                    _("Le nombre de crédits par service doit être supérieur à 0 pour le produit '%s'.") % 
                    record.name
                )

