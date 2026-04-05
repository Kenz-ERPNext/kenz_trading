

frappe.ui.form.on('Purchase Invoice', {

    refresh(frm) {
        load_item_uoms(frm);
        set_uom_query(frm);

        // Item search handled by monkey patch on erpnext.controllers.queries.item_query
    },

    items_on_form_rendered(frm) {
    },
    setup: function (frm) {
        frm.fields_dict["items"].grid.get_field("uom").get_query = function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.item_code && item_uoms[row.item_code]) {
                return {
                    filters: [["UOM", "name", "in", item_uoms[row.item_code]]]
                };
            } else {
                return {
                    filters: [["UOM", "name", "=", ""]]
                };
            }
        };
    },


    onload(frm) {
        load_item_uoms(frm);
        // Set default warehouse if update_stock is checked
        if (frm.doc.update_stock) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Warehouse",
                    filters: { "custom_is_default": 1 },
                    fields: ["name"],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('set_warehouse', r.message[0].name);
                    }
                }
            });
        } else {
            frm.set_value('set_warehouse', '');
        }
    },

    validate(frm) {
        // Set paid_amount only when saving
        if (frm.doc.is_paid && (!frm.doc.paid_amount || frm.doc.paid_amount == 0)) {
            frm.set_value('paid_amount', frm.doc.rounded_total || 0);
        }

        
    }

});



function load_item_uoms(frm) {
    (frm.doc.items || []).forEach(row => {
        if (row.item_code) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Item",
                    name: row.item_code
                },
                async: false, // IMPORTANT to ensure sync load
                callback: function (r) {
                    if (r.message) {
                        item_uoms[row.item_code] = (r.message.uoms || []).map(d => d.uom);
                    }
                }
            });
        }
    });
}



function set_uom_query(frm) {
    frm.fields_dict["items"].grid.get_field("uom").get_query = function (doc, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.item_code && item_uoms[row.item_code]) {
            return {
                filters: [
                    ["UOM", "name", "in", item_uoms[row.item_code]]
                ]
            };
        } else {
            return {
                filters: [
                    ["UOM", "name", "=", ""]
                ]
            };
        }
    };
}

let item_uoms = {};

frappe.ui.form.on("Purchase Invoice Item", {

    item_code(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Item",
                name: row.item_code
            },
            callback: function (r) {
                if (r.message) {

                    let allowed_uoms = (r.message.uoms || []).map(d => d.uom);
                    item_uoms[row.item_code] = allowed_uoms;

                    // Reset invalid UOM
                    if (row.uom && !allowed_uoms.includes(row.uom)) {
                        frappe.model.set_value(cdt, cdn, "uom", "");
                    }

                    frm.refresh_field("items");
                }
            }
        });
    }
});


// =============================================
// PURCHASE INVOICE ITEM SEARCH - Show All Items
// =============================================

// Item search handled by monkey patch on erpnext.controllers.queries.item_query