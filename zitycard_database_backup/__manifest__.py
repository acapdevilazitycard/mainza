{
   'name': 'Zitycard Database Backup',
    'version': '17.0.1.0',
    'category': 'Tools',
    'summary': 'Administrar y programar copias de seguridad de bases de datos para instancias de Odoo',
    'description': """
    Este módulo le ayuda a configurar, programar y administrar copias de seguridad de bases de datos para Odoo.
Incluye funciones para la generación de copias de seguridad, la gestión de retención y la generación de informes.
El módulo admite el almacenamiento local y se puede ampliar al almacenamiento en la nube.
Las funciones incluyen:
- Configurar copias de seguridad para bases de datos.
- Automatizar copias de seguridad con un programador.
- Conservar copias de seguridad en función de una política de retención definida.
- Generar informes detallados sobre el estado de las copias de seguridad.
- Realizar un seguimiento del progreso de las copias de seguridad en tiempo real.
    """,
    'depends': ['base'],
    'author': 'Zitycard',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/db_backup.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
