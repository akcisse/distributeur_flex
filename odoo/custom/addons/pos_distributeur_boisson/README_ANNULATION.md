# 🔄 Système d'Annulation Automatique des Crédits

## 📋 Vue d'ensemble

Ce document décrit le système d'annulation automatique des crédits envoyés au distributeur Flex/Hart96 lorsqu'un client annule sa commande avant que les boissons ne soient servies.

---

## 🎯 Fonctionnalité

### Cas d'Usage Principal

```
1. Client commande → Coca-Cola + Mojito
2. Barman clique "Distributeur" → Crédits envoyés au Flex ✅
3. ⏰ AVANT que les boissons soient servies
4. Client change d'avis et annule
5. → Système annule AUTOMATIQUEMENT les crédits 🔄
```

### Déclencheurs d'Annulation

L'annulation automatique se déclenche dans ces cas :

1. **Suppression de ligne** : `unlink()`
   - Barman supprime une ligne de commande dans le POS
   - Tous les crédits actifs de cette ligne sont annulés

2. **Réduction de quantité** : `write({'qty': new_qty})`
   - Barman réduit la quantité (ex: 3 → 1)
   - Les crédits en excès sont annulés (2 dans cet exemple)

---

## 🏗️ Architecture Technique

### Modèles Modifiés

#### 1. **`pos.credit.log`** (Extended)

Nouveaux champs pour tracking :

```python
# Lien vers la ligne de commande
order_line_id = Many2one('pos.order.line')

# Statut du crédit
status = Selection([
    ('sent', 'Envoyé'),      # Crédit envoyé, en attente
    ('served', 'Servi'),     # Boisson servie
    ('cancelled', 'Annulé'), # Crédit annulé
    ('refunded', 'Remboursé')
])

# Traçabilité annulation
cancelled_at = Datetime()
cancelled_by = Many2one('res.users')
cancellation_response = Text()

# Identifiant unique
credit_id = Char()  # Format: CRED-A1B2C3D4

# Flag pour lignes d'annulation
is_cancellation = Boolean()
```

#### 2. **`pos.order.line`** (Extended)

Nouveaux champs et méthodes :

```python
# Relation inverse avec les crédits
credit_ids = One2many('pos.credit.log', 'order_line_id')

# Indicateur si crédits envoyés
credits_sent = Boolean(compute='_compute_credits_sent')

# Méthodes principales
def unlink():
    """Annule crédits avant suppression"""
    
def write(vals):
    """Annule crédits si quantité réduite"""
    
def _cancel_credit_in_flex(credit_log):
    """Envoie annulation au Flex"""
    
def _cancel_quantity_credits(line, qty_to_cancel):
    """Annule X crédits"""
```

---

## 🔄 Flux d'Annulation Détaillé

### Étape 1 : Détection

```python
# Dans pos.order.line.unlink()
def unlink(self):
    for line in self:
        # Vérifier si produit nécessite distributeur
        if line.product_id.needs_distributor:
            # Chercher crédits actifs
            active_credits = env['pos.credit.log'].search([
                ('order_line_id', '=', line.id),
                ('status', '=', 'sent')
            ])
```

### Étape 2 : Préparation Annulation

```python
# Données d'annulation avec SIGNE MOINS
cancel_data = {
    'server_no': credit_log.server_no,  # Ex: 1
    'plu_no': credit_log.plu_no,        # Ex: "PLU001"
    'sign': '-',  # ❗ CRUCIAL: Signe moins = annulation
    'quantity': credit_log.quantity     # Ex: 1
}
```

### Étape 3 : Envoi au Middleware

```python
# Utilise MiddlewareClient
client = MiddlewareClient(env)
result = client.send_credit(cancel_data, auto_connect=True)
```

### Étape 4 : Mise à Jour Logs

Si succès :
```python
# 1. Mettre à jour le log original
credit_log.write({
    'status': 'cancelled',
    'cancelled_at': now(),
    'cancelled_by': user.id,
    'cancellation_response': response
})

# 2. Créer une ligne d'annulation (traçabilité)
env['pos.credit.log'].create({
    'product_name': '🔄 ANNULATION - Coca-Cola',
    'is_cancellation': True,
    'status': 'cancelled',
    # ... autres champs
})
```

