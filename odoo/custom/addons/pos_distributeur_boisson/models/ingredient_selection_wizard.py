# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class IngredientSelectionWizard(models.TransientModel):
    _name = 'ingredient.selection.wizard'
    _description = 'Wizard pour sélectionner des ingrédients'

    product_template_id = fields.Many2one('product.template', 'Produit Template', required=True)
    selected_ingredients = fields.Many2many(
        'pos.combo.option',
        string='Ingrédients Sélectionnés',
        domain="[('active', '=', True)]"
    )

    @api.model
    def default_get(self, fields_list):
        """Récupère les valeurs par défaut"""
        res = super().default_get(fields_list)
        
        # Vérifie d'abord le contexte pour product_template_id
        if self.env.context.get('default_product_template_id'):
            product_template_id = self.env.context.get('default_product_template_id')
            try:
                product_template = self.env['product.template'].browse(product_template_id)
                if product_template.exists():
                    res['product_template_id'] = product_template.id
                    res['selected_ingredients'] = [(6, 0, product_template.selected_combo_ingredient_ids.ids)]
            except Exception:
                pass
        
        # Sinon, essaie avec active_id
        elif self.env.context.get('active_id'):
            try:
                product_template = self.env['product.template'].browse(self.env.context.get('active_id'))
                if product_template.exists():
                    res['product_template_id'] = product_template.id
                    res['selected_ingredients'] = [(6, 0, product_template.selected_combo_ingredient_ids.ids)]
            except Exception:
                pass
        
        return res

    def action_add_selected_ingredients(self):
        """Ajoute les ingrédients sélectionnés au produit template"""
        self.ensure_one()
        
        if self.product_template_id and self.selected_ingredients:
            # Met à jour les ingrédients sélectionnés
            self.product_template_id.selected_combo_ingredient_ids = [(6, 0, self.selected_ingredients.ids)]
            
            # Force le recalcul du volume
            self.product_template_id._compute_combo_volume_total()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Succès',
                    'message': f'{len(self.selected_ingredients)} ingrédient(s) ajouté(s) avec succès !',
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        return True 