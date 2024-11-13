{
    'name': 'Zitycard Mainza',
    'version': '17.0.1.0.0',
    'category': 'Others',
    'summary': """Zitycard Mainza""",
    'description': 'Zitycard Mainza',
    'author': 'Zitycard',
    'company': 'Zitycard',
    'maintainer': 'Zitycard',
    'website': 'https://www.zitycard.com',
    'depends': [
        'account',
        'stock',
        'website_sale_stock',
        'purchase'
    ],
    'data': [
        'reports/report_deliveryslip.xml',
        'reports/report_stockpicking_operations.xml',
        'views/product_template_views.xml',
        'views/portal/product_template_portal_views.xml',
    ],
	'icon': '/zitycard_mainza/static/description/icon.png',
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'zitycard_mainza/static/src/**/*',
        ],
    },
}