---

## 📊 Interface Utilisateur

### Journal des Crédits Amélioré

**Vue Liste avec Couleurs :**

- 🟢 Vert : Crédit envoyé (`status = 'sent'`)
- 🔵 Bleu : Crédit servi (`status = 'served'`)
- 🟠 Orange : Ligne d'annulation (`is_cancellation = True`)
- ⚪ Gris : Crédit annulé (`status = 'cancelled'`)

**Filtres Disponibles :**

- `Envoyés` : Crédits actifs
- `Servis` : Boissons distribuées
- `Annulés` : Crédits annulés
- `Annulations` : Lignes d'annulation
- `Aujourd'hui` / `Cette semaine` / `Ce mois`

**Groupements :**

- Par Statut
- Par Utilisateur
- Par Employé
- Par Session
- Par Produit
- Par Date

### Exemple de Vue

```
┌─────────────────────────────────────────────────────────────────┐
│ Date/Heure        │ Statut          │ Produit        │ PLU     │
├─────────────────────────────────────────────────────────────────┤
│ 2025-10-14 10:30  │ 📤 Envoyé       │ Coca-Cola      │ PLU001  │
│ 2025-10-14 10:30  │ 📤 Envoyé       │ Mojito-Rhum    │ PLU010  │
│ 2025-10-14 10:30  │ 📤 Envoyé       │ Mojito-Menthe  │ PLU011  │
│ 2025-10-14 10:31  │ 🔄 Annulation   │ Mojito-Rhum    │ PLU010  │ ← Nouveau
│ 2025-10-14 10:31  │ 🔄 Annulation   │ Mojito-Menthe  │ PLU011  │ ← Nouveau
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Sécurité

### Vérifications

1. **Droits Barman** : Seuls les membres du groupe `pos_user_org.group_pos_barman` peuvent annuler
2. **Statut vérifié** : On n'annule QUE les crédits avec `status = 'sent'`
3. **Traçabilité complète** : Chaque annulation est loggée avec `cancelled_by` et `cancelled_at`

### Logs de Sécurité

```python
# Exemple de logs générés
_logger.info("🗑️ Suppression de ligne(s) détectée")
_logger.info("🔍 Ligne #42: Coca-Cola - Vérification crédits...")
_logger.info("⚠️ 1 crédit(s) actif(s) trouvé(s)")
_logger.info("🔄 Annulation crédit #123: Coca-Cola (PLU001)")
_logger.info("📤 Envoi annulation au middleware: {'sign': '-', ...}")
_logger.info("✅ Crédit #123 annulé avec succès")
```

---

## 🧪 Cas de Test

### Test 1 : Annulation Simple

```
1. Créer commande avec 1 Coca-Cola
2. Envoyer au distributeur → Crédit envoyé
3. Supprimer ligne Coca-Cola
4. ✅ Vérifier : Crédit annulé (status = 'cancelled')
5. ✅ Vérifier : Ligne d'annulation créée (is_cancellation = True)
```

### Test 2 : Réduction Quantité

```
1. Créer commande avec 3 Coca-Cola
2. Envoyer au distributeur → 3 crédits envoyés
3. Réduire quantité à 1
4. ✅ Vérifier : 2 crédits annulés
5. ✅ Vérifier : 1 crédit reste actif
```

### Test 3 : Cocktail Multi-Ingrédients

```
1. Créer commande avec 1 Mojito (3 ingrédients)
2. Envoyer au distributeur → 3 crédits envoyés (PLU010, PLU011, PLU012)
3. Supprimer ligne Mojito
4. ✅ Vérifier : 3 crédits annulés
5. ✅ Vérifier : 3 lignes d'annulation créées
```

### Test 4 : Échec Annulation

```
1. Créer commande avec 1 Coca-Cola
2. Envoyer au distributeur
3. Middleware/Flex devient indisponible
4. Supprimer ligne Coca-Cola
5. ✅ Vérifier : Échec loggé
6. ✅ Vérifier : Crédit reste en status 'sent'
```

---

## 🔧 Configuration Middleware

### Format des Données Envoyées

**Crédit Normal (Ajout) :**
```json
{
  "server_no": 1,
  "plu_no": 1,
  "sign": "+",
  "quantity": 1
}
```

**Crédit Annulation (Retrait) :**
```json
{
  "server_no": 1,
  "plu_no": 1,
  "sign": "-",  // ❗ Signe moins
  "quantity": 1
}
```

### Réponse Attendue du Middleware

**Succès :**
```json
{
  "success": true,
  "message": "Credit cancelled successfully"
}
```

**Échec :**
```json
{
  "success": false,
  "message": "Cannot cancel: drink already served"
}
```

---

## 📈 Statistiques et Reporting

### Requêtes Utiles

**Taux d'Annulation :**
```python
# Nombre total de crédits
total = env['pos.credit.log'].search_count([
    ('is_cancellation', '=', False)
])

