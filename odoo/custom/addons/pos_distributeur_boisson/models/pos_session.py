# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import logging
import requests
import json
from datetime import datetime
from .middleware_client import MiddlewareClient

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_current_server_no(self):
        """Récupère le server_no depuis l’employé courant et lève une erreur s’il est manquant pour un Barman."""
        # Exige le groupe Barmans avant de vérifier
        self._ensure_user_is_barman()
        employee = getattr(self.env.user, 'employee_id', False)
        if not employee or not employee.server_no:
            raise UserError(_('Server No (Distributeur) manquant sur la fiche Employé du Barman.'))
        return int(employee.server_no)

    def _ensure_user_is_barman(self):
        if not self.env.user.has_group('pos_user_org.group_pos_barman'):
            raise UserError(_('Accès refusé: réservé aux Barmans'))

    def _log_credit(self, product_name, plu_no, quantity, success, message, session=None, response=None, order_line_id=None):
        # Ne journaliser que les succès
        if not success:
            return
        try:
            # Générer un ID unique pour ce crédit
            import uuid
            credit_id = f"CRED-{uuid.uuid4().hex[:8].upper()}"
            
            self.env['pos.credit.log'].sudo().create({
                'user_id': self.env.user.id,
                'employee_id': getattr(self.env.user, 'employee_id', False).id if getattr(self.env.user, 'employee_id', False) else False,
                'session_id': (session or self).id if isinstance(self, self.__class__) else False,
                'order_line_id': order_line_id,  # ✨ NOUVEAU
                'product_name': product_name,
                'plu_no': str(plu_no) if plu_no is not None else False,
                'quantity': int(quantity or 1),
                'server_no': self._get_current_server_no(),
                'success': True,
                'status': 'sent',  # ✨ NOUVEAU
                'credit_id': credit_id,  # ✨ NOUVEAU
                'message': message,
                'response_payload': json.dumps(response) if isinstance(response, (dict, list)) else (response or ''),
            })
        except Exception as e:
            _logger.warning(f"Impossible de journaliser le crédit POS: {str(e)}")

    def _get_boissons_disponibles(self):
        '''
        Retourne les boissons disponibles avec leur code PLU
        depuis la base de données des produits
        '''
        products = self.env['product.product'].search_boissons_need_distributor()
        boissons_dict = {}
        for product in products:
            boissons_dict[product.plu_code] = {
                'nom': product.name,
                'prix': product.list_price,
                'volume': product.volume_distributeur or '25cl',
                'description': product.description_sale or product.name,
                'product_id': product.id,
                'barcode': product.barcode or False,
                'needs_distributor': product.needs_distributor,
                'is_combo_product': product.is_combo_product
            }
        _logger.info(f"Boissons nécessitant le distributeur trouvées: {len(boissons_dict)} produits")
        return boissons_dict

    def _send_credit_to_middleware(self, credit_data):
        '''
        Envoie un crédit individuel au middleware Hart96
        Utilise la classe MiddlewareClient centralisée
        '''
        # Forcer server_no depuis l’employé si non fourni
        if not credit_data.get('server_no'):
            credit_data = dict(credit_data, server_no=self._get_current_server_no())
        client = MiddlewareClient(self.env)
        return client.send_credit(credit_data)

    def _is_cocktail(self, product):
        return product.is_combo_product

    def _get_cocktail_ingredients(self, product):
        '''
        Récupère les ingrédients d'un cocktail depuis les combos Odoo
        '''
        _logger.info(f"🍹 Récupération des ingrédients pour le cocktail: {product.name}")
        
        try:
            # Utiliser la méthode get_cocktail_ingredients du modèle product.product
            if hasattr(product, 'get_cocktail_ingredients'):
                ingredients = product.get_cocktail_ingredients()
                _logger.info(f"🍹 Ingrédients récupérés via get_cocktail_ingredients: {len(ingredients) if ingredients else 0}")
                if ingredients:
                    return ingredients
            
            # Si pas d'ingrédients trouvés, essayer de récupérer depuis les ingrédients sélectionnés
            if hasattr(product, 'selected_combo_ingredient_ids') and product.selected_combo_ingredient_ids:
                ingredients = []
                for ingredient_option in product.selected_combo_ingredient_ids:
                    if ingredient_option.product_id and ingredient_option.product_id.plu_code:
                        ingredients.append({
                            'plu_code': ingredient_option.product_id.plu_code,
                            'name': ingredient_option.product_id.name,
                            'price': ingredient_option.product_id.list_price,
                            'quantity': 1,
                            'credits': ingredient_option.credits_per_serving or 1,
                            'product_id': ingredient_option.product_id.id,
                            'category_name': ingredient_option.combo_category_id.name if ingredient_option.combo_category_id else '',
                            'price_extra': ingredient_option.price_extra
                        })
                _logger.info(f"🍹 Ingrédients récupérés via selected_combo_ingredient_ids: {len(ingredients)}")
                if ingredients:
                    return ingredients
            
            # Si pas d'ingrédients trouvés, essayer de récupérer depuis les combos
            if hasattr(product, 'combo_line_ids') and product.combo_line_ids:
                ingredients = []
                for combo_line in product.combo_line_ids:
                    if combo_line.product_id and combo_line.product_id.is_distributeur_boisson:
                        ingredients.append({
                            'plu_no': combo_line.product_id.plu_code or f'PLU{combo_line.product_id.id}',
                            'name': combo_line.product_id.name,
                            'price': combo_line.product_id.list_price,
                            'quantity': combo_line.quantity or 1,
                            'credits': combo_line.product_id.credits_per_serving or 1,
                            'product_id': combo_line.product_id.id
                        })
                _logger.info(f"🍹 Ingrédients récupérés via combo_line_ids: {len(ingredients)}")
                if ingredients:
                    return ingredients
            
            # Si toujours pas d'ingrédients, essayer de récupérer depuis les produits liés
            if hasattr(product, 'product_template_id') and product.product_template_id:
                template = product.product_template_id
                if hasattr(template, 'combo_line_ids') and template.combo_line_ids:
                    ingredients = []
                    for combo_line in template.combo_line_ids:
                        if combo_line.product_id and combo_line.product_id.is_distributeur_boisson:
                            ingredients.append({
                                'plu_no': combo_line.product_id.plu_code or f'PLU{combo_line.product_id.id}',
                                'name': combo_line.product_id.name,
                                'price': combo_line.product_id.list_price,
                                'quantity': combo_line.quantity or 1,
                                'credits': combo_line.product_id.credits_per_serving or 1,
                                'product_id': combo_line.product_id.id
                            })
                    _logger.info(f"🍹 Ingrédients récupérés via template combo_line_ids: {len(ingredients)}")
                    if ingredients:
                        return ingredients
            
            # Si toujours pas d'ingrédients, essayer de récupérer depuis les attributs
            if hasattr(product, 'attribute_line_ids') and product.attribute_line_ids:
                ingredients = []
                for attr_line in product.attribute_line_ids:
                    if attr_line.product_id and attr_line.product_id.is_distributeur_boisson:
                        ingredients.append({
                            'plu_no': attr_line.product_id.plu_code or f'PLU{attr_line.product_id.id}',
                            'name': attr_line.product_id.name,
                            'price': attr_line.product_id.list_price,
                            'quantity': 1,
                            'credits': attr_line.product_id.credits_per_serving or 1,
                            'product_id': attr_line.product_id.id
                        })
                _logger.info(f"🍹 Ingrédients récupérés via attribute_line_ids: {len(ingredients)}")
                if ingredients:
                    return ingredients
            
            # Si toujours pas d'ingrédients, utiliser des ingrédients par défaut
            _logger.warning(f"🍹 Aucun ingrédient trouvé pour le cocktail {product.name}, utilisation d'ingrédients par défaut")
            return [
                {'plu_no': 'BASE001', 'name': 'Base par défaut', 'price': 0.0, 'quantity': 1, 'credits': 1, 'product_id': 0},
                {'plu_no': 'MIX001', 'name': 'Mélange par défaut', 'price': 0.0, 'quantity': 1, 'credits': 1, 'product_id': 0}
            ]
            
        except Exception as e:
            _logger.error(f"🍹 Erreur lors de la récupération des ingrédients: {str(e)}")
            # Retourner des ingrédients par défaut en cas d'erreur
            return [
                {'plu_no': 'BASE001', 'name': 'Base par défaut', 'price': 0.0, 'quantity': 1, 'credits': 1, 'product_id': 0},
                {'plu_no': 'MIX001', 'name': 'Mélange par défaut', 'price': 0.0, 'quantity': 1, 'credits': 1, 'product_id': 0}
            ]
    
    @api.model
    def distribuer_boisson(self, product_id, quantity=1, server_name=None):
        '''Distribue une boisson via le distributeur automatique'''
        # Sécurité Barman
        self._ensure_user_is_barman()
        try:
            product = self.env['product.product'].browse(product_id)
            if not product.exists():
                return {'success': False, 'message': 'Produit introuvable'}
            if not product.is_distributeur_boisson:
                return {'success': False, 'message': _(f'Le produit "{product.name}" n\'est pas une boisson du distributeur')}
            if not product.needs_distributor:
                return {'success': True, 'message': _(f'Boisson directe "{product.name}" - aucune action distributeur nécessaire'), 'direct_drink': True}
            is_cocktail = self._is_cocktail(product) or product.get('is_cocktail', False)
            if is_cocktail:
                return self._distribuer_cocktail(product, quantity, server_name)
            else:
                return self._distribuer_boisson_simple(product, quantity, server_name)
        except Exception as e:
            _logger.error(f"Erreur lors de la distribution: {str(e)}")
            return {'success': False, 'message': f'Erreur: {str(e)}'}

    def _distribuer_boisson_simple(self, product, quantity, server_name=None):
        '''Distribue une boisson simple'''
        self._ensure_user_is_barman()
        if not product.plu_code:
            return {'success': False, 'message': _(f'Le produit "{product.name}" n\'a pas de code PLU configuré')}
        server_no = self._get_current_server_no()
        credit_data = {
            'server_no': int(server_no),
            'plu_no': product.plu_code,
            'sign': '+',
            'quantity': quantity
        }
        _logger.info(f"Envoi crédit boisson simple: {product.name} (PLU: {product.plu_code}, Qty: {quantity}, Server: {server_no})")
        result = self._send_credit_to_middleware(credit_data)
        self._log_credit(product.name, product.plu_code, quantity, result.get('success'), result.get('message'), session=self, response=result)
        if result['success']:
            return {
                'success': True,
                'message': _(f'Boisson "{product.name}" commandée avec succès (Qty: {quantity})'),
                'product_name': product.name,
                'plu_no': product.plu_code,
                'quantity': quantity,
                'volume': product.volume_distributeur,
                'credits_per_serving': product.credits_per_serving,
                'server_name': server_name,
                'type': 'simple_drink',
                'middleware_response': result
            }
        else:
            return {
                'success': False,
                'message': _(f'Erreur lors de la commande de "{product.name}": {result["message"]}'),
                'error_details': result
            }

    def _distribuer_cocktail(self, product, quantity, server_name=None):
        '''Distribue un cocktail'''
        self._ensure_user_is_barman()
        _logger.info(f"🍹 Traitement du cocktail: {product.name}")
        ingredients_list = self._get_cocktail_ingredients(product)
        _logger.info(f"🍹 Ingrédients trouvés: {len(ingredients_list)}")
        if not ingredients_list:
            return {'success': False, 'message': _(f'Aucun ingrédient trouvé pour le cocktail "{product.name}"')}
        success_count = 0
        results = []
        server_no = self._get_current_server_no()
        _logger.info(f"🍹 Envoi des ingrédients (Server: {server_no})...")
        for i, ingredient_info in enumerate(ingredients_list):
            ingredient_plu = ingredient_info.get('plu_code') or ingredient_info.get('plu_no')
            credit_data = {
                'server_no': int(server_no),
                'plu_no': ingredient_plu,
                'sign': '+',
                'quantity': quantity
            }
            result = self._send_credit_to_middleware(credit_data)
            self._log_credit(f"{product.name} - {ingredient_info['name']}", ingredient_plu, quantity, result.get('success'), result.get('message'), session=self, response=result)
            results.append({
                'ingredient_plu': ingredient_plu,
                'ingredient_name': ingredient_info['name'],
                'success': result['success'],
                'message': result['message']
            })
            if result['success']:
                success_count += 1
        total_credits_expected = len(ingredients_list) * quantity
        _logger.info(f"🍹 Résumé: {success_count}/{total_credits_expected} ingrédients envoyés avec succès")
        cocktail_info = {
            'name': product.name,
            'type': 'cocktail',
            'ingredients_count': len(ingredients_list),
            'total_volume': sum(ing.get('volume', 0) for ing in ingredients_list),
            'price': product.list_price,
            'quantity': quantity
        }
        if success_count == total_credits_expected:
            return {
                'success': True,
                'message': _(f'Cocktail "{product.name}" distribué avec succès (Qty: {quantity}, Ingrédients: {len(ingredients_list)})'),
                'product_name': product.name,
                'quantity': quantity,
                'type': 'cocktail',
                'ingredients_list': ingredients_list,
                'total_credits_sent': success_count,
                'cocktail_info': cocktail_info,
                'details': results
            }
        elif success_count > 0:
            return {
                'success': False,
                'message': _(f'Distribution partielle du cocktail "{product.name}": {success_count}/{total_credits_expected} ingrédients envoyés'),
                'ingredients_list': ingredients_list,
                'cocktail_info': cocktail_info,
                'details': results
            }
        else:
            return {
                'success': False,
                'message': _(f'Échec complet de la distribution du cocktail "{product.name}"'),
                'ingredients_list': ingredients_list,
                'cocktail_info': cocktail_info,
                'details': results
            }
        


    @api.model
    def obtenir_boissons_disponibles(self):
        '''
        Retourne la liste des boissons disponibles nécessitant le distributeur
        
        Returns:
            list: Liste des boissons disponibles
        '''
        boissons = self._get_boissons_disponibles()
        
        result = []
        for code_plu, boisson in boissons.items():
            result.append({
                'code_plu': code_plu,
                'nom': boisson['nom'],
                'prix': boisson['prix'],
                'volume': boisson['volume'],
                'description': boisson['description'],
                'product_id': boisson['product_id'],
                'barcode': boisson['barcode'],
                'needs_distributor': boisson['needs_distributor'],
                'disponible': True
            })
        
        return result
    
    @api.model
    def obtenir_ingredients_cocktail(self, product_id):
        '''
        Retourne la liste détaillée des ingrédients d'un cocktail
        
        Args:
            product_id (int): ID du produit cocktail
            
        Returns:
            dict: Informations du cocktail et liste de ses ingrédients
        '''
        try:
            product = self.env['product.product'].browse(product_id)
            
            if not product.exists():
                return {
                    'success': False,
                    'message': 'Produit introuvable'
                }
            
            # Vérifier si c'est un cocktail
            if not self._is_cocktail(product):
                return {
                    'success': False,
                    'message': f'Le produit "{product.name}" n\'est pas un cocktail'
                }
            
            ingredients = self._get_cocktail_ingredients(product)
            
            if not ingredients:
                return {
                    'success': False,
                    'message': f'Aucun ingrédient trouvé pour le cocktail "{product.name}"'
                }
            
            # Préparer la liste des ingrédients pour l'affichage
            ingredients_list = []
            for ingredient_info in ingredients:
                ingredients_list.append({
                    'plu_no': ingredient_info['plu_code'],
                    'name': ingredient_info['name'],
                    'price': ingredient_info['price'],
                    'credits': ingredient_info['credits'],
                    'product_id': ingredient_info['product_id']
                })
            
            return {
                'success': True,
                'cocktail_name': product.name,
                'cocktail_price': product.list_price,
                'product_id': product.id,
                'ingredients_count': len(ingredients),
                'ingredients_list': ingredients_list,
                'message': f'Cocktail "{product.name}" contient {len(ingredients)} ingrédients'
            }
            
        except Exception as e:
            _logger.error(f"Erreur lors de la récupération des ingrédients: {str(e)}")
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }

    @api.model
    def verifier_statut_middleware(self):
        '''
        Vérifie le statut de connexion avec le middleware Hart96
        
        Returns:
            dict: Statut de la connexion
        '''
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'pos_distributeur.middleware_url', 
                'http://127.0.0.1:5000'  # Port par défaut du middleware Hart96
            )
            
            # Tenter de contacter le middleware Hart96
            response = requests.get(f"{base_url}/api/status", timeout=5)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get('connected'):
                        return {
                            'success': True,
                            'message': 'Middleware Hart96 connecté et disponible',
                            'url': base_url,
                            'connected': True,
                            'port': response_data.get('port'),
                            'baudrate': response_data.get('baudrate')
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Middleware Hart96 disponible mais non connecté au port série',
                            'url': base_url,
                            'connected': False
                        }
                except json.JSONDecodeError:
                    return {
                        'success': True,
                        'message': 'Middleware Hart96 disponible',
                        'url': base_url
                    }
            else:
                return {
                    'success': False,
                    'message': f'Middleware Hart96 indisponible: {response.status_code}',
                    'url': base_url
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Impossible de contacter le middleware Hart96: {str(e)}',
                'url': base_url
            }

    # Méthodes de compatibilité pour l'ancien système
    @api.model
    def distribuer_cocktail(self, product_id, quantity=1):
        '''
        Méthode de compatibilité - redirige vers distribuer_boisson
        '''
        return self.distribuer_boisson(product_id, quantity)

    @api.model
    def obtenir_produits_distributeur(self):
        '''
        Méthode de compatibilité - redirige vers obtenir_boissons_disponibles
        '''
        return self.obtenir_boissons_disponibles()
        
    @api.model
    def obtenir_cocktails_disponibles(self):
        '''
        Méthode de compatibilité - redirige vers obtenir_boissons_disponibles
        '''
        return self.obtenir_boissons_disponibles() 

    @api.model
    def envoyer_commande_distributeur(self, commande_data):
        '''
        Envoie une commande complète au distributeur en utilisant la nouvelle logique
        # Ajouter dans pos_session.py

        '''
        try:
            _logger.info(f"=== DÉBUT: Endpoint envoyer_commande_distributeur appelé ===")
            _logger.info(f"Arguments reçus: {commande_data}")
            _logger.info(f"Traitement de la commande {commande_data.get('order_id', 'N/A')} pour le distributeur")
            
            items = commande_data.get('items', [])
            if not items:
                return {
                    'success': True,
                    'message': 'Aucun item à traiter',
                    'items_processed': 0
                }
            
            results = []
            success_count = 0
            direct_count = 0
            error_count = 0
            
            # Traiter chaque item de la commande
            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 1)
                
                if not product_id:
                    results.append({
                        'item': item,
                        'success': False,
                        'message': 'ID produit manquant'
                    })
                    error_count += 1
                    continue
                
                # Vérifier si c'est un cocktail selon le flag envoyé par le frontend
                is_cocktail = item.get('is_cocktail', False)
                
                if is_cocktail:
                    _logger.info(f"🍹 Traitement d'un cocktail (ID: {product_id})")
                    # Pour les cocktails, on appelle directement _distribuer_cocktail
                    product = self.env['product.product'].browse(product_id)
                    if product.exists():
                        result = self._distribuer_cocktail(product, quantity)
                    else:
                        result = {
                            'success': False,
                            'message': f'Produit {product_id} introuvable'
                        }
                else:
                    # Distribuer la boisson normale
                    result = self.distribuer_boisson(product_id, quantity)
                results.append({
                    'item': item,
                    'success': result['success'],
                    'message': result['message'],
                    'details': result
                })
                
                if result['success']:
                    if result.get('direct_drink'):
                        direct_count += 1
                    else:
                        success_count += 1
                else:
                    error_count += 1
            
            total_items = len(items)
            
            # Préparer le message de résumé
            if error_count == 0:
                if success_count > 0 and direct_count > 0:
                    message = f"Commande traitée: {success_count} boisson(s) distribuée(s), {direct_count} boisson(s) directe(s)"
                elif success_count > 0:
                    message = f"Commande traitée: {success_count} boisson(s) distribuée(s) avec succès"
                elif direct_count > 0:
                    message = f"Commande traitée: {direct_count} boisson(s) directe(s) (aucune action distributeur)"
                else:
                    message = "Commande traitée: aucune boisson nécessitant le distributeur"
                
                return {
                    'success': True,
                    'message': message,
                    'items_processed': total_items,
                    'distributor_items': success_count,
                    'direct_items': direct_count,
                    'details': results
                }
            else:
                return {
                    'success': False,
                    'message': f"Erreurs lors du traitement: {error_count}/{total_items} items en échec",
                    'items_processed': total_items,
                    'distributor_items': success_count,
                    'direct_items': direct_count,
                    'error_items': error_count,
                    'details': results
                }
        except Exception as e:
            _logger.error(f"Erreur lors du traitement de la commande: {str(e)}")
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }

    @api.model
    def test_rpc_access(self):
        '''
        Méthode de test pour vérifier l'accès RPC
        '''
        _logger.info("=== TEST: Méthode test_rpc_access appelée ===")
        return {
            'success': True,
            'message': 'Méthode RPC accessible',
            'timestamp': str(datetime.now())
        }
    
    @api.model
    def cancel_simple_drink_credits(self, session_id, plu_no, quantity, product_name):
        """
        Annule les crédits d'une boisson simple
        Appelé depuis le JavaScript lors de la décrémentation
        """
        _logger.info(f"🔄 Annulation demandée: {product_name} (PLU: {plu_no}, Qty: {quantity})")
        
        try:
            # Vérifier droits Barman
            self._ensure_user_is_barman()
            
            # Chercher les crédits les plus récents pour ce PLU (non annulés)
            credits_to_cancel = self.env['pos.credit.log'].search([
                ('plu_no', '=', str(plu_no)),
                ('status', '=', 'sent'),
                ('session_id', '=', session_id)
            ], order='create_date desc', limit=int(quantity))
            
            if not credits_to_cancel:
                _logger.warning(f"⚠️ Aucun crédit actif trouvé pour PLU {plu_no}")
                return {
                    'success': False,
                    'message': f'Aucun crédit actif à annuler pour {product_name}'
                }
            
            # Annuler chaque crédit
            cancelled_count = 0
            for credit_log in credits_to_cancel:
                # Préparer les données d'annulation
                cancel_data = {
                    'server_no': credit_log.server_no,
                    'plu_no': credit_log.plu_no,
                    'sign': '-',
                    'quantity': 1
                }
                
                # Envoyer au middleware
                from .middleware_client import MiddlewareClient
                client = MiddlewareClient(self.env)
                result = client.send_credit(cancel_data, auto_connect=True)
                
                if result.get('success'):
                    # Mettre à jour le log
                    credit_log.write({
                        'status': 'cancelled',
                        'cancelled_at': fields.Datetime.now(),
                        'cancelled_by': self.env.user.id,
                        'cancellation_response': str(result.get('response', ''))
                    })
                    
                    # Créer log d'annulation
                    self.env['pos.credit.log'].sudo().create({
                        'user_id': self.env.user.id,
                        'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                        'session_id': session_id,
                        'product_name': f"🔄 ANNULATION - {product_name}",
                        'plu_no': credit_log.plu_no,
                        'quantity': 1,
                        'server_no': credit_log.server_no,
                        'success': True,
                        'status': 'cancelled',
                        'is_cancellation': True,
                        'message': 'Annulation suite à décrémentation POS',
                        'response_payload': str(result.get('response', ''))
                    })
                    
                    cancelled_count += 1
                    _logger.info(f"✅ Crédit #{credit_log.id} annulé")
            
            return {
                'success': True,
                'message': f'{cancelled_count} crédit(s) annulé(s) pour {product_name}',
                'cancelled_count': cancelled_count
            }
            
        except Exception as e:
            _logger.error(f"❌ Erreur annulation crédits: {str(e)}")
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }
    
    @api.model
    def cancel_cocktail_credits(self, session_id, product_id, quantity):
        """
        Annule les crédits d'un cocktail (tous les ingrédients)
        Appelé depuis le JavaScript lors de la décrémentation
        """
        _logger.info(f"🍹 Annulation cocktail demandée: Product ID {product_id}, Qty: {quantity}")
        
        try:
            # Vérifier droits Barman
            self._ensure_user_is_barman()
            
            # Récupérer le produit
            product = self.env['product.product'].browse(product_id)
            if not product.exists():
                return {
                    'success': False,
                    'message': f'Produit {product_id} introuvable'
                }
            
            # Récupérer les ingrédients
            ingredients = []
            if hasattr(product, 'selected_combo_ingredient_ids') and product.selected_combo_ingredient_ids:
                for ingredient_option in product.selected_combo_ingredient_ids:
                    if ingredient_option.product_id and ingredient_option.product_id.plu_code:
                        ingredients.append({
                            'plu_code': ingredient_option.product_id.plu_code,
                            'name': ingredient_option.product_id.name,
                        })
            
            if not ingredients:
                _logger.warning(f"⚠️ Aucun ingrédient trouvé pour le cocktail {product.name}")
                return {
                    'success': False,
                    'message': f'Aucun ingrédient à annuler pour {product.name}'
                }
            
            # Annuler les crédits de chaque ingrédient
            total_cancelled = 0
            for ingredient in ingredients:
                result = self.cancel_simple_drink_credits(
                    session_id,
                    ingredient['plu_code'],
                    quantity,
                    f"{product.name} - {ingredient['name']}"
                )
                if result.get('success'):
                    total_cancelled += result.get('cancelled_count', 0)
            
            return {
                'success': True,
                'message': f'{total_cancelled} crédit(s) d\'ingrédients annulés pour {product.name}',
                'cancelled_count': total_cancelled
            }
            
        except Exception as e:
            _logger.error(f"❌ Erreur annulation cocktail: {str(e)}")
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }

    @api.model
    def send_credit_to_middleware(self, credit_data):
        """Proxy RPC avec contrôle Barmans, server_no employé et journalisation"""
        self._ensure_user_is_barman()
        _logger.info(f"📤 RPC: Envoi crédit au middleware Hart96")
        _logger.info(f"📤 Données reçues: {credit_data}")
        # Forcer server_no depuis employé
        credit_data = dict(credit_data or {})
        credit_data['server_no'] = self._get_current_server_no()
        client = MiddlewareClient(self.env)
        result = client.send_credit(credit_data)
        self._log_credit(product_name=credit_data.get('product_name') or '', plu_no=credit_data.get('plu_no'), quantity=credit_data.get('quantity', 1), success=result.get('success'), message=result.get('message'), session=self, response=result)
        if result['success']:
            return {'success': True, 'message': result['message'], 'middleware_response': result.get('response', {})}
        else:
            return {'success': False, 'error': result['message'], 'middleware_response': result.get('response', {})}

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        params['search_params']['fields'].extend([
            'is_distributeur_boisson',
            'needs_distributor',
            'plu_code',
            'volume_distributeur',
            'detailed_type',
            'combo_ids',
            'credits_per_serving',
            'is_combo_product',
            'combo_line_ids'
        ])
        return params

    def _get_combo_data(self):
        '''
        Retourne les données de combo nécessaires pour le POS
        '''
        combo_data = {
            'categories': [],
            'options': [],
            'combo_lines': []
        }
        
        # Charger les catégories de combo
        categories = self.env['pos.combo.category'].search([('active', '=', True)])
        for category in categories:
            combo_data['categories'].append({
                'id': category.id,
                'name': category.name,
                'description': category.description or '',
                'sequence': category.sequence
            })
        
        # Charger les options de combo
        options = self.env['pos.combo.option'].search([('active', '=', True)])
        for option in options:
            combo_data['options'].append({
                'id': option.id,
                'name': option.name,
                'combo_category_id': [option.combo_category_id.id, option.combo_category_id.name],
                'product_id': [option.product_id.id, option.product_id.name],
                'price_extra': option.price_extra,
                'sequence': option.sequence,
                'description': option.description or ''
            })
        
        # Charger les lignes de combo pour les produits
        combo_lines = self.env['product.combo.line'].search([])
        for line in combo_lines:
            combo_data['combo_lines'].append({
                'id': line.id,
                'product_tmpl_id': [line.product_tmpl_id.id, line.product_tmpl_id.name],
                'combo_category_id': [line.combo_category_id.id, line.combo_category_id.name],
                'sequence': line.sequence,
                'required': line.required,
                'min_selections': line.min_selections,
                'max_selections': line.max_selections
            })
        
        return combo_data

    def _loader_params_pos_combo_category(self):
        '''
        Paramètres de chargement pour les catégories de combo
        '''
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name', 'description', 'sequence']
            }
        }

    def _loader_params_pos_combo_option(self):
        '''
        Paramètres de chargement pour les options de combo
        '''
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name', 'combo_category_id', 'product_id', 'price_extra', 'sequence', 'description']
            }
        }

    def _loader_params_product_combo_line(self):
        '''
        Paramètres de chargement pour les lignes de combo
        '''
        return {
            'search_params': {
                'domain': [],
                'fields': ['product_tmpl_id', 'combo_category_id', 'sequence', 'required', 'min_selections', 'max_selections']
            }
        }