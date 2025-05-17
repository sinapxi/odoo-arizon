/** @odoo-modules **/

import { _t } from "@web/core/l10n/translation";
import weSnippetEditor from "@website/js/editor/snippets.editor";
import weSnippetEditorr from "@web_editor/js/editor/snippets.editor";
import wSnippetOptions from "@website/js/editor/snippets.options";
import { Component, onMounted, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";


import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { throttleForAnimation } from "@web/core/utils/timing";
import { switchTextHighlight } from "@website/js/text_processing";
import { registry } from "@web/core/registry";

patch(weSnippetEditor.SnippetsMenu, {
    OptionsTabStructureEpt : [
        ['general-settings-ept', _t("General Settings")],
        ['shop-page-ept', _t("Shop Page")],
        ['product-page-ept', _t("Product Page")],
        ['cart-page-ept', _t("cart Page")],
    ],
    tabs : {
        ...weSnippetEditor.SnippetsMenu.tabs,
        THEME_EPT: 'theme-ept',
    },
    template : "theme_clarico_vega.SnippetsMenu",
});

patch(weSnippetEditor.SnippetsMenu.prototype, {
    setup() {
        super.setup();
    },
    async _onThemeTabClickEpt(ev) {
        let releaseLoader;
        try {
            const promise = new Promise(resolve => releaseLoader = resolve);
            this._execWithLoadingEffect(() => promise, false, 400);
            // loader is added to the DOM synchronously
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            // ensure loader is rendered: first call asks for the (already done) DOM update,
            // second call happens only after rendering the first "updates"
            if (!this.topFakeOptionElEpt) {
                let el;
                for (const [elementName, title] of weSnippetEditor.SnippetsMenu.OptionsTabStructureEpt) {
                    const newEl = document.createElement(elementName);
                    newEl.dataset.name = title;
                    if (el) {
                        el.appendChild(newEl);
                    } else {
                        this.topFakeOptionElEpt = newEl;
                    }
                    el = newEl;
                }
                this.bottomFakeOptionElEpt = el;
                this.el.appendChild(this.topFakeOptionElEpt);
            }

            // Need all of this in that order so that:
            // - the element is visible and can be enabled and the onFocus method is
            //   called each time.
            // - the element is hidden afterwards so it does not take space in the
            //   DOM, same as the overlay which may make a scrollbar appear.
            this.bottomFakeOptionElEpt.classList.remove('d-none');
            const editorPromise = this._activateSnippet($(this.bottomFakeOptionElEpt));
            // Because _activateSnippet uses the same mutex as the loader
            releaseLoader();
            releaseLoader = undefined;
            const editor = await editorPromise;
            this.bottomFakeOptionElEpt.classList.add('d-none');
//            editor.toggleOverlay(false);
            this._updateRightPanelContent({
                tab: weSnippetEditor.SnippetsMenu.tabs.THEME_EPT,
            });
        } catch (e) {
            // Normally the loading effect is removed in case of error during the action but here
            // the actual activity is happening outside of the action, the effect must therefore
            // be cleared in case of error as well
            if (releaseLoader) {
                releaseLoader();
            }
            throw e;
        }
    },
});