# Nombre d'annulations
cancelled = env['pos.credit.log'].search_count([
    ('status', '=', 'cancelled'),
    ('is_cancellation', '=', False)
])

taux = (cancelled / total) * 100
```

**Produits les Plus Annulés :**
```python
cancelled_products = env['pos.credit.log'].read_group(
    [('status', '=', 'cancelled')],
    ['product_name'],
    ['product_name']
)
```

**Annulations par Barman :**
```python
cancellations_by_user = env['pos.credit.log'].read_group(
    [('is_cancellation', '=', True)],
    ['cancelled_by'],
    ['cancelled_by']
)
```

---

## 🚨 Dépannage

### Problème : Annulations ne fonctionnent pas

**Vérifications :**

1. **Middleware supporte `sign: "-"` ?**
   ```bash
   # Tester manuellement
   curl -X POST http://192.168.1.59:5000/api/send-credit \
     -H "Content-Type: application/json" \
     -d '{"server_no": 1, "plu_no": 1, "sign": "-", "quantity": 1}'
   ```

2. **Droits Barman ?**
   ```python
   # Vérifier dans logs
   "⚠️ Utilisateur non-Barman tente d'annuler un crédit"
   ```

3. **Statut correct ?**
   ```python
   # Vérifier dans base de données
   SELECT status FROM pos_credit_log WHERE id = 123;
   # Doit être 'sent' pour être annulable
   ```

### Problème : Crédits annulés mais Flex distribue quand même

**Causes possibles :**

1. **Délai trop court** : Le Flex a déjà commencé la distribution
2. **Communication lente** : L'annulation arrive après le début de service
3. **File d'attente Flex** : Le Flex ne supporte pas l'annulation une fois en file

**Solutions :**

1. Réduire le délai entre commande et validation
2. Ajouter un timer de confirmation (5-10 secondes)
3. Vérifier capacités du Flex

---

## 📝 Notes de Développement

### Améliorations Futures

1. **Délai de Grâce**
   - Ajouter un popup de confirmation avec timer
   - Délai de 5-10 secondes avant envoi effectif

2. **Statut "Serving"**
   - Ajouter un statut intermédiaire entre 'sent' et 'served'
   - Empêcher annulation si distribution en cours

3. **Annulation Partielle Cocktails**
   - Permettre d'annuler seulement certains ingrédients
   - Interface de sélection dans le POS

4. **Dashboard Annulations**
   - Vue graphique des annulations
   - Alertes si taux d'annulation > seuil

5. **API Webhooks**
   - Notification du Flex vers Odoo quand distribution commence
   - Mise à jour automatique du statut en 'serving'

---

## 📞 Support

### Logs à Fournir

En cas de problème, fournir :

```bash
# Logs Odoo (filtré distributeur)
tail -f /var/log/odoo/odoo.log | grep -E "(🔄|🗑️|Annulation)"

# Logs middleware
curl http://192.168.1.59:5000/api/logs

# État de la base de données
SELECT * FROM pos_credit_log 
WHERE order_line_id = X 
ORDER BY create_date DESC;
```

---

**Version** : 1.0.0  
**Date** : 14 octobre 2025  
**Module** : `pos_distributeur_boisson`  
**Compatibilité** : Odoo 17.0+  
**Licence** : LGPL-3


