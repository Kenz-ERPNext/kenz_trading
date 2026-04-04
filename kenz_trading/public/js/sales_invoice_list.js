


// if (!frappe.listview_settings["Sales Invoice"]) {
//     frappe.listview_settings["Sales Invoice"] = {};
// }

// frappe.listview_settings["Sales Invoice"].onload = function(listview) {

//     frappe.db.get_single_value("Kenza Settings", "enable_bulk_edit").then(value => {

//         if (value) {

//             listview.page.add_inner_button("Bulk Print Preview", function() {

//                 let d = new frappe.ui.Dialog({
//                     title: "Select Print Format",
//                     fields: [
//                         {
//                             label: "Print Format",
//                             fieldname: "print_format",
//                             fieldtype: "Link",
//                             options: "Print Format",
//                             reqd: 1,
//                             get_query: function () {
//                                 return {
//                                     filters: {
//                                         doc_type: "Sales Invoice"
//                                     }
//                                 };
//                             }
//                         }
//                     ],
//                     primary_action_label: "Print",
//                     primary_action(values) {

//                         let selected_format = values.print_format;
//                         d.hide();

//                         let filters = listview.get_filters_for_args();

//                         frappe.call({
//                             method: "kenz_trading.api.bulk_print.get_sales_invoice_names",
//                             args: { filters: filters },
//                             freeze: true,
//                             freeze_message: __("Preparing Combined PDF... Please wait..."),
//                             callback: function(res) {

//                                 if (res.message && res.message.length) {

//                                     let names = res.message;

//                                     window.open(
//                                         frappe.urllib.get_full_url(
//                                             "/api/method/frappe.utils.print_format.download_multi_pdf?"
//                                             + "doctype=Sales Invoice"
//                                             + "&name=" + JSON.stringify(names)
//                                             + "&format=" + selected_format
//                                             + "&no_letterhead=0"
//                                         )
//                                     );

//                                 } else {
//                                     frappe.msgprint("No Submitted Sales Invoices found.");
//                                 }
//                             }
//                         });

//                     }
//                 });

//                 d.show();

//             });

//         }

//     });

// };




frappe.listview_settings["Sales Invoice"] = frappe.listview_settings["Sales Invoice"] || {};

let original_onload = frappe.listview_settings["Sales Invoice"].onload;

frappe.listview_settings["Sales Invoice"].onload = function(listview) {

    // 🔁 Call original ERPNext onload (THIS IS THE FIX)
    if (original_onload) {
        original_onload(listview);
    }

    // ✅ Your custom logic
    frappe.db.get_single_value("Kenza Settings", "enable_bulk_edit").then(value => {

        if (value) {

            listview.page.add_inner_button("Bulk Print Preview", function() {

                let d = new frappe.ui.Dialog({
                    title: "Select Print Format",
                    fields: [
                        {
                            label: "Print Format",
                            fieldname: "print_format",
                            fieldtype: "Link",
                            options: "Print Format",
                            reqd: 1,
                            get_query: function () {
                                return {
                                    filters: {
                                        doc_type: "Sales Invoice"
                                    }
                                };
                            }
                        }
                    ],
                    primary_action_label: "Print",
                    primary_action(values) {

                        let selected_format = values.print_format;
                        d.hide();

                        let filters = listview.get_filters_for_args();

                        frappe.call({
                            method: "kenz_trading.api.bulk_print.get_sales_invoice_names",
                            args: { filters: filters },
                            freeze: true,
                            freeze_message: __("Preparing Combined PDF... Please wait..."),
                            callback: function(res) {

                                if (res.message && res.message.length) {

                                    let names = res.message;

                                    window.open(
                                        frappe.urllib.get_full_url(
                                            "/api/method/frappe.utils.print_format.download_multi_pdf?"
                                            + "doctype=Sales Invoice"
                                            + "&name=" + JSON.stringify(names)
                                            + "&format=" + selected_format
                                            + "&no_letterhead=0"
                                        )
                                    );

                                } else {
                                    frappe.msgprint("No Submitted Sales Invoices found.");
                                }
                            }
                        });

                    }
                });

                d.show();

            });

        }

    });

};