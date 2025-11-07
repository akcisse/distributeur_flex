# Module POS Distributeur de Boissons - Documentation Complète

## 📋 Table des matières
1. [Vue d'ensemble](#vue-densemble)
2. [Architecture du module](#architecture-du-module)
3. [Fonctionnalités principales](#fonctionnalités-principales)
4. [Installation et configuration](#installation-et-configuration)
5. [Utilisation](#utilisation)
6. [API et endpoints](#api-et-endpoints)
7. [Modèles de données](#modèles-de-données)
8. [Sécurité](#sécurité)
9. [Dépannage](#dépannage)
10. [Développement](#développement)

## 🎯 Vue d'ensemble

Le module **POS Distributeur de Boissons** est une extension complète du Point de Vente (POS) d'Odoo 17.0 qui permet d'intégrer un distributeur automatique de boissons dans le système de vente. Le module gère à la fois les boissons simples et les cocktails complexes avec une interface intuitive et une communication robuste avec le middleware Hart96.

### 🎨 Caractéristiques principales
- **Interface POS intégrée** avec bouton distributeur
- **Gestion des cocktails** avec ingrédients multiples
- **Communication middleware** via HTTP/JSON
- **Codes PLU** configurables par produit
- **Système de crédits** flexible
- **Gestion d'erreurs** complète
- **Logs détaillés** pour le débogage

## 🏗️ Architecture du module

### Structure des dossiers
```
pos_distributeur_boisson/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── combo.py                    # Gestion des combos/cocktails
│   ├── pos_session.py              # Logique de session POS
│   ├── product_product.py          # Extension des produits
│   ├── product_template.py         # Extension des templates
│   ├── pos_order_line.py          # Extension des lignes de commande
│   ├── res_config_settings.py      # Configuration du module
│   ├── pos_config.py              # Configuration POS
│   ├── ingredient_selection_wizard.py # Assistant de sélection
│   └── migration.py               # Scripts de migration
├── controllers/
│   ├── __init__.py
│   └── main.py                    # Contrôleurs HTTP
├── views/
│   ├── product_combo_views.xml    # Vues des combos
│   ├── product_views_simple.xml   # Vues des produits
│   ├── ingredient_selection_wizard_views.xml # Vues de l'assistant
│   └── res_config_settings_views.xml # Vues de configuration
├── static/
│   └── src/
│       ├── js/
│       │   ├── distributeur.js    # Logique JS du distributeur
│       │   ├── combo_product.js   # Logique JS des combos
│       │   └── combo_popup.js     # Logique JS des popups
│       ├── css/
│       │   ├── distributeur.css   # Styles du distributeur
│       │   └── combo_ingredients.css # Styles des ingrédients
│       └── xml/
│           ├── distributeur.xml   # Template XML du distributeur
│           └── combo_popup.xml    # Template XML des popups
├── data/
│   ├── demo_products.xml          # Données de démonstration
│   ├── combo_test_data.xml        # Données de test des combos
│   └── pos_actions.xml           # Actions POS
└── security/
    ├── ir.model.access.csv        # Permissions d'accès
    └── security.xml               # Règles de sécurité
```

### 🔄 Flux de données
```
1. Interface POS → JavaScript
2. JavaScript → Contrôleur HTTP
3. Contrôleur → Modèles Odoo
4. Modèles → Middleware Client
5. Middleware Client → API Hart96
6. API Hart96 → Distributeur RS232
7. Distributeur → Réponse
8. Réponse → Interface POS
```

## ⚡ Fonctionnalités principales

### 🥤 Gestion des boissons simples
- **Configuration** : Produit standard avec code PLU
- **Distribution** : Un crédit par portion
- **Exemple** : Coca-Cola (PLU001) → 1 crédit

### 🍹 Gestion des cocktails
- **Configuration** : Produit de type "Combo" avec ingrédients
- **Distribution** : Un crédit par ingrédient
- **Exemple** : Mojito → 1 crédit rhum + 1 crédit menthe + 1 crédit citron

### 🎛️ Système de crédits flexible
- **Configuration** : Crédits par portion configurables
- **Exemples** :
  - Expresso : 1 crédit
  - Café long : 2 crédits
  - Café américain : 3 crédits
  - Smoothie XXL : 5 crédits

### 🔧 Configuration avancée
- **URL middleware** configurable
- **Numéro de serveur** unique
- **Token d'authentification** optionnel
- **Timeouts** configurables
- **Logs détaillés** activables

## 🚀 Installation et configuration

### Prérequis
- **Odoo 17.0** installé et fonctionnel
- **Module point_of_sale** activé
- **Middleware Hart96** accessible
- **Distributeur RS232** connecté
- **Python requests** installé

### Installation
1. **Copier le module** dans le dossier `addons`
2. **Mettre à jour la liste** des modules dans Odoo
3. **Installer le module** via l'interface d'administration
4. **Vérifier les permissions** de la base de données

### Configuration initiale
1. **Aller dans** Paramètres > Point de Vente > Distributeur de Boissons
2. **Configurer** :
   - URL du middleware (défaut: http://127.0.0.1:5000)
   - Numéro du serveur (défaut: 1)
   - Token d'authentification (optionnel)
3. **Tester la connexion** avec le middleware
4. **Configurer les produits** avec leurs codes PLU

### Configuration des produits
1. **Créer/Modifier** un produit
2. **Activer** "Nécessite distributeur" si applicable
3. **Saisir** le code PLU du produit
4. **Configurer** le volume distributeur (en cl)
5. **Définir** le nombre de crédits par portion
6. **Pour les cocktails** : configurer les ingrédients

## 📖 Utilisation

### Interface POS
1. **Ouvrir** une session POS
2. **Sélectionner** un produit boisson
3. **Cliquer** sur le bouton "Distributeur"
4. **Choisir** la quantité si applicable
5. **Confirmer** la distribution
6. **Vérifier** le statut de distribution

### Gestion des cocktails
1. **Créer** un produit de type "Combo"
2. **Configurer** les catégories d'ingrédients
3. **Ajouter** les options d'ingrédients
4. **Sélectionner** les ingrédients spécifiques
5. **Tester** la distribution du cocktail

### Monitoring
- **Logs détaillés** dans les logs Odoo
- **Statut middleware** vérifiable
- **Historique** des distributions
- **Gestion d'erreurs** complète

## 🔌 API et endpoints

### Endpoints disponibles

#### Test de connexion
```
POST /pos_distributeur_boisson/test
```
**Réponse** :
```json
{
    "success": true,
    "message": "Contrôleur POS Distributeur fonctionnel",
    "timestamp": "2024-01-01 12:00:00"
}
```

#### Envoi de crédit
```
POST /pos_distributeur_boisson/send_credit_to_middleware
```
**Paramètres** :
```json
{
    "server_no": 1,
    "plu_no": "PLU001",
    "sign": 1,
    "quantity": 1
}
```

#### Distribution de cocktail
```
POST /pos_distributeur_boisson/send_cocktail_ingredients
```
**Paramètres** :
```json
{
    "product_id": 123,
    "quantity": 1,
    "server_name": "Serveur 1"
}
```

### Communication middleware
Le module utilise la classe `MiddlewareClient` pour communiquer avec le middleware Hart96 :

```python
client = MiddlewareClient(env)
result = client.send_credit({
    'server_no': 1,
    'plu_no': 'PLU001',
    'sign': 1,
    'quantity': 1
})
```

## 📊 Modèles de données

### PosComboCategory
**Description** : Catégorie d'ingrédients pour les cocktails
- `name` : Nom de la catégorie
- `sequence` : Ordre d'affichage
- `active` : Statut actif/inactif
- `option_ids` : Options de la catégorie

### PosComboOption
**Description** : Option d'ingrédient pour les cocktails
- `name` : Nom de l'option
- `combo_category_id` : Catégorie parente
- `product_id` : Produit associé
- `price_extra` : Prix supplémentaire
- `plu_code` : Code PLU du distributeur
- `volume_distributeur` : Volume en centilitres
- `credits_per_serving` : Nombre de crédits par portion

### ProductComboLine
**Description** : Ligne de combo pour un produit template
- `product_tmpl_id` : Produit template parent
- `combo_category_id` : Catégorie d'ingrédients
- `required` : Sélection obligatoire
- `min_selections` : Nombre minimum de sélections
- `max_selections` : Nombre maximum de sélections

### Extension ProductTemplate
**Champs ajoutés** :
- `is_combo_product` : Produit de type combo
- `combo_line_ids` : Lignes de combo
- `selected_combo_ingredient_ids` : Ingrédients sélectionnés
- `combo_ingredient_ids` : Ingrédients calculés
- `combo_volume_total` : Volume total calculé

### Extension ProductProduct
**Champs ajoutés** :
- `plu_code` : Code PLU du distributeur
- `volume_distributeur` : Volume en centilitres
- `needs_distributor` : Nécessite le distributeur
- `credits_per_serving` : Crédits par portion
- `is_combo_product` : Produit de type combo

## 🔒 Sécurité

### Permissions d'accès
Le module définit des permissions spécifiques dans `security/ir.model.access.csv` :

- **pos.combo.category** : Lecture/Écriture pour les utilisateurs POS
- **pos.combo.option** : Lecture/Écriture pour les utilisateurs POS
- **product.combo.line** : Lecture/Écriture pour les utilisateurs POS

### Règles de sécurité
- **Accès aux combos** : Seuls les utilisateurs autorisés
- **Modification des produits** : Permissions standard Odoo
- **API endpoints** : Authentification utilisateur requise

### Middleware
- **Communication sécurisée** via HTTPS (recommandé)
- **Token d'authentification** configurable
- **Timeouts** pour éviter les blocages
- **Validation** des données reçues

## 🛠️ Dépannage

### Problèmes courants

#### 1. Erreur de connexion middleware
**Symptômes** : Erreur "Connexion impossible au middleware"
**Solutions** :
- Vérifier l'URL du middleware
- Vérifier que le middleware est démarré
- Vérifier les paramètres réseau
- Tester avec curl : `curl -X POST http://127.0.0.1:5000/test`

#### 2. Code PLU non reconnu
**Symptômes** : Erreur "Code PLU non trouvé"
**Solutions** :
- Vérifier la configuration du produit
- Vérifier que le code PLU est saisi
- Vérifier que le produit est actif
- Vérifier les permissions de la base de données

#### 3. Cocktail non distribué
**Symptômes** : Erreur lors de la distribution de cocktail
**Solutions** :
- Vérifier la configuration des ingrédients
- Vérifier que tous les ingrédients ont un code PLU
- Vérifier les permissions des tables de relation
- Consulter les logs détaillés

#### 4. Erreur de permissions
**Symptômes** : Erreur "Permission denied"
**Solutions** :
- Vérifier les permissions de la base de données
- Exécuter le script de migration
- Vérifier les permissions utilisateur
- Redémarrer Odoo

### Logs et débogage
Le module génère des logs détaillés avec les préfixes suivants :
- `🧪` : Tests et vérifications
- `📤` : Envoi de données
- `🍹` : Gestion des cocktails
- `🔧` : Configuration et maintenance
- `❌` : Erreurs et exceptions

### Commandes de diagnostic
```bash
# Vérifier les logs Odoo
tail -f /var/log/odoo/odoo.log | grep pos_distributeur_boisson

# Tester la connexion middleware
curl -X POST http://127.0.0.1:5000/test

# Vérifier les permissions de base de données
psql -U odoo -d odoo17 -c "SELECT * FROM information_schema.table_privileges WHERE table_name LIKE '%combo%';"
```

## 🚀 Développement

### Structure de développement
```
pos_distributeur_boisson/
├── models/           # Logique métier
├── controllers/      # API HTTP
├── views/           # Interface utilisateur
├── static/          # Assets frontend
├── data/            # Données de démonstration
└── security/        # Permissions et sécurité
```

### Ajout de nouvelles fonctionnalités

#### 1. Nouveau type de boisson
1. **Étendre** le modèle `product.product`
2. **Ajouter** les champs nécessaires
3. **Créer** les vues correspondantes
4. **Implémenter** la logique de distribution
5. **Tester** avec le middleware

#### 2. Nouvelle interface
1. **Créer** les fichiers JS/CSS/XML
2. **Déclarer** dans `__manifest__.py`
3. **Implémenter** la logique frontend
4. **Tester** dans le POS

#### 3. Nouvelle API
1. **Créer** le contrôleur HTTP
2. **Implémenter** la logique métier
3. **Ajouter** la documentation
4. **Tester** avec Postman/curl

### Tests
Le module inclut des données de test dans `data/` :
- `demo_products.xml` : Produits de démonstration
- `combo_test_data.xml` : Données de test des combos
- `pos_actions.xml` : Actions POS de test

### Migration
Le module inclut des scripts de migration dans `models/migration.py` :
- Correction des permissions de base de données
- Suppression des anciennes contraintes SQL
- Mise à jour des données existantes

## 📞 Support

### Documentation
- **README principal** : Vue d'ensemble et installation
- **README_COMBO.md** : Documentation spécifique aux combos
- **Code source** : Commentaires détaillés en français

### Maintenance
- **Mises à jour** : Compatible Odoo 17.0+
- **Sécurité** : Corrections de sécurité régulières
- **Performance** : Optimisations continues
- **Compatibilité** : Tests avec différentes versions

### Contribution
- **Code source** : Disponible sur demande
- **Documentation** : Mise à jour continue
- **Tests** : Suite de tests automatisés
- **Feedback** : Bienvenu et encouragé

---

**Version** : 1.1.1  
**Compatibilité** : Odoo 17.0+  
**Licence** : LGPL-3  
**Auteur** : Odoo Community  
**Support** : Documentation et logs détaillés inclus 