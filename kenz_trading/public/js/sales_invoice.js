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



// frappe.ui.form.on("Sales Invoice Item", {
//     item_code: function(frm, cdt, cdn) {
//         var row = locals[cdt][cdn];
//         if (row.item_code) {
//             frm.set_query("uom", cdt, function() {
//                 return {
//                     query: "kenz_trading.events.item.get_item_uoms",
//                     filters: {
//                         "item_code": row.item_code
//                     }
//                 };
//             });
//         }
//         console.log("UOM filter applied for item:", row.item_code);
//     },
// });