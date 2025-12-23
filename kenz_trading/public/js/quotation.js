

// frappe.ui.form.on("Quotation", {

//     refresh(frm) {

//         // frappe.msgprint("hiii")
//         if (frm.doc.docstatus === 1) {
//             frm.add_custom_button(
//                 __("Sales Invoice"),
//                 function () {
//                     frappe.call({
//                         method: "kenz_trading.events.quotation.make_sales_invoice",
//                         args: {
//                             quotation: frm.doc.name
//                         },
//                         callback: function (r) {
//                             if (r.message) {
//                                 frappe.model.sync(r.message);
//                                 frappe.set_route("Form", r.message.doctype, r.message.name);
//                             }
//                         }
//                     });
//                 },
//                 __("Create")
//             );
//         }
//     }
// });


frappe.ui.form.on("Quotation", {
    refresh(frm) {

        // only for submitted quotation
        if (frm.doc.docstatus !== 1) return;

        // get checkbox value from Kenza Settings (Single Doctype)
        frappe.db.get_single_value(
            "Kenza Settings",
            "enable_create_sales_invoice"
        ).then((enabled) => {

            // show button only if checkbox is enabled
            if (enabled) {
                frm.add_custom_button(
                    __("Sales Invoice"),
                    function () {
                        frappe.call({
                            method: "kenz_trading.events.quotation.make_sales_invoice",
                            args: {
                                quotation: frm.doc.name
                            },
                            callback: function (r) {
                                if (r.message) {
                                    frappe.model.sync(r.message);
                                    frappe.set_route(
                                        "Form",
                                        r.message.doctype,
                                        r.message.name
                                    );
                                }
                            }
                        });
                    },
                    __("Create")
                );
            }
        });
    }
});
