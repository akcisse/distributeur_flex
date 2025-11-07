{
    'name': 'POS Distributeur de Boisson',
    'version': '1.1.1',
    'category': 'Point of Sale',
    'summary': 'Module simple d\'intégration distributeur de boissons dans le POS',
    'description': """
        Ce module ajoute un bouton distributeur dans le POS pour commander des boissons.
    """,
    'author': 'Odoo Community',
    'website': 'https://www.odoo.com',
    'depends': ['point_of_sale', 'pos_user_org'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        
        'views/product_combo_views.xml',
        'views/product_views_simple.xml',
        'views/ingredient_selection_wizard_views.xml',
        
        'data/demo_products.xml',
        'data/combo_test_data.xml',
        'data/pos_actions.xml',
    ],
    'assets': {
        'point_of_sale.assets_prod': [
            'pos_distributeur_boisson/static/src/css/distributeur.css',
            'pos_distributeur_boisson/static/src/css/combo_ingredients.css',
            
            'pos_distributeur_boisson/static/src/xml/distributeur.xml',
            'pos_distributeur_boisson/static/src/js/distributeur.js',
            'pos_distributeur_boisson/static/src/js/combo_product.js',
            'pos_distributeur_boisson/static/src/js/combo_popup.js',
            'pos_distributeur_boisson/static/src/js/orderline_delete_button.js',
            'pos_distributeur_boisson/static/src/xml/combo_popup.xml',
        ],
        'web.assets_backend': [
            'pos_distributeur_boisson/static/src/css/combo_ingredients.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
