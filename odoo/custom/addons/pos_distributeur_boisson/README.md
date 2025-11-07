# Module POS Distributeur Boisson

## Description

Ce module étend le Point de Vente (POS) d'Odoo pour gérer un distributeur de boissons automatique. Il permet de distinguer entre les boissons simples et les cocktails, et d'envoyer les commandes appropriées au distributeur.

## 🚀 Fonctionnalités

### ✅ Interface utilisateur
- **Bouton distributeur** intégré dans l'interface POS
- **Popup de sélection** avec les boissons configurées en base
- **Codes PLU** configurables par produit
- **Communication HTTP** avec le middleware
- **Interface responsive** et intuitive

### ✅ Gestion des boissons
- **Configuration en base de données** - Les boissons sont des produits Odoo normaux
- **Champ PLU** sur chaque produit pour identification par le distributeur
- **Facturation automatique** des boissons distribuées
- **Gestion des stocks** intégrée d'Odoo
- **Prix et volumes** configurables par produit
- **Distinction automatique** entre boissons simples et cocktails

### ✅ Types de boissons supportés

#### 🥤 Boissons simples
- **Configuration** : Produit normal avec code PLU
- **Distribution** : Un seul crédit envoyé au distributeur
- **Exemple** : Coca-Cola (PLU001) → nombre de crédits configuré pour PLU001

#### 🍹 Cocktails (Produits Combo)
- **Configuration** : Produit de type "Combo" avec ingrédients
- **Distribution** : Un crédit par ingrédient envoyé au distributeur
- **Exemple** : Mojito (combo) → 1 crédit pour PLU010 (rhum) + 1 crédit pour PLU011 (menthe) + 1 crédit pour PLU012 (citron vert)

### ✅ Crédits configurables par boisson
#### 🎛️ Fonctionnalité avancée
- **Configuration flexible** : Chaque boisson peut nécessiter un nombre différent de crédits
- **Exemples d'utilisation** :
  - **Petite portion** : 1 crédit (ex: Expresso)
  - **Portion normale** : 2 crédits (ex: Café long)
  - **Grande portion** : 3 crédits (ex: Café américain)
  - **Portion XXL** : 5 crédits (ex: Méga smoothie)

#### ⚙️ Configuration
1. **Dans la fiche produit**, définir le champ **"Crédits par service"**
2. **Le système enverra automatiquement** le nombre de crédits configuré
3. **Pour une quantité de 2**, si la boisson nécessite 3 crédits, le système enverra 6 crédits au total (3 × 2)

#### 📊 Comportement
- **Envoi séquentiel** : Les crédits sont envoyés un par un au distributeur
- **Gestion d'erreur** : Si un crédit échoue, l'envoi s'arrête
- **Logs détaillés** : Chaque crédit envoyé est tracé dans les logs

### ✅ Communication avec le middleware
- **PLU001** - Coca-Cola (25cl) - 2,50€
- **PLU002** - Fanta Orange (25cl) - 2,50€
- **PLU003** - Sprite (25cl) - 2,50€
- **PLU005** - Eau Minérale (50cl) - 1,50€
- **PLU007** - Café (15cl) - 1,80€

### ✅ Communication avec le distributeur
- **Middleware HTTP** pour la communication
- **Port RS232** pour l'appareil distributeur
- **Codes PLU** envoyés automatiquement
- **Réponse "OK"** du distributeur
- **Gestion d'erreurs** complète

## 📋 Flux de fonctionnement

```
1. POS JS → déclenche action
2. Backend Odoo → appelle : http://127.0.0.1:8000/envoyer/PLU001
3. Mini app → écrit sur le port RS232 : PLU001\r\n
4. Distributeur → sert 25cl de Coca
5. Distributeur → renvoie "OK"
6. Mini app → retourne la réponse à Odoo
7. POS → affiche "Boisson servie avec succès"
```

## 🛠️ Installation

### 1. Prérequis
- Odoo 17.0
- Module `point_of_sale` activé
- Middleware accessible sur le réseau
- Distributeur connecté via RS232

