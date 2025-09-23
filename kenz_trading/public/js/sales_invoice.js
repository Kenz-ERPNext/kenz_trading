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
        let row = locals[cdt][cdn];

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
    }
});