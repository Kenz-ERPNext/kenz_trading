let item_uoms = {};
frappe.ui.form.on("Sales Invoice", { 
    custom_payment_mode: function (frm) {
        set_pos_value(frm);
    },
    customer: function (frm) {
        frm.set_value("custom_session_user", frappe.session.user);
        default_branch(frm)
    },
    

});

function set_pos_value(frm) {
    if (frm.doc.custom_payment_mode === "Credit") {
        frm.set_value("is_pos", 0);
    } else {
        frm.set_value("is_pos", 1);
    }
}

function default_branch(frm) {
    frappe.call({
        method: "kenz_trading.events.sales_invoice.get_default_branch",
        args: {
            user: frappe.session.user,
            
        },
        callback: function (r) {
            if (r.message) {
                frm.set_value("branch", r.message);
            }
        },
    });
}

frappe.ui.form.on("Sales Invoice Item", {
    item_code: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if (row.item_code) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Item",
                    name: row.item_code
                },
                callback: function (r) {
                    if (r.message) {
                        let allowed_uoms = (r.message.uoms || []).map(u => u.uom);

                        frm.fields_dict["items"].grid.get_field("uom").get_query = function (doc, cdt2, cdn2) {
                            let d = locals[cdt2][cdn2];
                            if (d.item_code === row.item_code) {
                                return {
                                    filters: [["UOM", "name", "in", allowed_uoms]]
                                };
                            }
                        };

                        frm.refresh_field("items");
                    }
                }
            });
        }


        if (row.item_code) {
            // Fetch the price_list_rate from Item Price doctypePurchase Order
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Item Price',
                    filters: {
                        item_code: row.item_code,
                        price_list: frm.doc.selling_price_list || "Standard Selling"
                    },
                    fields: ['price_list_rate']
                },
                callback: function(price_data) {
                    let price_list_rate = price_data.message?.[0]?.price_list_rate || "not available";

                    // Fetch actual quantity from the Bin doctype
                    frappe.call({
                        method: 'frappe.client.get_value',
                        args: {
                            doctype: 'Bin',
                            filters: {

                                item_code: row.item_code,
                                warehouse: row.warehouse
                            },
                            fieldname: 'actual_qty'
                        },
                        callback: function(stock_data) {
                            let actual_qty = stock_data.message?.actual_qty || 0;

                            // Display a combined message for both values
                            frappe.msgprint(
                                `Available quantity for item ${row.item_code} is ${actual_qty}.<br>
                                Price List Rate: ${price_list_rate}`
                            );
                        }
                    });
                }
            });
        }
    }
});