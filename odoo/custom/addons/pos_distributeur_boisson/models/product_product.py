# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Champ PLU pour identifier les boissons du distributeur
    plu_code = fields.Char(
        string="Code PLU",
        help="Code PLU (Price Look Up) utilisé par le distributeur automatique de boissons",
        index=True,
        copy=False
    )
    
    # Champ pour indiquer si c'est une boisson du distributeur
    is_distributeur_boisson = fields.Boolean(
        string="Boisson du distributeur",
        help="Cochez cette case si ce produit est disponible via le distributeur automatique",
        default=False
    )
    
    # Nouveau champ pour différencier les types de boissons
    needs_distributor = fields.Boolean(
        string="Nécessite le distributeur",
        help="Cochez cette case si cette boisson doit être servie via le distributeur automatique",
        default=False
    )
    
    # Note: Les champs distributeur (PLU, volume, crédits) sont maintenant dans pos.combo.option
    # et non plus dans product.product pour les ingrédients
    
    # Champ pour le volume servi par le distributeur (en cl)
    volume_distributeur = fields.Float(
        string="Volume distributeur (cl)",
        help="Volume servi par le distributeur automatique en centilitres",
        default=25.0
    )
    
    # Champ pour le nombre de crédits nécessaires par portion
    credits_per_serving = fields.Integer(
        string="Crédits par portion",
        help="Nombre de crédits nécessaires pour obtenir une portion de cette boisson",
        default=1
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

    # Champ pour les lignes de combo (directement éditable)
    combo_line_ids = fields.One2many(
        'product.combo.line',
        'product_tmpl_id',
        related='product_tmpl_id.combo_line_ids',
        string="Lignes de Combo",
        help="Configuration des lignes de combo pour ce produit",
        readonly=False
    )

    # Champ pour sélectionner les ingrédients spécifiques à ce cocktail
    selected_combo_ingredient_ids = fields.Many2many(
        comodel_name='pos.combo.option',
        related='product_tmpl_id.selected_combo_ingredient_ids',
        string='Ingrédients Sélectionnés',
        help="Sélectionnez les ingrédients spécifiques à utiliser pour ce cocktail",
        readonly=False
    )
    
    # Champ calculé pour afficher les ingrédients dans l'onglet Combo
    combo_ingredient_ids = fields.Many2many(
        comodel_name='pos.combo.option',
        related='product_tmpl_id.combo_ingredient_ids',
        string='Ingrédients Combo',
        readonly=True
    )
    
    # Champ calculé pour le volume total du cocktail
    combo_volume_total = fields.Float(
        related='product_tmpl_id.combo_volume_total',
        string='Volume total du cocktail (cl)',
        readonly=True,
        help="Volume total calculé à partir des ingrédients sélectionnés"
    )

    @api.onchange('is_combo_product')
    def _onchange_is_combo_product(self):
        """Synchronise le champ is_combo_product avec le template et hérite des propriétés distributeur"""
        if self.product_tmpl_id:
            self.product_tmpl_id.is_combo_product = self.is_combo_product
            
            # Si c'est un produit combo, hériter automatiquement des propriétés distributeur
            if self.is_combo_product:
                self.is_distributeur_boisson = True
                self.needs_distributor = True
                self.available_in_pos = True
                # Pour les cocktails, on garde credits_per_serving = 0 car les crédits viennent des ingrédients
                self.credits_per_serving = 0

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

    @api.onchange('selected_combo_ingredient_ids')
    def _onchange_selected_combo_ingredient_ids(self):
        """Force le recalcul du volume quand les ingrédients changent"""
        if self.is_combo_product and self.product_tmpl_id:
            self.product_tmpl_id._compute_combo_volume_total()





    @api.model_create_multi
    def create(self, vals_list):
        """Synchronise is_combo_product lors de la création et hérite des propriétés distributeur"""
        # Traiter chaque ensemble de valeurs
        for vals in vals_list:
            if 'is_combo_product' in vals and vals.get('product_tmpl_id'):
                template = self.env['product.template'].browse(vals['product_tmpl_id'])
                template.is_combo_product = vals['is_combo_product']
                
                # Si c'est un produit combo, hériter automatiquement des propriétés distributeur
                if vals.get('is_combo_product'):
                    vals['is_distributeur_boisson'] = True
                    vals['needs_distributor'] = True
                    vals['credits_per_serving'] = 0  # Les crédits viennent des ingrédients
            

            
            # Si c'est un produit du distributeur, l'associer automatiquement à la catégorie POS "Boissons"
            if vals.get('is_distributeur_boisson') or vals.get('needs_distributor'):
                # Rechercher la catégorie POS "Boissons"
                drinks_category = self.env['pos.category'].search([('name', 'ilike', 'Drinks')], limit=1)
                if drinks_category and vals.get('product_tmpl_id'):
                    template = self.env['product.template'].browse(vals['product_tmpl_id'])
                    if template and drinks_category not in template.pos_categ_ids:
                        template.pos_categ_ids = [(4, drinks_category.id)]
        
        return super().create(vals_list)

    def write(self, vals):
        """Synchronise is_combo_product lors de la modification et hérite des propriétés distributeur"""
        if 'is_combo_product' in vals:
            for record in self:
                if record.product_tmpl_id:
                    record.product_tmpl_id.is_combo_product = vals['is_combo_product']
                    
                    # Si c'est un produit combo, hériter automatiquement des propriétés distributeur
                    if vals.get('is_combo_product'):
                        vals['is_distributeur_boisson'] = True
                        vals['needs_distributor'] = True
                        vals['credits_per_serving'] = 0  # Les crédits viennent des ingrédients
        

        
        # Si c'est un produit du distributeur, l'associer automatiquement à la catégorie POS "Boissons"
        if vals.get('is_distributeur_boisson') or vals.get('needs_distributor'):
            drinks_category = self.env['pos.category'].search([('name', 'ilike', 'Drinks')], limit=1)
            if drinks_category:
                for record in self:
                    if record.product_tmpl_id and drinks_category not in record.product_tmpl_id.pos_categ_ids:
                        record.product_tmpl_id.pos_categ_ids = [(4, drinks_category.id)]
        
        return super().write(vals)

    @api.constrains('plu_code')
    def _check_plu_code_unique(self):
        """Vérifie que le code PLU est unique"""
        for record in self:
            if record.plu_code:
                duplicate = self.search([
                    ('plu_code', '=', record.plu_code),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(_(
                        "Le code PLU '%s' est déjà utilisé par le produit '%s'"
                    ) % (record.plu_code, duplicate[0].name))

    @api.constrains('volume_distributeur')
    def _check_volume_distributeur(self):
        """Vérifie que le volume distributeur est positif"""
        for record in self:
            if record.volume_distributeur <= 0:
                raise ValidationError(_(
                    "Le volume distributeur doit être supérieur à 0"
                ))

    @api.constrains('credits_per_serving')
    def _check_credits_per_serving(self):
        """Vérifie que le nombre de crédits est positif (sauf pour les cocktails)"""
        for record in self:
            if record.credits_per_serving < 0:
                raise ValidationError(_(
                    "Le nombre de crédits par portion ne peut pas être négatif"
                ))

    def get_distributeur_info(self):
        """Retourne les informations du distributeur pour ce produit"""
        if not self.is_distributeur_boisson:
            return None
            
        return {
            'plu_code': self.plu_code,
            'needs_distributor': self.needs_distributor,
            'volume_distributeur': self.volume_distributeur,
            'credits_per_serving': self.credits_per_serving,
        }

    def get_cocktail_ingredients(self):
        """
        Retourne la liste des ingrédients d'un cocktail avec leurs informations distributeur
        
        Returns:
            list: Liste des dictionnaires contenant les informations des ingrédients
                  [{'plu_code': 'PLU001', 'name': 'Menthe', 'credits': 1, 'product_id': 1}, ...]
        """
        if not self.is_combo_product:
            return []
            
        ingredients = []
        
        # Récupérer toutes les options de combo associées à ce produit
        for combo_line in self.combo_line_ids:
            category = combo_line.combo_category_id
            if category:
                # Récupérer les options de cette catégorie
                options = self.env['pos.combo.option'].search([
                    ('combo_category_id', '=', category.id),
                    ('active', '=', True)
                ])
                
                for option in options:
                    ingredient_product = option.product_id
                    if ingredient_product and ingredient_product.plu_code:
                        ingredient_info = {
                            'plu_code': ingredient_product.plu_code,
                            'name': ingredient_product.name,
                            'credits': ingredient_product.credits_per_serving or 1,
                            'product_id': ingredient_product.id,
                            'category_name': category.name,
                            'price_extra': option.price_extra
                        }
                        ingredients.append(ingredient_info)
                    else:
                        _logger.warning(f"Ingrédient {option.name} sans code PLU dans le cocktail {self.name}")
        
        return ingredients

    def get_combo_data(self):
        """Retourne les données de combo pour ce produit"""
        if not self.is_combo_product:
            return None
            
        combo_data = {
            'categories': [],
            'options': [],
            'combo_lines': []
        }
        
        # Charger les catégories de combo
        categories = self.env['pos.combo.category'].search([('active', '=', True)])
        for category in categories:
            combo_data['categories'].append({
                'id': category.id,
                'name': category.name,
                'description': category.description or '',
                'sequence': category.sequence
            })
        
        # Charger les options de combo
        options = self.env['pos.combo.option'].search([('active', '=', True)])
        for option in options:
            combo_data['options'].append({
                'id': option.id,
                'name': option.name,
                'combo_category_id': [option.combo_category_id.id, option.combo_category_id.name],
                'product_id': [option.product_id.id, option.product_id.name],
                'price_extra': option.price_extra,
                'sequence': option.sequence,
                'description': option.description or ''
            })
        
        # Charger les lignes de combo spécifiques à ce produit
        combo_lines = self.product_tmpl_id.combo_line_ids
        for line in combo_lines:
            combo_data['combo_lines'].append({
                'id': line.id,
                'product_tmpl_id': [line.product_tmpl_id.id, line.product_tmpl_id.name],
                'combo_category_id': [line.combo_category_id.id, line.combo_category_id.name],
                'sequence': line.sequence,
                'required': line.required,
                'min_selections': line.min_selections,
                'max_selections': line.max_selections
            })
        
        return combo_data

    @api.model
    def search_boissons_need_distributor(self):
        """
        Recherche les produits qui nécessitent le distributeur
        (boissons simples ET cocktails, mais pas les ingrédients uniquement)
        """
        return self.search([
            ('is_distributeur_boisson', '=', True),
            ('plu_code', '!=', False),
            ('available_in_pos', '=', True),
            ('is_ingredient_only', '=', False),  # Exclure les ingrédients uniquement
        ])

    def action_refresh_ingredients(self):
        """
        Force le recalcul des ingrédients disponibles
        """
        self.ensure_one()
        if self.product_tmpl_id:
            self.product_tmpl_id._compute_combo_ingredient_ids()
        return True

    def action_add_ingredients(self):
        """
        Ouvre une fenêtre pour sélectionner les ingrédients à ajouter
        """
        self.ensure_one()
        
        # Vérifie que le produit template existe
        if not self.product_tmpl_id or not self.product_tmpl_id.exists():
            raise ValidationError(_("Le produit template associé n'existe pas."))
        
        # Retourne une action pour ouvrir le wizard de sélection d'ingrédients
        return {
            'name': 'Sélectionner des Ingrédients',
            'type': 'ir.actions.act_window',
            'res_model': 'ingredient.selection.wizard',
            'view_mode': 'form',
            'context': {
                'default_product_template_id': self.product_tmpl_id.id,
                'active_id': self.product_tmpl_id.id,
            },
            'target': 'new',
            'views': [
                (False, 'form'),
            ],
        }

    @api.model
    def search_ingredients_for_combos(self):
        """
        Recherche les produits qui peuvent être utilisés comme ingrédients
        (produits normaux avec PLU, pas les cocktails, incluant les ingrédients uniquement)
        """
        return self.search([
            ('is_distributeur_boisson', '=', True),
            ('plu_code', '!=', False),
            ('is_combo_product', '=', False),
            ('available_in_pos', '=', True)
        ])

    def action_clear_ingredients(self):
        """
        Efface tous les ingrédients sélectionnés
        """
        self.ensure_one()
        
        if not self.product_tmpl_id:
            return False
        
        # Efface tous les ingrédients sélectionnés
        self.product_tmpl_id.selected_combo_ingredient_ids = [(6, 0, [])]
        
        # Force le recalcul des ingrédients affichés
        self.product_tmpl_id._compute_combo_ingredient_ids()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': 'Tous les ingrédients ont été effacés !',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def update_pos_availability(self):
        """
        Met à jour la disponibilité en POS pour tous les produits marqués comme boissons du distributeur
        (excluant les ingrédients uniquement)
        """
        products = self.search([
            ('is_distributeur_boisson', '=', True),
            ('available_in_pos', '=', False),
            ('is_ingredient_only', '=', False),  # Exclure les ingrédients uniquement
        ])
        
        for product in products:
            product.available_in_pos = True
        
        _logger.info(f"Mise à jour de la disponibilité POS pour {len(products)} produits")
        return len(products)

    def action_update_pos_availability(self):
        """
        Action pour mettre à jour la disponibilité POS des boissons du distributeur
        """
        self.ensure_one()
        
        updated_count = self.update_pos_availability()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f'{updated_count} produit(s) mis à jour avec succès !',
                'type': 'success',
                'sticky': False,
            }
        }