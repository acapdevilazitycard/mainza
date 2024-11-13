# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.http import request
from odoo.tools.translate import html_translate


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            for purchase_order_line_id in order.order_line:
                if purchase_order_line_id.product_id and purchase_order_line_id.product_id.standard_price != purchase_order_line_id.price_unit:
                    purchase_order_line_id.product_id.standard_price = purchase_order_line_id.price_unit
        return res
