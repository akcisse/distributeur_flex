# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    combo_options = fields.Text(
        string="Options de Combo",
        help="Options de combo sélectionnées au format JSON"
    )
    price_extra = fields.Float(
        string="Prix Additionnel",
        default=0.0,
        help="Prix additionnel pour les options de combo"
    )
    
    # ✨ NOUVEAUX CHAMPS pour tracking des crédits
    # Note: Le champ credit_ids sera ajouté dynamiquement après chargement des modules
    
    def _get_active_credits(self):
        """
        Récupère les crédits actifs pour cette ligne
        Méthode helper pour éviter le problème de dépendance circulaire
        """
        self.ensure_one()
        if not self.env['ir.model'].search([('model', '=', 'pos.credit.log')]):
            return self.env['pos.credit.log']
        
        return self.env['pos.credit.log'].search([
            ('order_line_id', '=', self.id),
            ('status', '=', 'sent'),
        ])

    def set_combo_options(self, options):
        """
        Définit les options de combo pour cette ligne
        """
        if options:
            self.combo_options = json.dumps(options)
        else:
            self.combo_options = False

    def get_combo_options(self):
        """
        Récupère les options de combo pour cette ligne
        """
        if self.combo_options:
            try:
                return json.loads(self.combo_options)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_price_extra(self, price_extra):
        """
        Définit le prix additionnel pour cette ligne
        """
        self.price_extra = price_extra or 0.0

    @api.depends('price_unit', 'price_extra')
    def _compute_price_subtotal_incl(self):
        """
        Recalcule le sous-total en incluant le prix additionnel
        """
        for line in self:
            base_price = line.price_unit
            extra_price = line.price_extra or 0.0
            line.price_subtotal_incl = (base_price + extra_price) * line.qty

    def _get_combo_options_text(self):
        """
        Retourne le texte formaté des options de combo
        """
        options = self.get_combo_options()
        if not options:
            return ""
        
        texts = []
        for option in options:
            category_name = option.get('category_name', '')
            name = option.get('name', '')
            if category_name and name:
                texts.append(f"{category_name}: {name}")
        
        return " | ".join(texts)

    def get_combo_summary(self):
        """
        Retourne un résumé des options de combo pour l'affichage
        """
        options = self.get_combo_options()
        if not options:
            return {
                'has_options': False,
                'text': '',
                'total_extra': 0.0
            }
        
        total_extra = sum(option.get('price_extra', 0.0) for option in options)
        text = self._get_combo_options_text()
        
        return {
            'has_options': True,
            'text': text,
            'total_extra': total_extra,
            'options_count': len(options)
        }
    
    # ============================================
    # 🔄 SYSTÈME D'ANNULATION AUTOMATIQUE
    # ============================================
    
    def unlink(self):
        """
        Surcharge de la suppression pour gérer l'annulation automatique des crédits
        """
        _logger.info("🗑️ Suppression de ligne(s) de commande POS détectée")
        
        # Parcourir toutes les lignes à supprimer
        for line in self:
            # Vérifier si le produit nécessite le distributeur
            if line.product_id and hasattr(line.product_id, 'needs_distributor') and line.product_id.needs_distributor:
                _logger.info(f"🔍 Ligne #{line.id}: {line.product_id.name} - Vérification crédits...")
                
                # Chercher les crédits actifs en utilisant la méthode helper
                try:
                    active_credits = line._get_active_credits()
                except Exception as e:
                    _logger.warning(f"⚠️ Impossible de récupérer les crédits: {str(e)}")
                    active_credits = self.env['pos.credit.log']
                
                if active_credits:
                    _logger.info(f"⚠️ {len(active_credits)} crédit(s) actif(s) trouvé(s) - Tentative d'annulation...")
                    
                    # Annuler chaque crédit
                    cancelled_count = 0
                    for credit_log in active_credits:
                        if self._cancel_credit_in_flex(credit_log):
                            cancelled_count += 1
                    
                    _logger.info(f"✅ {cancelled_count}/{len(active_credits)} crédit(s) annulé(s) avec succès")
                else:
                    _logger.info(f"✅ Aucun crédit actif, suppression simple")
        
        # Appeler la méthode parent pour suppression normale
        return super(PosOrderLine, self).unlink()
    
    def write(self, vals):
        """
        Surcharge de l'écriture pour gérer la modification de quantité
        """
        # Vérifier si la quantité change
        if 'qty' in vals:
            for line in self:
                old_qty = line.qty
                new_qty = vals['qty']
                
                # Si quantité réduite et produit nécessite distributeur
                if new_qty < old_qty and line.product_id and hasattr(line.product_id, 'needs_distributor') and line.product_id.needs_distributor:
                    qty_diff = int(old_qty - new_qty)
                    _logger.info(f"📉 Réduction quantité détectée: {old_qty} → {new_qty} (diff: {qty_diff})")
                    
                    # Annuler les crédits correspondants à la réduction
                    self._cancel_quantity_credits(line, qty_diff)
        
        return super(PosOrderLine, self).write(vals)
    
    def _cancel_credit_in_flex(self, credit_log):
        """
        Annule un crédit spécifique dans le Flex/Hart96
        
        Args:
            credit_log: Enregistrement pos.credit.log à annuler
            
        Returns:
            bool: True si annulation réussie, False sinon
        """
        try:
            _logger.info(f"🔄 Annulation crédit #{credit_log.id}: {credit_log.product_name} (PLU: {credit_log.plu_no})")
            
            # Vérifier les droits Barman
            if not self.env.user.has_group('pos_user_org.group_pos_barman'):
                _logger.warning("⚠️ Utilisateur non-Barman tente d'annuler un crédit")
                return False
            
            # Préparer la commande d'annulation avec SIGNE MOINS
            cancel_data = {
                'server_no': credit_log.server_no,
                'plu_no': credit_log.plu_no,
                'sign': '-',  # ❗ SIGNE MOINS = ANNULATION
                'quantity': credit_log.quantity
            }
            
            _logger.info(f"📤 Envoi annulation au middleware: {cancel_data}")
            
            # Envoyer au middleware via MiddlewareClient
            try:
                from ..models.middleware_client import MiddlewareClient
                client = MiddlewareClient(self.env)
                result = client.send_credit(cancel_data, auto_connect=True)
            except ImportError:
                _logger.error("❌ Impossible d'importer MiddlewareClient")
                return False
            
            if result.get('success'):
                # Mettre à jour le statut du log original
                credit_log.write({
                    'status': 'cancelled',
                    'cancelled_at': fields.Datetime.now(),
                    'cancelled_by': self.env.user.id,
                    'cancellation_response': str(result.get('response', ''))
                })
                
                _logger.info(f"✅ Crédit #{credit_log.id} annulé avec succès")
                
                # Créer un nouveau log pour l'annulation (traçabilité complète)
                self.env['pos.credit.log'].sudo().create({
                    'user_id': self.env.user.id,
                    'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                    'session_id': credit_log.session_id.id if credit_log.session_id else False,
                    'order_line_id': credit_log.order_line_id.id if credit_log.order_line_id else False,
                    'product_name': f"🔄 ANNULATION - {credit_log.product_name}",
                    'plu_no': credit_log.plu_no,
                    'quantity': credit_log.quantity,
                    'server_no': credit_log.server_no,
                    'success': True,
                    'status': 'cancelled',
                    'is_cancellation': True,
                    'message': 'Annulation automatique suite à suppression de ligne',
                    'response_payload': str(result.get('response', '')),
                    'credit_id': credit_log.credit_id
                })
                
                return True
            else:
                _logger.error(f"❌ Échec annulation crédit #{credit_log.id}: {result.get('message', 'Erreur inconnue')}")
                
                # Logger l'échec
                credit_log.write({
                    'message': f"Échec annulation: {result.get('message', 'Erreur inconnue')}"
                })
                
                return False
                
        except Exception as e:
            _logger.error(f"❌ Erreur lors de l'annulation du crédit: {str(e)}", exc_info=True)
            return False
    
    def _cancel_quantity_credits(self, line, qty_to_cancel):
        """
        Annule les crédits correspondant à une réduction de quantité
        
        Args:
            line: Ligne de commande concernée
            qty_to_cancel: Nombre d'unités à annuler
        """
        if qty_to_cancel <= 0:
            return
        
        # Récupérer les crédits actifs pour cette ligne (les plus récents en premier)
        try:
            all_active_credits = self.env['pos.credit.log'].search([
                ('order_line_id', '=', line.id),
                ('status', '=', 'sent'),
            ], order='create_date desc')
            
            # Limiter au nombre à annuler
            active_credits = all_active_credits[:int(qty_to_cancel)] if all_active_credits else self.env['pos.credit.log']
        except Exception as e:
            _logger.error(f"❌ Erreur récupération crédits pour annulation quantité: {str(e)}")
            return
        
        if not active_credits:
            _logger.warning(f"⚠️ Aucun crédit actif trouvé pour annulation de quantité")
            return
        
        _logger.info(f"🔄 Annulation de {len(active_credits)} crédit(s) pour réduction de quantité")
        
        cancelled_count = 0
        for credit_log in active_credits:
            if self._cancel_credit_in_flex(credit_log):
                cancelled_count += 1
        
        _logger.info(f"✅ {cancelled_count}/{len(active_credits)} crédit(s) annulé(s) avec succès")
    
    def action_cancel_credits(self):
        """
        Action manuelle pour annuler tous les crédits actifs d'une ligne
        (peut être appelée depuis l'interface si besoin)
        """
        self.ensure_one()
        
        try:
            active_credits = self._get_active_credits()
        except Exception as e:
            raise UserError(_("Erreur lors de la récupération des crédits: %s") % str(e))
        
        if not active_credits:
            raise UserError(_("Aucun crédit actif à annuler pour cette ligne."))
        
        cancelled_count = 0
        for credit_log in active_credits:
            if self._cancel_credit_in_flex(credit_log):
                cancelled_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Annulation de crédits'),
                'message': _('%d crédit(s) annulé(s) sur %d') % (cancelled_count, len(active_credits)),
                'type': 'success' if cancelled_count == len(active_credits) else 'warning',
                'sticky': False,
            }
        } 