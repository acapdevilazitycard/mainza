from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_noindex = fields.Boolean(
        default=False,
        help='Si está activado, el producto será visible en la web pero invisible para motores de búsqueda (Google, Bing, etc.)'
    )

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        product_or_template = product_or_template.sudo()

        if product_or_template.is_product_variant:
            product = product_or_template
            res.update({
                'sale_delay': product.sale_delay,
                'available_threshold': product.available_threshold,
            })
        else:
            res.update({
                'sale_delay': "",
                'available_threshold': 0,
            })
        return res

    has_free_qty = fields.Boolean(string='Has Free Quantity', compute='_compute_has_free_qty', store=True)

    @api.depends('product_variant_ids.free_qty')
    def _compute_has_free_qty(self):
        for product in self:
            product.has_free_qty = any(variant.free_qty > 0 for variant in product.product_variant_ids)
