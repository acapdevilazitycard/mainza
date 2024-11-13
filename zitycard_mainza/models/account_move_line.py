# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('product_id')
    def _compute_name(self):
        term_by_move = (self.move_id.line_ids | self).filtered(lambda l: l.display_type == 'payment_term').sorted(lambda l: l.date_maturity if l.date_maturity else date.max).grouped('move_id')
        for line in self.filtered(lambda l: l.move_id.inalterable_hash is False):
            if line.display_type == 'payment_term':
                term_lines = term_by_move.get(line.move_id, self.env['account.move.line'])
                n_terms = len(line.move_id.invoice_payment_term_id.line_ids)
                name = line.move_id.payment_reference or ''
                if n_terms > 1:
                    index = term_lines._ids.index(line.id) if line in term_lines else len(term_lines)
                    name = _('%s installment #%s', name, index+1).lstrip()
                line.name = name
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id

            values = []
            if product.name:
                values.append(product.name)
            if line.journal_id.type == 'sale':
                if product.description_sale:
                    values.append(product.description_sale)
            elif line.journal_id.type == 'purchase':
                if product.description_purchase:
                    values.append(product.description_purchase)
            line.name = '\n'.join(values)
