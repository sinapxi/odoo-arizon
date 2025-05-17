/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
var registry = publicWidget.registry;
import { _lt, _t } from "@web/core/l10n/translation";

registry.SimilarProductView = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .te_similar_view': '_initSimilarProductView',
    },

    _initSimilarProductView: async function (ev) {
        ev.preventDefault();
        self = this;
        var element = ev.currentTarget;
        var product_id = $(element).attr('data-id');
        var params = {
            'product_id': product_id,
        }

        self = await $.get('/similar_products_item_data', params).then(function (data) {
           $("#similaroffcanvasWithBackdrop .offcanvas-body").html(data);
        });
    }
});