# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import requests
import json
import logging
from datetime import datetime
from ..models.middleware_client import MiddlewareClient

_logger = logging.getLogger(__name__)

class PosDistributeurController(http.Controller):
    
    @http.route('/pos_distributeur_boisson/test', type='json', auth='user')
    def test_endpoint(self, **kwargs):
        """
        Endpoint de test simple pour vérifier que le contrôleur fonctionne
        """
        _logger.info("🧪 Test endpoint appelé")
        return {
            'success': True,
            'message': 'Contrôleur POS Distributeur fonctionnel',
            'timestamp': str(datetime.now())
        }
    
    @http.route('/pos_distributeur_boisson/is_barman', type='json', auth='user')
    def is_barman(self, **kwargs):
        """Retourne si l’utilisateur courant appartient au groupe Barmans"""
        is_barman = request.env.user.has_group('pos_user_org.group_pos_barman')
        return {'success': True, 'is_barman': bool(is_barman)}
    
    @http.route('/pos_distributeur_boisson/send_credit_to_middleware', type='json', auth='user')
    def send_credit_to_middleware(self, **kwargs):
        """
        Proxy pour envoyer des crédits au middleware Hart96
        Utilise la classe MiddlewareClient centralisée
        """
        _logger.info(f"📤 Direct: Envoi crédit au middleware Hart96")
        _logger.info(f"📤 Données reçues: {kwargs}")
        
        # Vérifier droits Barman
        if not request.env.user.has_group('pos_user_org.group_pos_barman'):
            return {'success': False, 'error': "Accès refusé: réservé aux Barmans"}
        
        # Utiliser la classe MiddlewareClient centralisée
        client = MiddlewareClient(request.env)
        result = client.send_credit(kwargs)
        
        # Adapter le format de réponse pour compatibilité
        if result['success']:
            return {
                'success': True,
                'message': result['message'],
                'middleware_response': result.get('response', {})
            }
        else:
            return {
                'success': False,
                'error': result['message'],
                'middleware_response': result.get('response', {})
            }
    

    @http.route('/pos_distributeur_boisson/send_cocktail_ingredients', type='json', auth='user')
    def send_cocktail_ingredients(self, **kwargs):
        """
        Envoie les crédits des ingrédients d'un cocktail au middleware Hart96
        Récupère les ingrédients du cocktail et envoie un crédit pour chacun
        
        Args:
            product_id (int): ID du produit cocktail
            quantity (int): Quantité du cocktail à préparer
            server_name (str): Nom du serveur (optionnel)
        """
        try:
            _logger.info(f"🍹 Envoi des ingrédients du cocktail au middleware Hart96")
            _logger.info(f"🍹 Données reçues: {kwargs}")
            
            if not request.env.user.has_group('pos_user_org.group_pos_barman'):
                return {'success': False, 'error': "Accès refusé: réservé aux Barmans"}
            
            product_id = kwargs.get('product_id')
            quantity = kwargs.get('quantity', 1)
            server_name = kwargs.get('server_name', 'Serveur')
            
            if not product_id:
                return {
                    'success': False,
                    'error': 'ID du produit cocktail manquant'
                }
            
            # Récupérer le produit cocktail
            product = request.env['product.product'].browse(product_id)
            if not product.exists():
                return {
                    'success': False,
                    'error': f'Produit cocktail {product_id} introuvable'
                }
            
            # Vérifier si c'est un cocktail
            if not product.is_combo_product:
                return {
                    'success': False,
                    'error': f'Le produit "{product.name}" n\'est pas un cocktail'
                }
            
            # Récupérer les ingrédients du cocktail
            ingredients_list = []
            
            # Utiliser les ingrédients sélectionnés si disponibles
            if hasattr(product, 'selected_combo_ingredient_ids') and product.selected_combo_ingredient_ids:
                for ingredient_option in product.selected_combo_ingredient_ids:
                    if ingredient_option.product_id and ingredient_option.product_id.plu_code:
                        ingredients_list.append({
                            'plu_code': ingredient_option.product_id.plu_code,
                            'name': ingredient_option.product_id.name,
                            'credits': ingredient_option.credits_per_serving or 1,
                            'product_id': ingredient_option.product_id.id,
                            'category_name': ingredient_option.combo_category_id.name if ingredient_option.combo_category_id else '',
                            'price_extra': ingredient_option.price_extra
                        })
            
            # Si pas d'ingrédients sélectionnés, utiliser la méthode get_cocktail_ingredients
            if not ingredients_list and hasattr(product, 'get_cocktail_ingredients'):
                ingredients_list = product.get_cocktail_ingredients()
            
            if not ingredients_list:
                return {
                    'success': False,
                    'error': f'Aucun ingrédient trouvé pour le cocktail "{product.name}"'
                }
            
            _logger.info(f"🍹 Ingrédients trouvés: {len(ingredients_list)}")
            
            # Préparer la liste des crédits à envoyer pour chaque ingrédient
            credits_list = []
            for ingredient_info in ingredients_list:
                ingredient_plu = ingredient_info.get('plu_code')
                credit_data = {
                    'plu_no': ingredient_plu,
                    'sign': '+',
                    'quantity': quantity
                }
                credits_list.append(credit_data)
            
            # Utiliser MiddlewareClient pour envoyer tous les crédits
            client = MiddlewareClient(request.env)
            middleware_result = client.send_multiple_credits(credits_list)
            
            # Préparer les détails pour chaque ingrédient
            results = []
            for i, (ingredient_info, credit_result) in enumerate(zip(ingredients_list, middleware_result['results'])):
                ingredient_name = ingredient_info.get('name', f'Ingrédient {i+1}')
                ingredient_plu = ingredient_info.get('plu_code')
                
                results.append({
                    'ingredient_name': ingredient_name,
                    'plu_code': ingredient_plu,
                    'success': credit_result['success'],
                    'message': credit_result['message']
                })
            
            # Préparer le résultat final
            total_ingredients = len(ingredients_list)
            success_count = middleware_result['success_count']
            cocktail_info = {
                'name': product.name,
                'type': 'cocktail',
                'ingredients_count': total_ingredients,
                'price': product.list_price,
                'quantity': quantity
            }
            
            # Retourner le résultat basé sur le succès global
            return {
                'success': middleware_result['success'],
                'message': f'Cocktail "{product.name}": {middleware_result["message"]} (Qty: {quantity})',
                'product_name': product.name,
                'quantity': quantity,
                'type': 'cocktail',
                'ingredients_list': ingredients_list,
                'total_credits_sent': success_count,
                'cocktail_info': cocktail_info,
                'details': results
            }
                
        except Exception as e:
            _logger.error(f"❌ Erreur inattendue lors de l'envoi des ingrédients du cocktail: {str(e)}")
            return {
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }
    
   
    def test_middleware_connection(self, **kwargs):
        """
        Test de connexion au middleware pour vérifier la configuration
        Utilise MiddlewareClient centralisé
        """
        _logger.info("🔍 Test de connexion au middleware")
        
        client = MiddlewareClient(request.env)
        return client.test_connection()
    
    @http.route('/pos_distributeur_boisson/test_connection_logs', type='json', auth='user')
    def test_connection_logs(self, **kwargs):
        """
        Test spécifique pour les logs de connexion et déconnexion
        Utilise MiddlewareClient centralisé
        """
        _logger.info("🔌 Test des logs de connexion/déconnexion")
        
        client = MiddlewareClient(request.env)
        
        # Test de connexion
        connect_result = client.connect_middleware()
        connect_status = "✅ Connexion réussie" if connect_result['success'] else f"❌ Échec connexion: {connect_result.get('error', 'Erreur inconnue')}"
        
        # Test de déconnexion
        disconnect_result = client.disconnect_middleware()
        disconnect_status = "✅ Déconnexion réussie" if disconnect_result['success'] else f"❌ Échec déconnexion: {disconnect_result.get('error', 'Erreur inconnue')}"
        
        return {
            'success': True,
            'message': 'Test des logs de connexion/déconnexion terminé',
            'middleware_url': client._get_middleware_url(),
            'connection_test': connect_status,
            'disconnection_test': disconnect_status,
            'logs': {
                'connection': connect_status,
                'disconnection': disconnect_status
            }
        }
    
    