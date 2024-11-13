from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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
