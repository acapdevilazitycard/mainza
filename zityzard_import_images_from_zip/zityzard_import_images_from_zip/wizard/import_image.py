# -*- coding: utf-8 -*-
import base64
import tempfile
import io
import zipfile
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ImportImage(models.TransientModel):
    _name = "import.image"
    _description = 'Import Image Wizard'
    file = fields.Binary(string='Archivo ZIP', required=True)
    search_by = fields.Selection(selection=[
                    ('name', "Name"),
                    ('internal_reference', "Internal Reference"),
                    ('barcode', "Barcode"),
                    ('category', "category"),
                    ('identification_no', "ID"),
                    ('attributes', "Attributes"),
                ], string='Buscar por', required=True)
    model_template = fields.Selection([
        ('product.template', "Product Template"),
    ], help="Modelo para la importación", string="Modelo de importación",
        default='product.template')
    split = fields.Char(string='Separador')
    field_name = fields.Char(string='Nombre del campo de la imagen')

    def _get_vals(self, search_value, search_by):
        search_vals = search_value.split(self.split) if self.split else [search_value]

        if search_by == 'attributes':
            if len(search_vals) < 2 or len(search_vals) % 2 != 0:
                return False

            domain = []
            attr_count = len(search_vals) // 2

            for i in range(0, len(search_vals), 2):
                attribute_name = search_vals[i]
                value_name = search_vals[i + 1]

                attribute = self.env['product.attribute'].search([('name', '=', attribute_name)], limit=1)
                if not attribute:
                    continue

                attr_value = self.env['product.attribute.value'].search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', value_name)
                ], limit=1)

                if not attr_value:
                    continue

                product_tmpl_ids = self.env['product.template.attribute.value'].search([
                    ('attribute_id', '=', attribute.id),
                    ('product_attribute_value_id', '=', attr_value.id)
                ]).mapped('product_tmpl_id')

                if product_tmpl_ids:
                    domain.append(('product_tmpl_id', 'in', product_tmpl_ids.ids))

            if domain:
                products = self.env['product.product'].search(domain)
                final_products = self.env['product.product']

                for product in products:
                    if len(product.product_template_attribute_value_ids) == attr_count:
                        final_products |= product

                return final_products if final_products else False
            return False

        elif len(search_vals) == 2 and search_by == 'category':
            parent_category = self.env['product.category'].search([('name', '=', search_vals[0])], limit=1)
            if parent_category:
                category = self.env['product.category'].search([('name', '=', search_vals[1])], limit=1)
                if category:
                    return self.env['product.product'].search([('categ_id', '=', category.id)])
        elif search_by == 'category':
            category = self.env['product.category'].search([('name', '=', search_value)])
            if category:
                return self.env['product.product'].search([('categ_id', '=', category.id)])
        elif search_by == 'name':
            return self.env['product.product'].search([('name', '=', search_value)])
        elif search_by == 'internal_reference':
            return self.env['product.product'].search([('default_code', '=', search_value)])
        elif search_by == 'barcode':
            return self.env['product.product'].search([('barcode', '=', search_value)])
        elif search_by == 'identification_no':
            return self.env['product.product'].search([('id', '=', search_value)])
        return False

    def import_images(self):
        if not self.file:
            raise UserError('Please upload a ZIP file.')

        zip_file = base64.b64decode(self.file)
        zip_data = io.BytesIO(zip_file)

        with zipfile.ZipFile(zip_data, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.lower().endswith(('png', 'jpg', 'jpeg')):
                    image_data = zip_ref.read(file_name)
                    file_name = file_name.split('.')[0]  # Assuming file name is product name or category
                    vals = self._get_vals(file_name, self.search_by)

                    if vals:
                        for val in vals:
                            val.write({self.field_name: base64.b64encode(image_data)})
                            _logger.warning("UPDATED PHOTO - %s", val.name)
                    else:
                        _logger.warning("VALUE NOT FIND: %s", file_name)

        return {'type': 'ir.actions.act_window_close'}
