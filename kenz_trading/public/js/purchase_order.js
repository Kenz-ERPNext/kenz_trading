frappe.ui.form.on("Purchase Order", {

    refresh(frm) {
        // Customize item field to show all items
        customize_po_item_field(frm);
    },

    items_on_form_rendered(frm) {
        customize_po_item_field(frm);
    },
});


// =============================================
// PURCHASE ORDER ITEM SEARCH - Show All Items
// =============================================

function customize_po_item_field(frm) {
    setTimeout(() => {
        let items_grid = frm.fields_dict.items.grid;
        if (items_grid) {
            let item_field = items_grid.get_field('item_code');

            if (item_field) {
                item_field.get_query = function(doc, cdt, cdn) {
                    return {
                        query: "kenz_trading.events.sales_invoice.get_all_sales_items_for_link_field",
                        page_len: 1000
                    };
                };

                if (item_field.df) {
                    item_field.df.page_len = 1000;
                }
            }

            if (items_grid.grid_form && items_grid.grid_form.fields_dict.item_code) {
                items_grid.grid_form.fields_dict.item_code.get_query = function(doc, cdt, cdn) {
                    return {
                        query: "kenz_trading.events.sales_invoice.get_all_sales_items_for_link_field",
                        page_len: 1000
                    };
                };
            }
        }
    }, 1000);

    setTimeout(() => {
        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            let original_add_new_row = frm.fields_dict.items.grid.add_new_row;
            frm.fields_dict.items.grid.add_new_row = function(idx, callback, show) {
                let result = original_add_new_row.call(this, idx, callback, show);

                setTimeout(() => {
                    let item_field = this.get_field('item_code');
                    if (item_field) {
                        item_field.get_query = function(doc, cdt, cdn) {
                            return {
                                query: "kenz_trading.events.sales_invoice.get_all_sales_items_for_link_field",
                                page_len: 1000
                            };
                        };

                        if (item_field.df) {
                            item_field.df.page_len = 1000;
                        }
                    }
                }, 500);

                return result;
            };
        }
    }, 1500);
}
