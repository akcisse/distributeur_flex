# -*- coding: utf-8 -*-

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    Migration pour corriger les permissions de la table de relation Many2many
    """
    try:
        # Corriger les permissions pour la table de relation Many2many
        cr.execute("""
            GRANT ALL PRIVILEGES ON TABLE pos_combo_option_product_template_rel TO odoo;
        """)
        _logger.info("Permissions corrigées pour pos_combo_option_product_template_rel")
    except Exception as e:
        _logger.error("Erreur lors de la correction des permissions: %s", str(e))
        # Ne pas faire échouer l'installation si la correction échoue
        pass 

def migrate(cr, version):
    """
    Migration script pour supprimer l'ancienne contrainte SQL
    """
    try:
        # Supprimer l'ancienne contrainte SQL si elle existe
        cr.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'pos_combo_option_product_category_uniq'
                    AND table_name = 'pos_combo_option'
                ) THEN
                    ALTER TABLE pos_combo_option DROP CONSTRAINT pos_combo_option_product_category_uniq;
                END IF;
            END $$;
        """)
        _logger.info("Ancienne contrainte SQL supprimée avec succès")
    except Exception as e:
        _logger.error("Erreur lors de la suppression de l'ancienne contrainte: %s", str(e))
        # Ne pas faire échouer la migration si la contrainte n'existe pas
        pass 