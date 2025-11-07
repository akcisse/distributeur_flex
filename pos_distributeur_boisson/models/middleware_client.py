# -*- coding: utf-8 -*-

import requests
import json
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class MiddlewareClient:
    """
    Client centralisé pour la communication avec le middleware Hart96
    Évite la duplication de code entre les différents modules
    """
    
    def __init__(self, env):
        self.env = env
        self._middleware_url = None
        self._server_no = None
    
    def _get_middleware_url(self):
        """Récupère l'URL du middleware depuis la configuration Odoo"""
        if not self._middleware_url:
            self._middleware_url = self.env['ir.config_parameter'].sudo().get_param(
                'pos_distributeur.middleware_url', 
                'http://192.168.1.59:5000'
            )
            
            # S'assurer que l'URL a un port
            if not self._middleware_url.endswith(':5000') and not self._middleware_url.endswith(':80'):
                if 'http://192.168.1.59' in self._middleware_url:
                    self._middleware_url = 'http://192.168.1.59:5000'
        
        return self._middleware_url
    
    def _get_server_no(self):
        """Récupère le numéro de serveur depuis la configuration Odoo"""
        if not self._server_no:
            self._server_no = self.env['ir.config_parameter'].sudo().get_param(
                'pos_distributeur.server_no', 
                '1'
            )
        return self._server_no
    
    def _prepare_hart96_data(self, credit_data):
        """
        Prépare les données au format attendu par le middleware Hart96
        
        Args:
            credit_data (dict): Données avec server_no, plu_no, sign, quantity
        
        Returns:
            dict: Données formatées pour Hart96
        """
        plu_no = credit_data.get('plu_no', '1')
        
        # Convertir PLU001 en 1 si nécessaire
        if isinstance(plu_no, str) and plu_no.startswith('PLU'):
            plu_no = plu_no.replace('PLU', '')
        
        return {
            'server_no': int(credit_data.get('server_no', self._get_server_no())),
            'plu_no': int(plu_no),
            'sign': credit_data.get('sign', '+'),
            'quantity': int(credit_data.get('quantity', 1))
        }
    
    def connect_middleware(self):
        """
        Ouvre la connexion au middleware Hart96
        
        Returns:
            dict: Résultat de la connexion
        """
        try:
            middleware_url = self._get_middleware_url()
            url_connect = f"{middleware_url}/api/connect"
            
            connect_data = {
                "port": "COM1",
                "baudrate": 9600
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url_connect, json=connect_data, headers=headers, timeout=10)
            
            _logger.info(f"🔌 Connexion middleware: {response.status_code} - {response.text}")
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response': response.text
            }
            
        except Exception as e:
            _logger.error(f"🔌 Erreur connexion middleware: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def disconnect_middleware(self):
        """
        Ferme la connexion au middleware Hart96
        
        Returns:
            dict: Résultat de la déconnexion
        """
        try:
            middleware_url = self._get_middleware_url()
            url_disconnect = f"{middleware_url}/api/disconnect"
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url_disconnect, json={}, headers=headers, timeout=10)
            
            _logger.info(f"🔌 Déconnexion middleware: {response.status_code} - {response.text}")
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response': response.text
            }
            
        except Exception as e:
            _logger.error(f"🔌 Erreur déconnexion middleware: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_credit(self, credit_data, auto_connect=True):
        """
        Envoie un crédit au middleware Hart96
        
        Args:
            credit_data (dict): Données du crédit
            auto_connect (bool): Si True, gère automatiquement la connexion/déconnexion
        
        Returns:
            dict: Résultat de l'envoi
        """
        try:
            middleware_url = self._get_middleware_url()
            api_url = f"{middleware_url}/api/send-credit"
            
            # Préparer les données au format Hart96
            hart96_data = self._prepare_hart96_data(credit_data)
            
            _logger.info(f"📤 Envoi crédit vers middleware Hart96: {api_url}")
            _logger.info(f"📤 Données originales: {json.dumps(credit_data, indent=2)}")
            _logger.info(f"📤 Données Hart96 formatées: {json.dumps(hart96_data, indent=2)}")
            
            # Connexion automatique si demandée
            if auto_connect:
                connect_result = self.connect_middleware()
                if not connect_result['success']:
                    _logger.warning(f"⚠️ Échec connexion middleware: {connect_result.get('error', 'Erreur inconnue')}")
            
            # Envoyer la requête
            headers = {'Content-Type': 'application/json'}
            response = requests.post(api_url, json=hart96_data, headers=headers, timeout=10)
            
            _logger.info(f"📥 Réponse middleware: {response.status_code} - {response.text}")
            
            # Déconnexion automatique si demandée
            if auto_connect:
                disconnect_result = self.disconnect_middleware()
                if not disconnect_result['success']:
                    _logger.warning(f"⚠️ Échec déconnexion middleware: {disconnect_result.get('error', 'Erreur inconnue')}")
            
            # Traitement de la réponse
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get('success'):
                        return {
                            'success': True,
                            'message': response_data.get('message', 'Crédit envoyé avec succès'),
                            'response': response_data
                        }
                    else:
                        return {
                            'success': False,
                            'message': response_data.get('error', 'Erreur lors de l\'envoi du crédit'),
                            'response': response_data
                        }
                except json.JSONDecodeError:
                    # Traiter comme texte simple
                    response_text = response.text.strip()
                    if response_text == 'OK':
                        return {
                            'success': True,
                            'message': 'Crédit envoyé avec succès',
                            'response': response_text
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'Réponse inattendue: {response_text}',
                            'response': response_text
                        }
            else:
                return {
                    'success': False,
                    'message': f'Erreur HTTP {response.status_code}: {response.text}',
                    'response': response.text
                }
                
        except requests.exceptions.ConnectionError:
            _logger.error("❌ Erreur de connexion au middleware Hart96")
            return {
                'success': False,
                'message': 'Impossible de se connecter au middleware Hart96. Vérifiez qu\'il est démarré et accessible.'
            }
        except requests.exceptions.Timeout:
            _logger.error("❌ Timeout lors de la connexion au middleware Hart96")
            return {
                'success': False,
                'message': 'Timeout lors de la connexion au middleware Hart96'
            }
        except Exception as e:
            _logger.error(f"❌ Erreur inattendue: {str(e)}")
            return {
                'success': False,
                'message': f'Erreur inattendue: {str(e)}'
            }
    
    def send_multiple_credits(self, credits_list):
        """
        Envoie plusieurs crédits au middleware Hart96
        Gère une seule connexion/déconnexion pour tous les crédits
        
        Args:
            credits_list (list): Liste des données de crédits
        
        Returns:
            dict: Résultat global avec détails de chaque crédit
        """
        if not credits_list:
            return {
                'success': False,
                'message': 'Aucun crédit à envoyer'
            }
        
        # Connexion unique
        connect_result = self.connect_middleware()
        if not connect_result['success']:
            return {
                'success': False,
                'message': f'Impossible de se connecter au middleware: {connect_result.get("error", "Erreur inconnue")}'
            }
        
        results = []
        success_count = 0
        
        try:
            # Envoyer tous les crédits
            for i, credit_data in enumerate(credits_list):
                _logger.info(f"📤 Envoi crédit {i+1}/{len(credits_list)}")
                
                result = self.send_credit(credit_data, auto_connect=False)  # Pas de connexion automatique
                results.append(result)
                
                if result['success']:
                    success_count += 1
                    _logger.info(f"✅ Crédit {i+1} envoyé avec succès")
                else:
                    _logger.error(f"❌ Échec crédit {i+1}: {result['message']}")
        
        finally:
            # Déconnexion unique
            disconnect_result = self.disconnect_middleware()
            if not disconnect_result['success']:
                _logger.warning(f"⚠️ Échec déconnexion: {disconnect_result.get('error', 'Erreur inconnue')}")
        
        return {
            'success': success_count == len(credits_list),
            'message': f'{success_count}/{len(credits_list)} crédits envoyés avec succès',
            'total_credits': len(credits_list),
            'success_count': success_count,
            'results': results
        }
    
    def test_connection(self):
        """
        Test la connexion au middleware Hart96
        
        Returns:
            dict: Résultat du test
        """
        try:
            middleware_url = self._get_middleware_url()
            test_url = f"{middleware_url}/api/status"
            
            response = requests.get(test_url, timeout=5)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    return {
                        'success': True,
                        'message': 'Connexion au middleware réussie',
                        'middleware_url': middleware_url,
                        'status': response_data
                    }
                except json.JSONDecodeError:
                    return {
                        'success': True,
                        'message': 'Connexion au middleware réussie (réponse non-JSON)',
                        'middleware_url': middleware_url,
                        'response_text': response.text
                    }
            else:
                return {
                    'success': False,
                    'message': f'Erreur HTTP {response.status_code}',
                    'middleware_url': middleware_url
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': f'Impossible de se connecter au middleware sur {middleware_url}',
                'middleware_url': middleware_url
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur: {str(e)}',
                'middleware_url': middleware_url
            } 