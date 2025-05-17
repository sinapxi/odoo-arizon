# -*- coding: utf-8 -*-

import datetime
import json
import logging

from itertools import product
from odoo.osv import expression
from odoo import http, fields, _
from odoo.http import request, route
from odoo.tools import lazy
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSaleWishlist
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.exceptions import UserError
from werkzeug.datastructures import ImmutableOrderedMultiDict

# from Odoo.odoo.odoo.cli.scaffold import template

_logger = logging.getLogger(__name__)


class CustomerPortalExt(CustomerPortal):

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        res = super().account(redirect=redirect, **post)

        countries = res.qcontext.get('countries', False)
        partner = res.qcontext.get('partner', False)
        current_website = request.env['website'].get_current_website()

        if countries:
            allow_countries = set(current_website.allow_countries or countries)

            if partner and partner.country_id:
                allow_countries.add(partner.country_id)

            allowed_countries = allow_countries

            res.qcontext.update({
                'countries': allowed_countries,
                'default_country_id': current_website.default_country_id if current_website.default_country_id else None
            })

        return res


class EmiproThemeBase(http.Controller):

    @http.route(['/quick_view_item_data'], type='json', auth="public", website=True)
    def get_quick_view_item(self, product_id=None):
        if product_id:
            product = request.env['product.template'].search([['id', '=', product_id]])
            response = http.Response(template="emipro_theme_base.quick_view_container", qcontext={'product': product})
            return response.render()

    @http.route(['/similar_products_item_data'], type='http', auth="public", website=True)
    def similar_products_item_data(self, product_id=None):
        if product_id:
            product = request.env['product.template'].search([['id', '=', product_id]])
            website_ids = [False, request.website.id]
            alternative_products = product.alternative_product_ids.filtered(
                lambda p: p.sale_ok and p.website_id.id in website_ids)

            def sort_function(value):
                list_price = value.get('list_price', 0)
                price = value.get('price', 0)
                if list_price > price:
                    return (list_price - price) / list_price
                else:
                    return 0

            alternative_products_details = list(
                map(lambda product: product._get_combination_info(), alternative_products))
            values = {
                'alternative_products': alternative_products_details,
                'website': request.website

            }
            response = http.Response(template="emipro_theme_base.similar_products_view_container", qcontext=values)
            return response.render()

    @http.route(['/shop/clear_cart'], type='json', auth="public", website=True)
    def clear_cart(self):
        """
        Clear the xml in e-commerce website
        @return: -
        """
        order = request.website.sale_get_order()
        order and order.website_order_line.unlink()
        request.session['website_sale_cart_quantity'] = 0

    @http.route(['/get_search_data'], type='json', auth="public", website=True)
    def search_popover_data(self):
        response = http.Response(template="theme_clarico_vega.mobile_header_search_container")
        return response.render()

    @http.route(['/get_categories_list_data'], type='json', auth="public", website=True)
    def categories_list_data(self):
        current_website = request.website.get_current_website()
        all_categories = request.env['product.public.category'].sudo().search(
            [('website_id', 'in', (False, current_website.id)), ('parent_id', '=', False)])
        category_data = [
            {
                'current_category': category,
                'product_count': request.env['product.template'].sudo().search_count(
                    [('public_categ_ids', 'child_of', category.id)]),
            }
            for category in all_categories
        ]
        if category_data:
            values = {
                'categories': category_data,
            }
            response = http.Response(template="emipro_theme_base.mobile_header_categories_option_view_container", qcontext=values)
            return response.render()

    @http.route(['/hover/color'], type='json', auth="public", methods=['POST'], website=True)
    def hover_color(self, product_id=False, value_id=False, **post):
        if product_id and value_id:
            product_id = request.env['product.template'].sudo().browse(product_id)
            variant = product_id.product_variant_ids.product_template_variant_value_ids and \
                      product_id.product_variant_ids.filtered(
                          lambda p: int(
                              value_id) in p.product_template_variant_value_ids.product_attribute_value_id.ids)[0]
            if variant:
                return {
                    'url': f'/web/image/product.product/{str(variant.id)}/image_512',
                    'product_id': product_id.id,
                }

    @http.route(['/rename_collection'], type='json', auth='public', website=True)
    def rename_collection(self, collection_name=None, collection_id=None):
        res = False
        if collection_id and collection_name:
            collection = request.env['wishlist.collection'].sudo().browse(int(collection_id))
            collection.name = collection_name
            res = True
        return res

    @http.route('/select_collection_modal_data', auth='public', type='json', website=True)
    def select_collection_modal_data(self):
        """ Render collection popup for logged-in user
        """
        response = http.Response(template="theme_clarico_vega.select_collection_popup_tmpl",
                                 qcontext={})
        return response.render()

    @http.route(['/check_collection'], type='json', auth='user', website=True)
    def _check_collection(self, collection_id=None):
        """ This controller will check either products are available in collection or not
            return: True if contains at least one product else False
        """
        res = False
        if collection_id:
            collection = request.env['wishlist.collection'].sudo().browse(int(collection_id))
            res = True if collection.product_line_ids else False
        return res

    @http.route('/check_collections', auth='public', type='json', website=True)
    def _check_collections(self):
        """ Check collections are available or not for current logged-in user.
        :return: dict
        """
        res = {}
        user = request.env.user.sudo()
        res['is_partner'] = False if user.id == request.env.ref(
            'base.public_user').id else user.partner_id
        collections = request.env['wishlist.collection'].get_partner_collections(user.partner_id)
        res['collections'] = collections or False
        return res

    @http.route('/check_collection_name', auth='user', type='json', website=True)
    def check_collection_name(self, collection_name):
        """ Check collection name is valid or not
        :param collection_name: Name of collection entered by User
        :return: True if collection name is valid else False
        """
        res = True
        partner = request.env.user.sudo().partner_id
        collections = request.env['wishlist.collection'].get_partner_collections(partner)
        if collection_name in collections.mapped('name') or \
                collection_name.isspace() or not len(collection_name):
            res = False
        return res

    @http.route('/add_select_collection', auth='user', type='json', website=True)
    def add_select_collection(self, collection_name):
        """ Create new collection.
        :param collection_name: name of collection
        :return: string id of created collection
        """
        partner = request.env.user.sudo().partner_id
        collection = request.env['wishlist.collection'].sudo()
        collections = collection.get_partner_collections(partner)
        if len(collection_name) and collection_name not in collections.mapped('name'):
            vals = {'name': collection_name, 'partner_id': partner.id}
            collection = collection.create(vals)
        return str(collection.id)

    @http.route('/add_product_in_collection', auth='user', type='json', website=True)
    def add_product_in_collection(self, collection_id, product_id, product_qty):
        """ Add product in selected collection.
        :param collection_id: id of selected collection
        :param product_id: id of the product that will be added in collection
        :param product_qty: quantity of product
        :return: bool
        """
        res = False
        collection = request.env['wishlist.collection'].sudo().search([('id', '=', int(collection_id))])
        product = request.env['product.product'].sudo().search([('id', '=', int(product_id))])
        line_product_ids = collection.product_line_ids.mapped('product_id') or False

        if product:
            if line_product_ids and product.id in line_product_ids.ids:
                res = False
            else:
                vals = {'collection_id': collection.id, 'product_id': product.id, 'quantity': int(product_qty)}
                request.env['product.line'].sudo().create(vals)
                res = True

        return res

    @http.route('/check_product_in_collection', auth='user', type='json', website=True)
    def check_product_in_collection(self, collection_id, product_id):
        """ Check whether product is already exist in collection or not
        :param collection_id: id of collection in string
        :param product_id: id of product in string
        :return: True if product already exist in collection else False
        """
        res = False
        collection = request.env['wishlist.collection'].sudo().search([('id', '=', int(collection_id))])
        line_product_ids = collection.product_line_ids.mapped('product_id') or False
        if line_product_ids and product_id in line_product_ids.ids:
            res = True
        return res

    @http.route('/add_to_cart_collection', type='json', auth='user', website=True)
    def add_to_cart_collection(self, product_line_id=None):
        """ Update products to cart when a user clicks Add to Cart button,
        also redirect user to cart"""
        product_line = request.env['product.line'].sudo().search(
            [('id', '=', int(product_line_id))]) if product_line_id else None
        current_cart_order = request.website.sale_get_order(force_create=True)
        res = False
        if product_line:
            res = current_cart_order._cart_update(product_id=product_line.product_id.id,
                                                  add_qty=product_line.quantity)
        return res

    @http.route('/remove_collection', auth='user', type='json', website=True)
    def remove_collection(self, collection_id):
        """ Remove collection if logged-in user and partner of collection are same.
        :param collection_id: id of collection in string
        :return: True if collection removed else False
        """
        partner = request.env.user.sudo().partner_id
        collection = request.env['wishlist.collection'].sudo().browse(int(collection_id))
        res = False
        if collection.partner_id == partner:
            wishes = request.env['product.wishlist'].sudo().search(
                [('partner_id', '=', partner.id),
                 ('product_id', 'in', collection.product_line_ids.product_id.ids)]
            ) if partner and collection.product_line_ids else request.env['product.wishlist'].sudo()
            if wishes:
                # Remove wishes which is associated with current partner and products of the current collection.
                wishes.sudo().unlink()
            collection.product_line_ids.unlink()
            res = collection.unlink()
        return res

    @http.route('/remove_product', auth='user', type='json', website=True)
    def remove_product(self, product_line_id):
        """ Remove product from collection(list) and also remove wishlist record where product is linked.
        :param product_line_id: product line of list
        :return: collection
        """
        product_line_id = request.env['product.line'].sudo().search(
            [('id', '=', int(product_line_id))])

        partner = request.env.user.sudo().partner_id
        wish = request.env['product.wishlist'].sudo().search(
            [('partner_id', '=', partner.id), ('product_id', '=', product_line_id.product_id.id)]
        ) if partner and product_line_id else request.env['product.wishlist'].sudo()
        if wish:
            # Remove wish which is associated with current partner and product.
            wish.sudo().unlink()

        collection = product_line_id.collection_id
        product_line_id.unlink()
        return collection

    @http.route('/shop/wishlist/all_products', auth='public', type='json', website=True)
    def shop_wishlist_all_products(self):
        values = request.env['product.wishlist'].with_context(display_default_code=False).current()
        return json.dumps(values.mapped('product_id').ids)

    @http.route('/send_collection', auth='user', type='json', website=True)
    def send_collection(self, collection_id=None, recipient_email=None):
        res = False

        partner = request.env.user.sudo().partner_id
        collection = request.env['wishlist.collection'].sudo().browse(int(collection_id))

        template = request.env.ref('emipro_theme_base.share_wishlist_collection_email', raise_if_not_found=False)

        if template:
            try:
                template = template.with_context(recipient_email=recipient_email,
                                                 subject='%s Has Shared an Exclusive Wishlist Collection with You!' % (
                                                     collection.partner_id.name))
                template.send_mail(collection.id)
                _logger.info("<%s> Shared wishlist to <%s>", collection.partner_id.name, recipient_email)
                res = True
            except Exception as e:
                _logger.info("Error occured while sharing wishlist %s", str(e))

        return res

    @http.route('/get_product_info', auth='public', type='json', website=True)
    def get_product_info(self, product_id=None):
        if product_id:
            product = request.env['product.template'].browse(eval(product_id))
            combination_info = product._get_combination_info()
            response = http.Response(template="theme_clarico_vega.product_pager",
                                     qcontext={'product': product, 'combination_info': combination_info})
            return response.render()