### 2. Configuration
1. **Installer le module** dans Odoo
2. **Aller dans Paramètres > Point de Vente > Distributeur de Boissons**
3. **Configurer les paramètres** :
   - **URL du middleware** (défaut: http://127.0.0.1:5000)
   - **Numéro du serveur** (défaut: 1) - Identifiant unique du distributeur
   - **Token d'authentification** (optionnel)
4. **Tester la connexion** avec le middleware

### 3. Configuration des boissons

#### 🥤 Configuration d'une boisson simple
1. **Aller dans Point de Vente > Produits**
2. **Créer un nouveau produit** avec les champs suivants :
   - **Nom** : Nom de la boisson (ex: Coca-Cola)
   - **Type de produit** : Consommable ou Service
   - **Code PLU** : Code unique pour le distributeur (ex: PLU001)
   - **Prix** : Prix de vente
   - **Volume distributeur** : Volume de la boisson (ex: 25cl)
   - **Crédits par service** : Nombre de crédits à envoyer (ex: 1 pour une boisson normale, 3 pour une grande portion)
   - **Cocher "Boisson du distributeur"**
   - **Cocher "Nécessite le distributeur"**
   - **Cocher "Disponible dans POS"**

#### 🍹 Configuration d'un cocktail (Combo)
1. **Créer les produits ingrédients** (si pas déjà fait) :
   - Chaque ingrédient doit avoir son propre code PLU
   - Exemple : Rhum (PLU010), Menthe (PLU011), Citron vert (PLU012)

2. **Créer le produit cocktail** :
   - **Nom** : Nom du cocktail (ex: Mojito)
   - **Type de produit** : **Combo** (important !)
   - **Prix** : Prix de vente du cocktail
   - **Cocher "Boisson du distributeur"**
   - **Cocher "Nécessite le distributeur"**
   - **Cocher "Disponible dans POS"**

3. **Configurer le combo** :
   - **Aller dans l'onglet "Combos"**
   - **Ajouter un combo** avec les ingrédients :
     - Rhum (PLU010)
     - Menthe (PLU011) 
     - Citron vert (PLU012)

4. **Synchroniser les produits** avec le POS si nécessaire

### 4. Utilisation
1. Ouvrir une session POS
2. Cliquer sur le bouton "Distributeur"
3. Sélectionner la boisson souhaitée
4. Cliquer sur "Distribuer la boisson"
5. Le produit est automatiquement ajouté à la commande avec le bon prix et les bonnes informations

## 🎯 Avantages du nouveau système

### ✅ Facturation intégrée
- **Produits réels** : Chaque boisson est un produit Odoo normal
- **Facturation automatique** : Prix, taxes, et TVA correctement appliqués
- **Traçabilité** : Chaque vente est enregistrée avec le bon produit

### ✅ Gestion flexible
- **Configuration simple** : Ajouter/modifier des boissons via l'interface Odoo
- **Prix dynamiques** : Les prix sont mis à jour automatiquement
- **Stocks gérés** : Possibilité d'activer la gestion des stocks

### ✅ Maintenance facilitée
- **Pas de code dur** : Plus besoin de modifier le code pour ajouter des boissons
- **Interface admin** : Gestion via l'interface utilisateur d'Odoo
- **Validation automatique** : Vérification des codes PLU uniques

## 🔧 Architecture technique

### Structure du module
```
pos_distributeur_boisson/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── pos_session.py          # Logique métier et communication
│   └── res_config_settings.py  # Configuration système
├── views/
│   └── pos_config_views.xml    # Configuration et produit
└── static/src/
    ├── css/
    │   └── distributeur.css    # Styles CSS
    ├── js/
    │   └── distributeur.js     # Logique JavaScript
    └── xml/
        └── distributeur.xml    # Templates Owl
```

### Composants principaux

#### 1. **Modèle Python** (`models/pos_session.py`)
```python
# Méthodes principales
def distribuer_boisson(self, code_plu)         # Distribution d'une boisson
def obtenir_boissons_disponibles(self)         # Liste des boissons
def verifier_statut_middleware(self)           # Vérification du middleware
def _send_to_middleware(self, code_plu)        # Communication HTTP
```

#### 2. **Interface JavaScript** (`static/src/js/distributeur.js`)
```javascript
// Composants Owl
export class DistributeurButton       // Bouton principal
export class DistributeurPopup        // Popup de sélection
```

#### 3. **Templates XML** (`static/src/xml/distributeur.xml`)
```xml
<!-- Templates Owl pour l'interface -->
<t t-name="pos_distributeur_boisson.DistributeurButton">
<t t-name="pos_distributeur_boisson.DistributeurPopup">
```

## 🔌 Communication avec le middleware

### URL de l'API
- **Base URL**: `http://127.0.0.1:8000`
- **Endpoint**: `/envoyer/{code_plu}`
- **Méthode**: GET
- **Exemple**: `http://127.0.0.1:8000/envoyer/PLU001`

### Réponse attendue
- **Succès**: `OK` (texte simple)
- **Erreur**: Tout autre texte sera considéré comme une erreur

### Vérification du statut
- **Endpoint**: `/status`
- **Méthode**: GET
- **URL**: `http://127.0.0.1:8000/status`

## ⚙️ Configuration du middleware

### Paramètres configurables
- **URL du middleware**: Accessible via Paramètres > Point de Vente > Distributeur de Boissons
- **Numéro du serveur**: Identifiant unique du distributeur (1, 2, 3...)
- **Token d'authentification**: Optionnel pour sécuriser les communications

### Données envoyées au middleware
Le système envoie un objet JSON avec les informations suivantes :
```json
{
  "server_no": 1,           // Numéro du serveur (configurable)
  "plu_no": "PLU001",       // Code PLU complet du produit
  "sign": "+",             // "+" pour distribuer, "-" pour débiter
  "quantity": 1             // Quantité à distribuer
}
```

### Explication des champs
- **server_no**: Numéro d'identification du distributeur (configurable dans les paramètres)
- **plu_no**: Code PLU complet du produit (ex: PLU001, PLU002...)
- **sign**: Signe de l'opération ("+" pour ajouter un crédit/distribuer, "-" pour débiter)
- **quantity**: Nombre d'unités à distribuer

## 🎨 Personnalisation

### Ajouter une nouvelle boisson
1. **Aller dans Point de Vente > Boissons du Distributeur**
2. **Cliquer sur "Nouveau"**
3. **Remplir les informations** :
   - **Nom** : Nom de la boisson (ex: Limonade)
   - **Code PLU** : Code unique (ex: PLU009)
   - **Prix** : Prix de vente (ex: 2.20)
   - **Volume** : Volume (ex: 25cl)
   - **Cocher "Boisson du distributeur"**
   - **Cocher "Disponible dans POS"**
4. **Sauvegarder** le produit
5. **Configurer le code PLU** dans le distributeur physique
6. **Synchroniser** les produits avec le POS si nécessaire

### Modifier l'URL du middleware
1. Aller dans **Paramètres > Distributeur de Boissons**
2. Modifier l'URL du middleware
3. Sauvegarder

## 🐛 Résolution des problèmes

### Le bouton n'apparaît pas
1. Vérifier l'installation du module
2. Vider le cache du navigateur
3. Redémarrer Odoo

### Erreur de connexion au middleware
1. Vérifier que le middleware est démarré
2. Tester l'URL manuellement : `http://127.0.0.1:8000/status`
3. Vérifier la configuration réseau

### Le distributeur ne répond pas
1. Vérifier la connexion RS232
2. Tester manuellement le code PLU
3. Vérifier les logs du middleware

### Erreur "Code PLU non disponible"
1. Vérifier que le code PLU existe dans la configuration
2. Redémarrer le module si nécessaire

## 📊 Logs et débogage

### Logs Odoo
```bash
# Voir les logs du module
tail -f /var/log/odoo/odoo.log | grep distributeur
```

### Logs du middleware
- Vérifier les logs du middleware pour les requêtes reçues
- Tester manuellement les endpoints

### Test manuel
```bash
# Tester le middleware
curl http://127.0.0.1:8000/envoyer/PLU001

# Vérifier le statut
curl http://127.0.0.1:8000/status
```

## 🔄 Versions

### Version 2.0.0 (Actuelle)
- ✅ Communication HTTP avec middleware
- ✅ Codes PLU pour chaque boisson
- ✅ Interface simplifiée
- ✅ Communication RS232 via middleware
- ✅ Configuration système complète
- ✅ Gestion d'erreurs robuste

### Améliorations possibles
- 🔄 Plus de boissons
- 🔄 Configuration par POS
- 🔄 Statistiques de consommation
- 🔄 Gestion des stocks en temps réel
- 🔄 Interface d'administration du middleware

## 📞 Support

### En cas de problème
1. Vérifier les logs Odoo
2. Tester la connexion au middleware
3. Vérifier la configuration RS232
4. Consulter ce README

### Configuration minimale requise
- **Middleware**: Accessible sur le réseau
- **Distributeur**: Connecté via RS232
- **Codes PLU**: Configurés dans le distributeur
- **Odoo**: Version 17.0 avec module POS

---

**Développé avec ❤️ pour la distribution automatique de boissons**

*Version PLU compatible avec les distributeurs RS232* 

 cd /opt/odoo/odoo17 && python3 odoo-bin -d odoo17 --dev=reload --log-level=info