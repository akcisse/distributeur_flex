# -*- coding: utf-8 -*-
"""
Script de migration pour ajouter les nouveaux champs au modèle pos.credit.log
Ce script doit être exécuté après la mise à jour du module
"""

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


def migrate_pos_credit_log(env):
    """
    Migre les données existantes de pos.credit.log
    Ajoute les valeurs par défaut pour les nouveaux champs
    """
    _logger.info("🔄 Début migration pos.credit.log...")
    
    try:
        # Récupérer tous les logs existants sans statut
        existing_logs = env['pos.credit.log'].search([
            ('status', '=', False)
        ])
        
        if existing_logs:
            _logger.info(f"📊 {len(existing_logs)} enregistrements à migrer")
            
            # Mettre à jour avec valeurs par défaut
            existing_logs.write({
                'status': 'sent',  # Tous les anciens logs = envoyés
                'is_cancellation': False
            })
            
            _logger.info(f"✅ {len(existing_logs)} enregistrements migrés avec succès")
        else:
            _logger.info("✅ Aucune migration nécessaire (tous les logs ont déjà un statut)")
        
        return True
        
    except Exception as e:
        _logger.error(f"❌ Erreur lors de la migration: {str(e)}", exc_info=True)
        return False


class PosCreditLogMigration(models.AbstractModel):
    """
    Modèle abstrait pour gérer la migration
    """
    _name = 'pos.credit.log.migration'
    _description = 'Migration helper for pos.credit.log'
    
    @api.model
    def run_migration(self):
        """
        Méthode appelable depuis l'interface pour lancer la migration
        """
        result = migrate_pos_credit_log(self.env)
        
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migration Réussie',
                    'message': 'Les données ont été migrées avec succès',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur de Migration',
                    'message': 'Une erreur est survenue lors de la migration',
                    'type': 'danger',
                    'sticky': True,
                }
            }