class WebsiteExt(Website):

    @http.route()
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        
        if search_type is None:
            search_type = 'products_only'

        res = super().autocomplete(search_type, term, order, limit, max_nb_chars, options)

        filtered_results = [rs for rs in res['results'] if rs.get('_fa') != 'fa-folder-o']
        res['results'] = filtered_results

        current_website = request.website.get_current_website()
        categories = request.env['product.public.category'].sudo().search(
            [('website_id', 'in', (False, current_website.id))]).filtered(
            lambda catg: term.strip().lower() in catg.name.strip().lower())
        search_categories = []
        for categ in categories:
            search_categories.append({'_fa': 'fa-folder-o', 'name': categ.name,
                                      'website_url': f'/shop/category/{categ.id}'})
        res['categories'] = search_categories[:10]

        if term and current_website and current_website.enable_smart_search:
            is_quick_link = {'status': False}

            brand = request.env['product.brand'].sudo().search(
                [('website_id', 'in', (False, current_website.id)),('website_published','=',True)]).filtered(
                lambda b: term.strip().lower() in b.name.strip().lower())

            if brand and current_website.search_in_brands:
                is_quick_link.update({'status': True,
                                      'navigate_type': 'brand',
                                      'name': brand[0].name,
                                      'url': f'/shop/brands/{brand[0].id}'})

            if current_website.search_in_attributes_and_values:
                attribute_value = request.env['product.attribute.value'].sudo().search([]).filtered(lambda value: term.strip().lower() == value.name.strip().lower())
                if not attribute_value:
                    attribute_value = request.env['product.attribute.value'].sudo().search([]).filtered(
                        lambda value: term.strip().lower() in value.name.strip().lower())

                if attribute_value:
                    is_quick_link.update({'status': True,
                                          'navigate_type': 'attr_value',
                                          'name': attribute_value[0].name,
                                          'attribute_name': attribute_value[0].attribute_id.name,
                                          'url': f'/shop?search=&attribute_value='
                                                 f'{attribute_value[0].attribute_id.id}-{attribute_value[0].id}'})
            res['is_quick_link'] = is_quick_link

        return res

    @http.route([
        '/website/search',
        '/website/search/page/<int:page>',
        '/website/search/<string:search_type>',
        '/website/search/<string:search_type>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=False)
    def hybrid_list(self, page=1, search='', search_type='all', **kw):
        result = super().hybrid_list(page=page, search=search, search_type=search_type, **kw)

        curr_website = request.website.get_current_website()
        if search and curr_website.enable_smart_search:
            search_term = ' '.join(search.split()).strip().lower()
            if search_term:
                request.env['search.keyword.report'].sudo().create({
                    'search_term': search_term,
                    'no_of_products_in_result': result.qcontext.get('search_count', 0),
                    'user_id': request.env.user.id
                })

        return result

    @http.route(website=True, auth="public", sitemap=False, csrf=False)
    def web_login(self, *args, **kw):
        """
            Login - overwrite of the web login so that regular users are redirected to the backend
            while portal users are redirected to the same page from popup
            Returns formatted data required by login popup in a JSON compatible format
            Added by: Shubham Kumar
            Date: 15 Oct 2024
        """
        login_form_ept = kw.get('login_form_ept', False)
        if 'login_form_ept' in kw.keys():
            kw.pop('login_form_ept')

        response = super(WebsiteExt, self).web_login(*args, **kw)
        if login_form_ept:
            if response.is_qweb and response.qcontext.get('error', False):
                return json.dumps(
                    {'error': response.qcontext.get('error', False), 'login_success': False,
                     'hide_msg': False})
            else:
                if request.params.get('login_success', False):
                    credential = {'login': request.params['login'], 'password': request.params['password'],
                                  'type': 'password'}
                    uid = request.session.authenticate(request.session.db, credential)['uid']
                    user = request.env['res.users'].browse(uid)
                    redirect = '1'
                    if user.totp_enabled:
                        redirect = request.env(user=uid)['res.users'].browse(uid)._mfa_url()
                        return json.dumps(
                            {'redirect': redirect, 'login_success': True, 'hide_msg': True})
                    if user.has_group('base.group_user'):
                        redirect = b'/web?' + request.httprequest.query_string
                        redirect = redirect.decode('utf-8')
                    return json.dumps(
                        {'redirect': redirect, 'login_success': True, 'hide_msg': False})
        return response

    @http.route(auth='public', website=True, sitemap=False, csrf=False)
    def web_auth_reset_password(self, *args, **kw):
        """
            Reset password from popup and redirect to the same page
            Returns formatted data required by login popup in a JSON compatible format
            Added by: Shubham Kumar
            Date: 15 Oct 2024
        """
        reset_form_ept = kw.get('reset_form_ept', False)
        if 'reset_form_ept' in kw.keys():
            kw.pop('reset_form_ept')
        response = super(WebsiteExt, self).web_auth_reset_password(*args, **kw)
        if reset_form_ept:
            if response.is_qweb and response.qcontext.get('error', False):
                return json.dumps({'error': response.qcontext.get('error', False)})
            elif response.is_qweb and response.qcontext.get('message', False):
                return json.dumps({'message': response.qcontext.get('message', False)})
        return response

    @http.route('/see_all', type='json', auth="public", methods=['POST'], website=True)
    def get_see_all(self, attr_id='', is_mobile='', attr_count='', brand_count='', is_brand='', tag_count='',
                    is_tag=''):
        # category = None
        # if category_id:
        #     category = request.env['product.public.category'].sudo().browse(int(category_id))

        attr_count = attr_count and eval(attr_count)
        brand_count = brand_count and eval(brand_count)
        tag_count = tag_count and eval(tag_count)

        if attr_id and attr_id != '0':
            attributes = request.env['product.attribute'].search([('id', '=', attr_id), ('visibility', '=', 'visible')])

            if is_mobile == 'True':
                response = http.Response(template="theme_clarico_vega.see_all_attr_mobile",
                                         qcontext={'attributes': attributes, 'attr_count': attr_count})

            else:
                response = http.Response(template="theme_clarico_vega.see_all_attr",
                                         qcontext={'attributes': attributes, 'attr_count': attr_count})

        elif is_brand == 'True':
            brands = request.env['product.brand'].sudo().search(
                [('website_published', '=', True), ('product_ids', '!=', False)])

            if is_mobile == 'True':
                response = http.Response(template="theme_clarico_vega.see_all_attr_brand_mobile",
                                         qcontext={'brands': brands, 'brand_count': brand_count})
            else:
                response = http.Response(template="theme_clarico_vega.see_all_attr_brand",
                                         qcontext={'brands': brands, 'brand_count': brand_count})

        elif is_tag:
            ProductTag = request.env['product.tag'].sudo().search([('visible_on_ecommerce', '=', True)])
            response = http.Response(template="theme_clarico_vega.see_all_tags",
                                     qcontext={'all_tags': ProductTag, 'tag_count': tag_count})

        return response.render()


class WebsiteSaleExt(WebsiteSale):

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        discount = 'discount' in post.get('order', '')
        if discount:
            post.pop('order', None)

        fuzzy_search_term, product_count, search_result = super(WebsiteSaleExt, self)._shop_lookup_products(attrib_set,
                                                                                                            options,
                                                                                                            post,
                                                                                                            search,
                                                                                                            website)

        def sort_function(product):
            list_price = product.get('list_price', 0)
            price = product.get('price', 0)
            # Calculate the discount ratio only if list_price is greater than price
            return (list_price - price) / list_price if list_price > price else 0

        if discount:
            # Get the product combination info and sort it directly in one step
            product_prices_data = sorted((product._get_combination_info() for product in search_result),
                                         key=sort_function, reverse=True)

            # Extract product template IDs and browse the sorted products
            product_template_ids = [p.get('product_template_id') for p in product_prices_data]
            search_result = request.env['product.template'].browse(product_template_ids)

        return fuzzy_search_term, product_count, search_result

    @route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
        '/shop/brands/<model("product.brand"):brand>',
        '/shop/brands/<model("product.brand"):brand>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):

        request_args = request.httprequest.args
        post.update(request_args=request_args.getlist('attribute_value', None))

        mutable_data = request_args.to_dict(flat=False)  # flat=False retains multiple values for the same key

        if 'attribute_value' in mutable_data:
            mutable_data['attribute_value'] = [
                value for value in mutable_data['attribute_value'] if value and not value.startswith('0')
            ]

        request.httprequest.args = ImmutableOrderedMultiDict(mutable_data)

        res = super(WebsiteSaleExt, self).shop(page=page, category=category, search=search, min_price=min_price,
                                               max_price=max_price, ppg=ppg, **post)

        # Create Report for the search keyword
        curr_website = request.website.get_current_website()
        if search and curr_website.enable_smart_search:
            search_term = ' '.join(search.split()).strip().lower()
            attrib = res.qcontext.get('attrib_values', False)
            if search_term and not category and not attrib and page == 0:
                request.env['search.keyword.report'].sudo().create({
                    'search_term': search_term,
                    'no_of_products_in_result': res.qcontext.get('search_count', 0),
                    'user_id': request.env.user.id
                })

        return res

    def _prepare_address_form_values(self, *args, address_type, use_delivery_as_billing, **kwargs):
        rendering_values = super()._prepare_address_form_values(*args, address_type=address_type,
                                                                use_delivery_as_billing=use_delivery_as_billing,
                                                                **kwargs)
        countries = rendering_values.get('countries', False)
        partner_id = rendering_values.get('partner_sudo', False)
        current_website = request.env['website'].get_current_website()

        if countries:
            allow_countries = set(current_website.allow_countries or countries)

            if partner_id and partner_id.country_id:
                allow_countries.add(partner_id.country_id)

            allowed_countries = allow_countries or countries

            rendering_values.update({
                'countries': allowed_countries,
                'default_country_id': current_website.default_country_id if current_website.default_country_id else None
            })

        return rendering_values

    def _get_search_options(self, **post):
        options = super(WebsiteSaleExt, self)._get_search_options(**post)
        curr_website = request.website.get_current_website()

        # Brand Page
        options.update({'brand': post.get('brand', False)})

        # Out Of Stock
        options.update({'out_of_stock': post.get('out_of_stock', False) or not curr_website.display_out_of_stock})

        # BRAND FILTER
        if post.get('request_args', False):
            options.update({'request_args': post.get('request_args')})

        return options

    def _get_additional_extra_shop_values(self, values, **post):
        vals = super(WebsiteSaleExt, self)._get_additional_extra_shop_values(values, **post)

        attrib_values = values.get('attrib_values', False)
        category = values.get('category', None)
        search = values.get('search', '')
        base_domain = self._get_shop_domain(search, category, attrib_values)

        if post.get('brand', False):
            base_domain = expression.AND([base_domain, [('product_brand_id', '=', post.get('brand').id)]])
            values.update(brand_val=post.get('brand', False))

        if post.get('tags', False):
            base_domain = expression.AND(
                [base_domain, [('product_variant_ids.all_product_tag_ids', 'in', post.get('tags'))]])

        # Added brand records
        products = values.get('products', None)
        if products:
            search_product = values.get('search_product', None)
            brands = lazy(lambda: request.env['product.brand'].search(
                [('product_ids', 'in', search_product and search_product.ids or []),('website_published','=',True)]))
        else:
            brand_ids = {v[1] if v[0] == 0 else None for v in attrib_values}
            brands = lazy(lambda: request.env['product.brand'].browse(brand_ids))

        if not values.get('brand', False):
            values.update(brands=brands)

        # Brand Product Count
        brand_count = {}

        for brand in brands:
            brand_domain = expression.AND([base_domain, [('product_brand_id', '=', brand.id)]])
            brand_count[brand.id] = request.env['product.template'].search_count(brand_domain) or 0

        values.update(brand_count=brand_count)

        # Attribute Product Count
        attr_count = {}

        for a in values.get('attributes', []):
            for v in a.value_ids:
                attribute_domain = expression.AND([base_domain, [('attribute_line_ids.value_ids', '=', v.id)]])
                attr_count[v.id] = request.env['product.template'].search_count(attribute_domain) or 0

        values.update(attr_count=attr_count)

        # Tag Product Count
        tag_count = {}

        for tag in values.get('all_tags', []):
            tag_domain = expression.AND([base_domain, [('product_variant_ids.all_product_tag_ids', '=', tag.id)]])
            tag_count[tag.id] = request.env['product.template'].search_count(tag_domain) or 0

        values.update(tag_count=tag_count)

        # Categories Product Count
        categ_count = {}

        def get_category_count(category):
            categ_base_domain = self._get_shop_domain(search, None, attrib_values)

            if post.get('brand', False):
                categ_base_domain = expression.AND(
                    [categ_base_domain, [('product_brand_id', '=', post.get('brand').id)]])

            if post.get('tags', False):
                categ_base_domain = expression.AND(
                    [categ_base_domain, [('product_variant_ids.all_product_tag_ids', 'in', post.get('tags'))]])

            category_domain = expression.AND([categ_base_domain, [('public_categ_ids', 'child_of', category.id)]])
            return request.env['product.template'].search_count(category_domain) or 0

        for category in values.get('categories', []):
            categ_count[category.id] = get_category_count(category)

            for child_categ in category.child_id:
                categ_count[child_categ.id] = get_category_count(child_categ)

        values.update(categ_count=categ_count)

        return vals

    @http.route(['/shop/cart_popover'], type='http', auth="public", website=True, sitemap=False)
    def cart_popover(self, **post):
        """
        Main xml management + abandoned xml revival
        access_token: Abandoned xml SO access token
        revive: Revival method when abandoned xml. Can be 'merge' or 'squash'
        """
        order = request.website.sale_get_order()
        if order and order.carrier_id:
            # Express checkout is based on the amout of the sale order. If there is already a
            # delivery line, Express Checkout form will display and compute the price of the
            # delivery two times (One already computed in the total amount of the SO and one added
            # in the form while selecting the delivery carrier)
            order._remove_delivery_line()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()

        request.session['website_sale_cart_quantity'] = order.cart_quantity

        values = {}

        values.update({
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': [],
        })
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
            values['suggested_products'] = order._cart_accessories()
            values.update(self._get_express_shop_payment_values(order))

        values.update(self._cart_values(**post))
        return request.render("emipro_theme_base.cart_popover", values)

    # Render the Hotspot Product popover template
    @http.route('/get-pop-up-product-details', type='http', auth='public', website=True)
    def get_popup_product_details(self, **kw):
        """
        Render the Hotspot Product popover template
        @param kw: dict for product details
        @return: response for template
        """
        product = int(kw.get('product'))
        if kw.get('product', False):
            product = request.env['product.template'].sudo().browse(product)
            values = {'product': product}
            return request.render("theme_clarico_vega.product_add_to_cart_popover", values,
                                  headers={'Cache-Control': 'no-cache'})

    @http.route('/search_sidebar_ept', type='http', auth='public', website=True, sitemap=False)
    def search_sidebar(self):
        return request.render('theme_clarico_vega.website_search_box_input_ept', headers={'Cache-Control': 'no-cache'})


class WebsiteSaleVariantControllerExt(WebsiteSaleVariantController):

    @route()
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty,
                                     parent_combination=None, **kwargs):
        res = super().get_combination_info_website(product_template_id=product_template_id,
                                                   product_id=product_id,
                                                   combination=combination,
                                                   add_qty=add_qty,
                                                   parent_combination=parent_combination, **kwargs)

        product_id = res.get('product_id', product_id)
        product = request.env['product.product'].sudo().search([('id', '=', product_id)])
        product_template = request.env['product.template'].sudo().search([('id', '=', product_template_id)])
        pricelist = request.website._get_current_pricelist()

        # Price Table
        if product and product_template:
            if request.website.display_product_price():
                res['price_table_details'] = pricelist.enable_price_table and self.get_price_table(pricelist,
                                                                                                   product,
                                                                                                   product_template)
        details = self.get_offer_details(pricelist, product, add_qty)
        res.update(details)

        return res

    def get_price_table(self, pricelist, product, product_tempate):
        current_date = datetime.datetime.now()
        pricelist_items = pricelist._get_applicable_rules(product, current_date)

        # Get the rules based on the priority based on condition
        # updated_rules = (items.filtered(
        #     lambda rule: rule.applied_on == '0_product_variant' and rule.product_id.id == product.id)
        #                  or items.filtered(
        #             lambda rule: rule.applied_on == '1_product' and rule.product_tmpl_id.id == product_tempate.id)
        #                  or items.filtered(lambda
        #                                        rule: rule.applied_on == '2_product_category' and rule.categ_id.id in product_tempate.categ_id.search(
        #             [('id', 'parent_of', product_tempate.categ_id.ids)]).ids)
        #                  or items.filtered(lambda rule: rule.applied_on == '3_global'))

        price_list_items = []
        minimum_qtys = set()
        minimum_qtys.add(1)
        for rule in pricelist_items:
            minimum_qtys.add(rule.min_quantity)
        minimum_qtys.discard(0)
        minimum_qtys = list(minimum_qtys)
        minimum_qtys.sort()

        for qty in minimum_qtys:
            price = pricelist._get_product_price(product=product, quantity=qty, target_currency=pricelist.currency_id)
            list_price = product.list_price or 0
            discount = 0
            if list_price and price:
                difference = round(list_price - price, 2)
                discount = round((difference*100) / list_price, 2)
            data = {'qty': int(qty), 'price': price, 'disc_per': discount}
            price_list_items.append(data)

        price_list_vals = {
            'pricelist_items': price_list_items,
            'currency_id': pricelist.currency_id,
        }

        return http.Response(template="emipro_theme_base.product_price_table", qcontext=price_list_vals).render()

    def get_offer_details(self, pricelist, product, add_qty):
        offer_details = {
            'is_offer': False
        }
        try:
            vals = pricelist._compute_price_rule(product, add_qty)
            if vals.get(int(product)) and vals.get(int(product))[1]:
                suitable_rule = vals.get(int(product))[1]
                suitable_rule = request.env['product.pricelist.item'].sudo().browse(suitable_rule)
                if suitable_rule.date_end and suitable_rule.is_display_timer:
                    start_date = int(round(datetime.datetime.timestamp(suitable_rule.date_start) * 1000))
                    end_date = int(round(datetime.datetime.timestamp(suitable_rule.date_end) * 1000))
                    current_date = int(round(datetime.datetime.timestamp(datetime.datetime.now()) * 1000))
                    offer_details.update({
                        'is_offer': True,
                        'start_date': start_date,
                        'end_date': end_date,
                        'current_date': current_date,
                        'suitable_rule': suitable_rule,
                        'offer_msg': suitable_rule.offer_msg,
                    })
        except Exception as e:
            return offer_details
        return offer_details


# class AuthSignupHome(Home):
#
#     @http.route(website=True, auth="public", sitemap=False, csrf=False)
#     def web_auth_signup(self, *args, **kw):
#         """
#             Signup from popup and redirect to the same page
#             Returns formatted data required by login popup in a JSON compatible format
#
#             Added by: Shubham Kumar
#             Date: 10 Oct 2024
#         """
#         qcontext = self.get_auth_signup_qcontext()
#
#         if 'signup_form_ept' in kw.keys():
#             kw.pop('signup_form_ept')
#
#         login_email = kw.get('login', False)
#
#         def recaptcha_token_verification(token=None):
#             ip_addr = request.httprequest.remote_addr
#             recaptcha_result = request.env['ir.http']._verify_recaptcha_token(ip_addr, token)
#             if recaptcha_result in ['is_human', 'no_secret', 'is_bot']:
#                 return [True, 'Validation Successful']
#             if recaptcha_result == 'wrong_secret':
#                 return [False, 'The reCaptcha private key is invalid.']
#             elif recaptcha_result == 'wrong_token':
#                 return [False, 'The reCaptcha token is invalid.']
#             elif recaptcha_result == 'timeout':
#                 return [False, 'Your request has timed out, please retry.']
#             elif recaptcha_result == 'bad_request':
#                 return [False, 'The request is invalid or malformed.']
#             else:
#                 return [False, "Form didn't submitted, Try again"]
#
#         # Check google recaptcha if available
#         if login_email and 'error' not in qcontext and request.httprequest.method == 'POST':
#             if request.website.signup_captcha_option:
#                 token = ''
#                 if 'recaptcha_token_response' in kw.keys():
#                     token = kw.pop('recaptcha_token_response')
#                 if 'recaptcha_token_response' in request.params:
#                     request.params.pop('recaptcha_token_response')
#                 verification = recaptcha_token_verification(token)
#                 if not verification[0]:
#                     qcontext['captcha_error'] = _(verification[1])
#
#         if 'captcha_error' in qcontext:
#             return json.dumps(
#                 {'error': qcontext.get('captcha_error', False), 'login_success': False})
#
#         response = super(AuthSignupHome, self).web_auth_signup(*args, **kw)
#         if request.httprequest.method == 'POST':
#             if response.is_qweb and response.qcontext.get('error', False):
#                 return json.dumps(
#                     {'error': response.qcontext.get('error', False), 'login_success': False})
#             else:
#                 return json.dumps({'redirect': '1', 'login_success': True})
#
#         return response


class WebsiteSnippetFilterEpt(Website):

    @http.route('/website/snippet/filters', type='json', auth='public', website=True)
    def get_dynamic_filter(self, filter_id, template_key, limit=None, search_domain=None, with_sample=False, **post):
        dynamic_filter = request.env['website.snippet.filter'].sudo().search(
            [('id', '=', filter_id)] + request.website.website_domain()
        )
        add2cart = post.get('product_context', {}).get('add2cart') == 'true'
        compare = post.get('product_context', {}).get('compare') == 'true'
        wishlist = post.get('product_context', {}).get('wishlist') == 'true'
        rating = post.get('product_context', {}).get('rating') == 'true'
        quickview = post.get('product_context', {}).get('quickview') == 'true'
        color_swatches = post.get('product_context', {}).get('color_swatches') == 'true'
        image_flipper = post.get('product_context', {}).get('image_flipper') == 'true'
        product_label = post.get('product_context', {}).get('product_label') == 'true'
        count = post.get('brand_context', {}).get('count') or post.get('category_context', {}).get('count') == 'true'
        return dynamic_filter and dynamic_filter.with_context(add2cart=add2cart, compare=compare, wishlist=wishlist,
                                                              rating=rating, quickview=quickview,
                                                              color_swatches=color_swatches,
                                                              image_flipper=image_flipper, product_label=product_label,
                                                              count=count)._render(template_key, limit, search_domain,
                                                                                   with_sample) or []


class WebsiteSaleWishlistEpt(WebsiteSaleWishlist):

    @http.route()
    def get_wishlist(self, count=False, **kw):
        """
        - Render collection of the current logged-in user
        - Filter out and render only wishes whose products are not available in the collections
        """
        res = super().get_wishlist(count=count, **kw)
        partner = request.env.user.sudo().partner_id
        collection_ids = request.env['wishlist.collection'].get_partner_collections(partner)
        if res.qcontext.get('wishes'):
            if collection_ids and collection_ids.product_line_ids:
                wishes = res.qcontext.get('wishes').filtered(
                    lambda
                        wish: wish.product_id.id not in collection_ids.product_line_ids.product_id.ids)
                res.qcontext['wishes'] = wishes
        res.qcontext['collections'] = collection_ids
        return res
