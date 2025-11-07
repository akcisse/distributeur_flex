/** @odoo-module **/
/**
 * Extension du comportement du bouton de suppression pour décrémenter au lieu de tout supprimer
 * et annuler les crédits du distributeur automatiquement
 */

import { Orderline } from "@point_of_sale/app/store/models";
import { Order } from "@point_of_sale/app/store/models";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

// ========================================
// PATCH DU MODÈLE ORDERLINE
// ========================================
patch(Orderline.prototype, {
    /**
     * Méthode pour obtenir la quantité (compatible avec différentes versions)
     */
    _getQuantity() {
        return this.get_quantity ? this.get_quantity() : this.qty;
    },
    
    /**
     * Méthode pour définir la quantité (compatible avec différentes versions)
     */
    _setQuantity(qty) {
        if (this.set_quantity) {
            this.set_quantity(qty);
        } else {
            this.qty = qty;
        }
    },
    
    /**
     * Méthode pour obtenir le produit (compatible avec différentes versions)
     */
    _getProduct() {
        return this.get_product ? this.get_product() : this.product;
    },
    
    /**
     * Vérifie si le produit nécessite l'annulation de crédits
     */
    shouldCancelCredit(product) {
        return product && (
            product.is_distributeur_boisson || 
            product.needs_distributor || 
            product.distributeur_boisson
        );
    },
    
    /**
     * Annule un certain nombre de crédits pour ce produit
     */
    async cancelOneCredit(product, quantity) {
        try {
            console.log(`🔄 Tentative d'annulation de ${quantity} crédit(s) pour ${product.display_name || product.name}`);
            
            // Vérifier que c'est bien une boisson du distributeur
            const isDistributeurDrink = product.is_distributeur_boisson || product.needs_distributor;
            if (!isDistributeurDrink) {
                console.log(`⏭️ Pas une boisson du distributeur, annulation ignorée`);
                return;
            }
            
            // Utiliser le service RPC du POS (pas this.env car on est dans un modèle)
            const pos = this.pos;
            if (!pos || !pos.env || !pos.env.services || !pos.env.services.rpc) {
                console.warn("⚠️ Service RPC non disponible via POS");
                return;
            }
            
            const rpcService = pos.env.services.rpc;
            const order = pos.get_order();
            if (!order) {
                console.warn("⚠️ Pas de commande active");
                return;
            }
            
            const session = order.pos_session_id;
            if (!session) {
                console.warn("⚠️ Pas de session POS active - annulation impossible");
                return;
            }
            
            // Vérifier si c'est un cocktail
            const isCocktail = product.is_combo_product;
            
            if (isCocktail) {
                // Pour les cocktails, annuler les ingrédients
                console.log(`🍹 Produit cocktail détecté, annulation des ingrédients...`);
                const result = await rpcService({
                    model: 'pos.session',
                    method: 'cancel_cocktail_credits',
                    args: [session, product.id, quantity],
                    kwargs: {}
                });
                
                if (result && result.success) {
                    console.log(`✅ Crédits cocktail annulés: ${result.message}`);
                } else {
                    console.log(`⚠️ Annulation cocktail non réussie: ${result ? result.message : 'Erreur inconnue'}`);
                }
            } else {
                // Pour les boissons simples
                const plu_no = product.plu_code || 'PLU1';
                console.log(`🥤 Boisson simple, annulation PLU: ${plu_no}`);
                
                const result = await rpcService({
                    model: 'pos.session',
                    method: 'cancel_simple_drink_credits',
                    args: [session, plu_no, quantity, product.display_name || product.name],
                    kwargs: {}
                });
                
                if (result && result.success) {
                    console.log(`✅ Crédits annulés: ${result.message}`);
                } else {
                    console.log(`⚠️ Annulation crédit non réussie: ${result ? result.message : 'Erreur inconnue'}`);
                }
            }
            
        } catch (error) {
            // L'annulation des crédits a échoué mais ce n'est pas grave
            // La décrémentation a déjà fonctionné
            console.log(`⚠️ Annulation crédit échouée (non bloquant): ${error.message}`);
        }
    },
    
    /**
     * Affiche une notification
     */
    showNotification(message, type = "info") {
        if (this.env && this.env.services && this.env.services.notification) {
            this.env.services.notification.add(message, {
                type: type,
                sticky: false,
            });
        }
    },
});

