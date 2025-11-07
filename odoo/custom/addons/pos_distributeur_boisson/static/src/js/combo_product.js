/** @odoo-module **/
import { Product } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Product.prototype, {
    // Dans un patch, on n'override pas le constructor avec super()
    // On ajoute seulement de nouvelles méthodes ou on override des méthodes existantes
    
    // Méthode pour récupérer les données combo
    getComboData() {
        if (!this.is_combo_product) {
            return null;
        }
        
        return {
            combo_lines: this.combo_line_ids || [],
            is_combo: true
        };
    },
    
    // Override d'une méthode existante si nécessaire
    get_price() {
        // Appeler la méthode originale avec super
        const originalPrice = super.get_price();
        
        // Ajouter votre logique de prix combo ici si nécessaire
        return originalPrice;
    }
});

console.log("POS Combo Product patch loaded successfully");
