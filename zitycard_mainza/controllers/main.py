from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSale(WebsiteSale):

    def _get_search_order(self, post):
        order = post.get('order') or request.env['website'].get_current_website().shop_default_sort
        if order in ['name asc','website_sequence asc']:
            return 'is_published desc, has_free_qty desc, %s, id desc' % order
        else:
            return super()._get_search_order(post)
