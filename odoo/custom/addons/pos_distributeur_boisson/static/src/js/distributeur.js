/** @odoo-module **/
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

export class DistributeurButton extends Component {
    static template = "pos_distributeur_boisson.DistributeurButton";
    
    setup() {
        super.setup();
        this.popup = useService("popup");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    }
    
    async onClick() {
        try {
            // Vérifier droit Barman
            const grp = await this.rpc('/pos_distributeur_boisson/is_barman', {});
            if (!grp?.is_barman) {
                this.notification.add(_t("Accès refusé: réservé aux Barmans"), { type: "danger" });
                return;
            }
            
            const pos = this.env.services.pos;
            if (!pos) {
                this.notification.add(_t("Erreur: Service POS non disponible"), { type: "danger" });
                return;
            }
            const currentOrder = pos.get_order();
            if (!currentOrder) {
                this.notification.add(_t("Aucune commande active"), { type: "warning" });
                return;
            }
            let lines = [];
            if (currentOrder.get_orderlines) lines = currentOrder.get_orderlines();
            else if (currentOrder.orderlines) lines = currentOrder.orderlines;
            if (lines.length === 0) {
                this.notification.add(_t("Aucun produit dans la commande"), { type: "info" });
                return;
            }
            const items = [];
            for (const line of lines) {
                let product = line.get_product ? line.get_product() : line.product;
                if (product) {
                    const isDistributeur = product.is_distributeur_boisson || product.needs_distributor || product.distributeur_boisson;
                    const isCocktail = product.is_combo_product;
                    if (isDistributeur) {
                        let quantity = line.get_quantity ? line.get_quantity() : (line.quantity ?? line.qty ?? 1);
                        if (isCocktail) {
                            items.push({ type: 'cocktail', product_id: product.id, product_name: product.name, quantity, server_name: 'Serveur' });
                        } else {
                            // Laisser le backend injecter server_no (employé)
                            items.push({ plu_no: product.plu_code?.replace('PLU','PLU') || product.plu_code || 'PLU1', sign: '+', quantity, product_name: product.name });
                        }
                    }
                }
            }
            if (items.length === 0) {
                this.notification.add(_t("Aucun produit nécessitant le distributeur dans cette commande"), { type: "info" });
                return;
            }
            this.notification.add(_t("⏳ Envoi de la commande au distributeur..."), { type: "info" });
            try {
                const connectionTest = await this.rpc('/pos_distributeur_boisson/test_middleware_connection', {});
                if (connectionTest?.success) this.notification.add(_t("✅ Connexion au middleware établie"), { type: "success" });
                else this.notification.add(_t("❌ Impossible de se connecter au middleware"), { type: "warning" });
            } catch (_) {}
            const results = [];
            let successCount = 0;
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                try {
                    let result;
                    if (item.type === 'cocktail') {
                        result = await this.rpc('/pos_distributeur_boisson/send_cocktail_ingredients', { product_id: item.product_id, quantity: item.quantity, server_name: item.server_name });
                    } else {
                        // Passer par le modèle qui injecte server_no et journalise
                        result = await this.rpc('/web/dataset/call_kw', { model: 'pos.session', method: 'send_credit_to_middleware', args: [item], kwargs: {} });
                    }
                    if (result?.success) { successCount++; results.push({ item, success: true, message: result.message || 'OK', details: result.details || null, ingredients_list: result.ingredients_list || null }); }
                    else { results.push({ item, success: false, message: result?.error || result?.message || 'Erreur inconnue', details: result?.details || null }); }
                } catch (error) {
                    results.push({ item, success: false, message: `Erreur réseau: ${error.message}` });
                }
            }
            const summary = successCount === items.length;
            this.notification.add(`${summary ? '✅' : '❌'} ${summary ? _t('Commande envoyée avec succès') : _t("Erreurs lors de l'envoi") } (${successCount}/${items.length})`, { type: summary ? "success" : "danger" });
        } catch (error) {
            this.notification.add(`❌ ${error.message}`, { type: "danger" });
        }
    }
}

ProductScreen.addControlButton({
    component: DistributeurButton,
    condition: () => true,
});