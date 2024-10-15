from odoo import api, models, fields


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    discount = fields.Float(string='Descuento (%)', help='Descuento aplicado al precio estándar')

    discount_price = fields.Float(
        string='Precio Estándar',
        compute='_compute_discount_price',
        store=True,
        readonly=True,
    )

    @api.depends('product_tmpl_id.standard_price', 'discount')
    def _compute_discount_price(self):
        for record in self:
            base_price = record.price
            discount = record.discount or 0.0
            record.discount_price = base_price * (1 - discount / 100)
