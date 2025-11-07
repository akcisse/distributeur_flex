# -*- coding: utf-8 -*-
{
    'name': 'POS User Organization & Barmans',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'summary': 'Groupes Barmans, journal crédits POS, présence utilisateurs, server_no employé',
    'depends': ['point_of_sale', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pos_credit_log_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
        'point_of_sale.assets_prod': [
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
