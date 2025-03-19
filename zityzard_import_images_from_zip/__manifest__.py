# -*- coding: utf-8 -*-
{
    'name': "Zitycard - Importar imágenes de productos desde zip",
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """Importación de imágenes para productos desde archivo zip""",
    'description': """Importación de imágenes para productos desde archivo zip""",
    'author': "Zitycard",
    'maintainer': 'Zitycard',
    'website': 'https://www.zitycard.com',
    'depends': ['sale_management', 'contacts', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_image.xml',
    ],
	'icon': '/zitycard_import_images_from_zip/static/description/icon.png',
}
