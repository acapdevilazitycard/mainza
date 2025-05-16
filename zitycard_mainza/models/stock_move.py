from odoo import fields, models

class StockMove(models.Model):
    _inherit = 'stock.move'

    sale_line_name = fields.Text(
        related='sale_line_id.name',
        string='Descripción de venta',
        readonly=False,
    )