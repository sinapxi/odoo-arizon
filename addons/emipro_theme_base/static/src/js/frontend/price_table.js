/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { cookie } from "@web/core/browser/cookie";

WebsiteSale.include({

    events: Object.assign(WebsiteSale.prototype.events, {
//        'click .price_rule_box': 'setQty',
        'click .cart_line .js_add_cart_json': '_onChangeCartQuantity',
        'change .cart_line input.js_quantity[data-product-id]': '_onChangeCartQuantity',
        'click .cart_line .js_delete_product': '_onClickRemoveItem',
    }),

//    setQty: function(ev) {
//        const self = ev.currentTarget;
//        const qty = $(self).attr('qty');
//        if(qty !== undefined && qty >= 1){
//            var qty_box = $(self).closest('#product_details').find("input[type='text'][name='add_qty']");
//            if(qty_box !== undefined){
//                qty_box.val(qty);
//                this._getCombinationInfo(ev);
//                cookie.set('selected_offer',$(self).attr('qty'));
//                setTimeout(function() {
//                    var content = $('.table_content');
//                    for(var i=0;i<content.length;i++){
//                        $(content[i]).removeClass('active');
//                        $(content[i]).find('i').addClass('d-none');
//                        if($(content[i]).attr('qty') == cookie.get('selected_offer')){
//                            $(content[i]).addClass('active');
//                            $(content[i]).find('i').removeClass('d-none');
//                        }
//                    }
//                }, 500);
//            }
//        }
//    },
    _onChangeCartQuantity: function (ev) {
        var $input = $(ev.currentTarget.offsetParent).find('.js_quantity');
        if ($input.data('update_change')) {
            return;
        }
        var value = parseInt($input.val() || 0, 10);
        if (isNaN(value)) {
            value = 1;
        }
        var $dom = $input.closest('.cart_line');
        // var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
        var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
        var line_id = parseInt($input.data('line-id'), 10);
        var productIDs = [parseInt($input.data('product-id'), 10)];
        // Applied changes for update/add quantity on cart popover
        if ( $input.val() == 0 && !$input.data('update_change') ){
            $input.data('update_change', true);
            $dom.find('.js_quantity').val(0).trigger('change');
            $dom.remove();
        }
        if (line_id && productIDs){
            this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
            this._onClickFreeShipTextUpdate(ev);
        }
    },
    _onClickRemoveItem: function(ev){
        $(ev.currentTarget).parent().siblings().find('.js_quantity').val(0).trigger('change');
        $(ev.currentTarget).parent().parent().remove();
        this._onClickFreeShipTextUpdate(ev);
    },
    _onClickFreeShipTextUpdate: function(ev){
        setTimeout(function(){
            var $order_total_price = parseFloat($('#order_total .oe_currency_value').text().replace(/[^0-9.]/g, ''));
            var $offer_cart_price = parseFloat($('.offer_price').text().replace(/[^0-9.]/g, ''));
            var result = $order_total_price - $offer_cart_price;
            /*Progress bar design*/
            var progressPercent = Math.min(($order_total_price / $offer_cart_price) * 100, 100);

            if($order_total_price < $offer_cart_price) {
                $('.main_free_ship_data .oe_currency_value').text(Math.abs(result).toFixed(2));
                $('.not_free_ship_text').removeClass('d-none');
                $('.final_msg_ship').addClass('d-none');
                $('.first_main_freeship_price').removeClass('d-none');
                $('.free_ship_not_added').removeClass('d-none');
                $('.progress-fill').css('width', `${progressPercent}%`);
                $('.progress-percentage').text(`${Math.floor(progressPercent)}%`);
            }
            else{
                $('.main_free_ship_data .oe_currency_value').text('0');
                $('.not_free_ship_text').addClass('d-none');
                $('.final_msg_ship').removeClass('d-none');
                $('.first_main_freeship_price').addClass('d-none');
                $('.free_ship_not_added').addClass('d-none');
                $('.progress-fill').css('width', `${progressPercent}%`);
                $('.progress-percentage').text(`${Math.floor(progressPercent)}%`);
            }
        }, 2000);
    },
});
