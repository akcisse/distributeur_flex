# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

def post_init_hook(cr, registry):
    """
    Hook post-installation pour corriger les permissions de la table de relation
    """
    try:
        # Corriger les permissions pour la table de relation Many2many
        # Utiliser l'utilisateur regiosis qui est configuré dans odoo17.conf
        cr.execute("""
            GRANT ALL PRIVILEGES ON TABLE pos_combo_option_product_template_rel TO regiosis;
            ALTER TABLE pos_combo_option_product_template_rel OWNER TO regiosis;
        """)
        _logger.info("Permissions corrigées pour pos_combo_option_product_template_rel")
    except Exception as e:
        _logger.error("Erreur lors de la correction des permissions: %s", str(e))
        # Ne pas faire échouer l'installation si la correction échoue
        pass

class PosComboCategory(models.Model):
    _name = 'pos.combo.category'
    _description = 'Catégorie de composant pour produit combo'
    _order = 'sequence, name'

    name = fields.Char('Nom', required=True)
    sequence = fields.Integer('Séquence', default=10)
    active = fields.Boolean('Actif', default=True)
    option_ids = fields.One2many('pos.combo.option', 'combo_category_id', 'Options')
    description = fields.Text('Description')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de la catégorie doit être unique !')
    ]

class PosComboOption(models.Model):
    _name = 'pos.combo.option'
    _description = 'Option de combo pour produit'
    _order = 'sequence'

    name = fields.Char('Nom', required=True)
    combo_category_id = fields.Many2one('pos.combo.category', 'Catégorie', required=True)
    product_id = fields.Many2one('product.product', 'Produit', required=True)
    price_extra = fields.Float('Prix supplémentaire', default=0.0)
    sequence = fields.Integer('Séquence', default=10)
    active = fields.Boolean('Actif', default=True)
    description = fields.Text('Description')
    
    # Champs pour le distributeur (ingrédients)
    plu_code = fields.Char(
        string="Code PLU",
        help="Code PLU (Price Look Up) utilisé par le distributeur automatique de boissons",
        index=True,
        copy=False
    )
    
    volume_distributeur = fields.Float(
        string="Volume distributeur (cl)",
        help="Volume servi par le distributeur automatique en centilitres",
        default=5.0
    )
    
    credits_per_serving = fields.Integer(
        string="Crédits par portion",
        help="Nombre de crédits nécessaires pour obtenir une portion de cet ingrédient",
        default=1
    )
    
    _sql_constraints = [
        ('plu_code_uniq', 'unique(plu_code)', 
         'Ce code PLU est déjà utilisé par une autre option.')
    ]

    @api.constrains('plu_code')
    def _check_plu_code_unique(self):
        """Vérifie que le code PLU est unique"""
        for record in self:
            if record.plu_code:
                existing = self.search([
                    ('plu_code', '=', record.plu_code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_(
                        "Le code PLU '%s' est déjà utilisé par l'option '%s'"
                    ) % (record.plu_code, existing[0].name))

    def action_select_ingredient(self):
        """
        Méthode appelée quand un ingrédient est sélectionné dans la fenêtre popup
        """
        self.ensure_one()
        
        # Récupère le contexte pour savoir quel produit template ajouter l'ingrédient
        product_template_id = self.env.context.get('product_template_id')
        
        if product_template_id:
            product_template = self.env['product.template'].browse(product_template_id)
            
            # Ajoute cet ingrédient au produit template
            current_ingredients = product_template.selected_combo_ingredient_ids
            if self not in current_ingredients:
                product_template.selected_combo_ingredient_ids = [(4, self.id)]
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Succès',
                    'message': f'Ingrédient "{self.name}" ajouté avec succès !',
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        return True

class ProductComboLine(models.Model):
    _name = 'product.combo.line'
    _description = 'Ligne de combo pour produit template'
    _order = 'sequence'

    product_tmpl_id = fields.Many2one('product.template', 'Produit Template', required=True, ondelete='cascade')
    combo_category_id = fields.Many2one('pos.combo.category', 'Catégorie', required=True)
    sequence = fields.Integer('Séquence', default=10)
    required = fields.Boolean('Obligatoire', default=True)
    max_selections = fields.Integer('Sélections max', default=1)
    min_selections = fields.Integer('Sélections min', default=1)
    
    @api.constrains('min_selections', 'max_selections')
    def _check_selections(self):
        for record in self:
            if record.min_selections > record.max_selections:
                raise ValidationError(_('Le nombre minimum de sélections ne peut pas être supérieur au nombre maximum.'))
            if record.min_selections < 0:
                raise ValidationError(_('Le nombre minimum de sélections ne peut pas être négatif.'))

    def get_available_ingredients(self):
        """
        Retourne les ingrédients disponibles pour cette catégorie
        """
        if not self.combo_category_id:
            return self.env['pos.combo.option']
        
        return self.env['pos.combo.option'].search([
            ('combo_category_id', '=', self.combo_category_id.id),
            ('active', '=', True)
        ])

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_combo_product = fields.Boolean('Produit Combo', default=False)
    combo_line_ids = fields.One2many('product.combo.line', 'product_tmpl_id', string='Lignes de Combo')
    
    # Champ pour sélectionner les ingrédients spécifiques à ce cocktail
    selected_combo_ingredient_ids = fields.Many2many(
        comodel_name='pos.combo.option',
        string='Ingrédients Sélectionnés',
        help="Sélectionnez les ingrédients spécifiques à utiliser pour ce cocktail",
        domain="[('active', '=', True)]"
    )
    
    # Champ calculé pour afficher les ingrédients dans l'onglet Combo
    combo_ingredient_ids = fields.Many2many(
        comodel_name='pos.combo.option',
        string='Ingrédients Combo',
        compute='_compute_combo_ingredient_ids',
        store=False
    )
    
    # Champ calculé pour le volume total du cocktail basé sur les ingrédients sélectionnés
    combo_volume_total = fields.Float(
        string='Volume total du cocktail (cl)',
        compute='_compute_combo_volume_total',
        store=False,
        help="Volume total calculé à partir des ingrédients sélectionnés"
    )

    @api.onchange('is_combo_product')
    def _onchange_is_combo_product(self):
        if not self.is_combo_product:
            self.combo_line_ids = [(5, 0, 0)]

    @api.onchange('selected_combo_ingredient_ids')
    def _onchange_selected_combo_ingredient_ids(self):
        """Force le recalcul du volume quand les ingrédients changent"""
        if self.is_combo_product:
            self._compute_combo_volume_total()

    @api.depends('combo_line_ids', 'combo_line_ids.combo_category_id', 'selected_combo_ingredient_ids')
    def _compute_combo_ingredient_ids(self):
        """
        Calcule les ingrédients disponibles pour ce produit combo
        en fonction des ingrédients sélectionnés
        """
        for product in self:
            if product.is_combo_product:
                # Utilise les ingrédients sélectionnés spécifiquement pour ce cocktail
                if product.selected_combo_ingredient_ids:
                    product.combo_ingredient_ids = [(6, 0, product.selected_combo_ingredient_ids.ids)]
                else:
                    product.combo_ingredient_ids = [(6, 0, [])]
            else:
                product.combo_ingredient_ids = [(6, 0, [])]

    @api.depends('selected_combo_ingredient_ids', 'selected_combo_ingredient_ids.volume_distributeur')
    def _compute_combo_volume_total(self):
        """
        Calcule le volume total du cocktail basé sur les ingrédients sélectionnés
        """
        for product in self:
            if product.is_combo_product and product.selected_combo_ingredient_ids:
                total_volume = 0.0
                for ingredient in product.selected_combo_ingredient_ids:
                    if ingredient.volume_distributeur:
                        total_volume += ingredient.volume_distributeur
                product.combo_volume_total = total_volume
            else:
                product.combo_volume_total = 0.0

    def action_refresh_ingredients(self):
        """
        Force le recalcul des ingrédients disponibles
        """
        self.ensure_one()
        self._compute_combo_ingredient_ids()
        return True

    def action_select_ingredients(self, ingredient_ids):
        """
        Ajoute les ingrédients sélectionnés au produit combo
        """
        self.ensure_one()
        
        if ingredient_ids:
            # Convertit les IDs en liste si ce n'est pas déjà le cas
            if isinstance(ingredient_ids, int):
                ingredient_ids = [ingredient_ids]
            
            # Récupère les ingrédients sélectionnés
            selected_ingredients = self.env['pos.combo.option'].browse(ingredient_ids)
            
            # Ajoute les ingrédients sélectionnés à la liste existante
            current_ingredients = self.selected_combo_ingredient_ids
            new_ingredients = current_ingredients + selected_ingredients
            
            # Met à jour la liste des ingrédients sélectionnés
            self.selected_combo_ingredient_ids = [(6, 0, new_ingredients.ids)]
            
            # Force le recalcul des ingrédients affichés
            self._compute_combo_ingredient_ids()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Succès',
                    'message': f'{len(selected_ingredients)} ingrédient(s) ajouté(s) avec succès !',
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        return True

    def action_clear_ingredients(self):
        """
        Efface tous les ingrédients sélectionnés
        """
        self.ensure_one()
        
        # Efface tous les ingrédients sélectionnés
        self.selected_combo_ingredient_ids = [(6, 0, [])]
        
        # Force le recalcul des ingrédients affichés
        self._compute_combo_ingredient_ids()
        
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

    def action_add_ingredients(self):
        """
        Ouvre une fenêtre pour sélectionner les ingrédients à ajouter
        """
        self.ensure_one()
        
        # Vérifie que le produit template existe
        if not self.exists():
            raise ValidationError(_("Le produit template n'existe pas."))
        
        # Retourne une action pour ouvrir le wizard de sélection d'ingrédients
        return {
            'name': 'Sélectionner des Ingrédients',
            'type': 'ir.actions.act_window',
            'res_model': 'ingredient.selection.wizard',
            'view_mode': 'form',
            'context': {
                'default_product_template_id': self.id,
                'active_id': self.id,
            },
            'target': 'new',
            'views': [
                (False, 'form'),
            ],
        }

    def get_combo_ingredients_by_category(self):
        """
        Retourne les ingrédients organisés par catégorie pour ce produit combo
        """
        if not self.is_combo_product:
            return {}
        
        ingredients_by_category = {}
        
        for ingredient in self.combo_ingredient_ids:
            category_name = ingredient.combo_category_id.name
            if category_name not in ingredients_by_category:
                ingredients_by_category[category_name] = []
            
            ingredients_by_category[category_name].append({
                'id': ingredient.id,
                'name': ingredient.name,
                'price_extra': ingredient.price_extra,
                'product_id': ingredient.product_id.name,
            })
        
        return ingredients_by_category 