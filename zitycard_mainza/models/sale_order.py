from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    nombre_presupuesto = fields.Char(string='Nombre Presupuesto', copy=False)