// ========================================
// PATCH DU PRODUCTSCREEN - INTERCEPTER updateSelectedOrderline
// ========================================
patch(ProductScreen.prototype, {
    /**
     * Surcharge de updateSelectedOrderline pour intercepter AVANT la transformation
     * C'EST LA MÉTHODE APPELÉE PAR LE NUMBER BUFFER
     */
    async updateSelectedOrderline({ buffer, key }) {
        console.log(`🎯 [DISTRIBUTEUR] updateSelectedOrderline appelée - buffer="${buffer}", key="${key}"`);
        
        const order = this.pos.get_order();
        const selectedLine = order.get_selected_orderline();
        
        // Si on appuie sur Backspace ET buffer est null (ou vide)
        if (selectedLine && key === "Backspace" && (buffer === null || buffer === "")) {
            console.log(`⌫ [DISTRIBUTEUR] Backspace avec buffer vide détecté !`);
            
            // Vérifier le mode numpad
            if (this.pos.numpadMode === "quantity") {
                // Gérer combo parent
                let targetLine = selectedLine;
                if (selectedLine.comboParent) {
                    targetLine = selectedLine.comboParent;
                }
                
                const currentQty = targetLine.get_quantity();
                const product = targetLine.get_product();
                
                console.log(`📊 [DISTRIBUTEUR] Quantité actuelle: ${currentQty}`);
                
                // Si quantité > 1, décrémenter de 1
                if (currentQty > 1) {
                    console.log(`➖ [DISTRIBUTEUR] Décrémentation vers ${currentQty - 1}`);
                    
                    // Décrémenter la quantité
                    const result = targetLine.set_quantity(currentQty - 1, Boolean(targetLine.comboLines?.length));
                    
                    // Si la ligne a des comboLines, décrémenter aussi
                    if (targetLine.comboLines) {
                        for (const line of targetLine.comboLines) {
                            line.set_quantity(currentQty - 1, true);
                        }
                    }
                    
                    if (!result) {
                        this.numberBuffer.reset();
                    }
                    
                    // Annuler 1 crédit si c'est une boisson du distributeur
                    if (targetLine.shouldCancelCredit && targetLine.shouldCancelCredit(product)) {
                        targetLine.cancelOneCredit(product, 1).catch(err => {
                            console.error('❌ Erreur annulation crédit:', err);
                        });
                    }
                    
                    console.log(`✅ [DISTRIBUTEUR] Décrémentation terminée`);
                    // NE PAS appeler super - on a géré la décrémentation
                    return;
                }
                
                // Si quantité = 1, laisser la méthode originale supprimer
                console.log(`🗑️ [DISTRIBUTEUR] Quantité = 1, laisser supprimer`);
                
                // Annuler le crédit avant que la suppression se fasse
                if (targetLine.shouldCancelCredit && targetLine.shouldCancelCredit(product)) {
                    targetLine.cancelOneCredit(product, 1).catch(err => {
                        console.error('❌ Erreur annulation crédit:', err);
                    });
                }
            }
        }
        
        // Pour tous les autres cas, appeler la méthode originale
        return super.updateSelectedOrderline(...arguments);
    },
});

// ========================================
// PATCH DU MODÈLE ORDER (au cas où)
// ========================================
patch(Order.prototype, {
    /**
     * Surcharge de removeOrderline comme backup
     */
    removeOrderline(line) {
        console.log(`🗑️ [DISTRIBUTEUR] removeOrderline() appelée`);
        
        const currentQty = line.get_quantity ? line.get_quantity() : line.qty;
        const product = line.get_product ? line.get_product() : line.product;
        
        console.log(`📊 [DISTRIBUTEUR] Quantité dans removeOrderline: ${currentQty}`);
        
        // Si quantité > 1, décrémenter de 1 au lieu de supprimer (backup)
        if (currentQty > 1) {
            console.log(`➖ [DISTRIBUTEUR] Backup décrémentation vers ${currentQty - 1}`);
            
            // Décrémenter la quantité
            line.set_quantity(currentQty - 1);
            
            // Annuler 1 crédit si c'est une boisson du distributeur
            if (line.shouldCancelCredit && line.shouldCancelCredit(product)) {
                line.cancelOneCredit(product, 1).catch(err => {
                    console.error('❌ Erreur annulation crédit:', err);
                });
            }
            
            // Ne pas supprimer la ligne
            return false;
        }
        
        // Si quantité = 1 ou moins, supprimer normalement
        console.log(`🗑️ [DISTRIBUTEUR] Suppression ligne (qty=${currentQty})`);
        
        // Annuler le crédit restant avant suppression
        if (line.shouldCancelCredit && line.shouldCancelCredit(product)) {
            line.cancelOneCredit(product, 1).catch(err => {
                console.error('❌ Erreur annulation crédit:', err);
            });
        }
        
        // Appeler la méthode originale pour supprimer la ligne
        return super.removeOrderline(...arguments);
    },
});

console.log("✅ [DISTRIBUTEUR] Module chargé - Patches appliqués (ProductScreen + Order)");
