# -*- coding: utf-8 -*-

import datetime
from collections import Counter

from odoo import models, fields, api, _
from odoo.osv import expression


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    def _filter_records_to_values(self, records, is_sample=False):
        res_products = super()._filter_records_to_values(records, is_sample)
        if self.model_name == 'product.product':
            if self.env.context.get('add2cart'):
                res_products = [{**d, 'add2cart': True} for d in res_products]
            if self.env.context.get('compare'):
                res_products = [{**d, 'compare': True} for d in res_products]
            if self.env.context.get('wishlist'):
                res_products = [{**d, 'wishlist': True} for d in res_products]
            if self.env.context.get('rating'):
                res_products = [{**d, 'rating': True} for d in res_products]
            if self.env.context.get('quickview'):
                res_products = [{**d, 'quickview': True} for d in res_products]
            if self.env.context.get('color_swatches'):
                res_products = [{**d, 'color_swatches': True} for d in res_products]
            if self.env.context.get('image_flipper'):
                res_products = [{**d, 'image_flipper': True} for d in res_products]
            if self.env.context.get('product_label'):
                res_products = [{**d, 'product_label': True} for d in res_products]
        if self.model_name in ['product.public.category', 'product.brand']:
            if self.env.context.get('count'):
                res_products = [{**d, 'count': True} for d in res_products]
        return res_products

    def _get_products_discount_products(self, website, limit, domain, **kwargs):
        products = []
        price_list = website._get_current_pricelist()
        pl_items = price_list.item_ids.filtered(lambda r: ((not r.date_start or r.date_start <= datetime.datetime.today()) and (not r.date_end or r.date_end > datetime.datetime.today())))
        products_ids = []
        if pl_items.filtered(lambda r: r.applied_on in ['3_global']):
            products = self.env['product.product'].with_context(display_default_code=False,
                                                                add2cart_rerender=True).search(domain, limit=limit)
        else:
            product_product = self.env['product.product'].search([])
            for line in pl_items:
                if line.applied_on in ['1_product']:
                    products = product_product.filtered(lambda l : l.id in line.product_tmpl_id.product_variant_ids.ids)
                elif line.applied_on in ['2_product_category']:
                    products = product_product.filtered(lambda l: l.categ_id.id in line.categ_id.ids)
            products_ids = products and list(set(products.ids)) or []
        if products_ids:
            domain = expression.AND([domain, [('id', 'in', products_ids)]])
            products = self.env['product.product'].with_context(display_default_code=False,
                                                                add2cart_rerender=True).search(domain, limit=limit)
        return products
