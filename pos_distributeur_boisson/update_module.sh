#!/bin/bash

# Script de mise à jour du module POS Distributeur de Boissons
# Correction du bouton de suppression qui décrémente au lieu de tout supprimer

echo "=========================================="
echo "  Mise à jour POS Distributeur Boisson"
echo "=========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Vider le cache des assets Odoo
echo -e "${YELLOW}Étape 1/4:${NC} Suppression du cache des assets..."
psql -U odoo -d odoo17 -c "DELETE FROM ir_attachment WHERE name LIKE '%pos_distributeur_boisson%' OR name LIKE '%web.assets%';" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Cache assets supprimé"
else
    echo -e "${YELLOW}⚠${NC} Impossible de supprimer le cache (nécessite les droits PostgreSQL)"
    echo "   Vous pouvez ignorer cette étape et vider le cache du navigateur"
fi
echo ""

# 2. Mettre à jour les permissions
echo -e "${YELLOW}Étape 2/4:${NC} Mise à jour des permissions des fichiers..."
chmod +x /opt/odoo/odoo17/addons/pos_distributeur_boisson/*.sh 2>/dev/null
chmod -R 755 /opt/odoo/odoo17/addons/pos_distributeur_boisson/static/ 2>/dev/null
echo -e "${GREEN}✓${NC} Permissions mises à jour"
echo ""

# 3. Redémarrer Odoo
echo -e "${YELLOW}Étape 3/4:${NC} Redémarrage d'Odoo..."
echo "   Tentative avec systemctl..."
sudo systemctl restart odoo17 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Odoo redémarré avec succès"
    echo "   Attendez 10 secondes que le service démarre..."
    sleep 10
else
    echo -e "${YELLOW}⚠${NC} Impossible de redémarrer via systemctl"
    echo "   ${RED}IMPORTANT:${NC} Vous devez redémarrer Odoo manuellement !"
    echo ""
    echo "   Méthode 1 - Si Odoo est lancé comme service:"
    echo "   ${GREEN}sudo systemctl restart odoo17${NC}"
    echo ""
    echo "   Méthode 2 - Si Odoo est lancé manuellement:"
    echo "   ${GREEN}pkill -f odoo-bin${NC}"
    echo "   ${GREEN}cd /opt/odoo/odoo17 && python3 odoo-bin -d odoo17 --dev=reload${NC}"
    echo ""
fi
echo ""

# 4. Instructions pour finaliser
echo -e "${YELLOW}Étape 4/4:${NC} Instructions de finalisation"
echo ""
echo "Pour finaliser la mise à jour, suivez ces étapes dans Odoo:"
echo ""
echo "1. ${GREEN}Vider le cache du navigateur${NC}"
echo "   - Chrome/Edge: Ctrl + Shift + Delete"
echo "   - Firefox: Ctrl + Shift + Delete"
echo "   - Ou faire un rechargement forcé: Ctrl + Shift + R"
echo ""
echo "2. ${GREEN}Mettre à jour le module${NC}"
echo "   - Aller dans Applications"
echo "   - Rechercher 'POS Distributeur'"
echo "   - Cliquer sur ⋮ → Mettre à jour"
echo ""
echo "3. ${GREEN}Tester dans le POS${NC}"
echo "   - Ouvrir une session POS"
echo "   - Ajouter un article avec quantité 3"
echo "   - Cliquer sur le bouton 🗑️"
echo "   - La quantité devrait passer de 3 → 2 (et non 3 → 0)"
echo ""
echo "4. ${GREEN}Vérifier les logs dans la console${NC}"
echo "   - Ouvrir la console du navigateur (F12)"
echo "   - Vous devriez voir:"
echo "     ${GREEN}✓ Module orderline_delete_button chargé${NC}"
echo "     ${GREEN}✓ Patch ProductScreen chargé${NC}"
echo ""

echo "=========================================="
echo "  ${GREEN}Mise à jour terminée !${NC}"
echo "=========================================="
echo ""
echo "Si le problème persiste:"
echo "  - Vérifiez les logs: tail -f /var/log/odoo/odoo.log"
echo "  - Consultez le fichier: INSTRUCTIONS_MAJ.md"
echo "  - Redémarrez complètement le serveur"
echo ""

