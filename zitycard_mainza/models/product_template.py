# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.http import request
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        product_or_template = product_or_template.sudo()

        if product_or_template.is_product_variant:
            product = product_or_template
            res.update({
                'sale_delay': product.sale_delay,
            })
        else:
            res.update({
                'sale_delay': "",
            })
        return res
