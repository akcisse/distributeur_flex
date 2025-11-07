/** @odoo-module **/
/**
 * Patch du ProductScreen pour intercepter la valeur "remove" et décrémenter
 * au lieu de supprimer toute la ligne
 */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    /**
     * Surcharge de _setValue pour gérer la suppression avec décrémentation
     */
    _setValue(val) {
        const { numpadMode } = this.pos;
        let selectedLine = this.currentOrder.get_selected_orderline();
        
        if (selectedLine && numpadMode === "quantity" && val === "remove") {
            console.log(`🗑️ [POS DISTRIBUTEUR] Action "remove" interceptée`);
            
            // Gérer combo parent
            if (selectedLine.comboParent) {
                selectedLine = selectedLine.comboParent;
            }
            
            const currentQty = selectedLine.get_quantity();
            const product = selectedLine.get_product();
            
            console.log(`📊 [POS DISTRIBUTEUR] Quantité actuelle: ${currentQty}`);
            
            // Si quantité > 1, décrémenter de 1
            if (currentQty > 1) {
                console.log(`➖ [POS DISTRIBUTEUR] Décrémentation de 1 (nouvelle quantité: ${currentQty - 1})`);
                
                // Décrémenter la quantité
                const result = selectedLine.set_quantity(currentQty - 1, Boolean(selectedLine.comboLines?.length));
                
                // Si la ligne a des comboLines, décrémenter aussi
                if (selectedLine.comboLines) {
                    for (const line of selectedLine.comboLines) {
                        line.set_quantity(currentQty - 1, true);
                    }
                }
                
                if (!result) {
                    this.numberBuffer.reset();
                }
                
                // Annuler 1 crédit si c'est une boisson du distributeur
                if (selectedLine.shouldCancelCredit && selectedLine.shouldCancelCredit(product)) {
                    selectedLine.cancelOneCredit(product, 1).catch(err => {
                        console.error('Erreur annulation crédit:', err);
                    });
                }
                
                // NE PAS appeler super - on a géré la décrémentation
                console.log(`✅ [POS DISTRIBUTEUR] Décrémentation terminée`);
                return;
            }
            
            // Si quantité = 1, supprimer normalement mais annuler le crédit
            console.log(`🗑️ [POS DISTRIBUTEUR] Quantité = 1, suppression de la ligne`);
            
            // Annuler le crédit avant suppression
            if (selectedLine.shouldCancelCredit && selectedLine.shouldCancelCredit(product)) {
                selectedLine.cancelOneCredit(product, 1).catch(err => {
                    console.error('Erreur annulation crédit:', err);
                });
            }
            
            // Appeler la méthode originale pour supprimer la ligne (elle passera par removeOrderline)
            return super._setValue(...arguments);
        }
        
        // Pour tous les autres cas, appeler la méthode originale
        return super._setValue(...arguments);
    },
});

console.log("✅ [POS DISTRIBUTEUR] Patch ProductScreen chargé - Action remove interceptée");

