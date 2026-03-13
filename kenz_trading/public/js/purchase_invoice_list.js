


// frappe.listview_settings["Purchase Invoice"] = {



    
//     onload: function(listview) {

//         frappe.db.get_single_value("Kenza Settings", "enable_bulk_edit").then(value => {

//             if (value) {

//                 listview.page.add_inner_button("Bulk Print Preview", function() {

//                     let d = new frappe.ui.Dialog({
//                         title: "Select Print Format",
//                         fields: [
//                             {
//                                 label: "Print Format",
//                                 fieldname: "print_format",
//                                 fieldtype: "Link",
//                                 options: "Print Format",
//                                 reqd: 1,
//                                 get_query: function () {
//                                     return {
//                                         filters: {
//                                             doc_type: "Purchase Invoice"
//                                         }
//                                     };
//                                 }
//                             }
//                         ],
//                         primary_action_label: "Print",
//                         primary_action(values) {

//                             let selected_format = values.print_format;

//                             d.hide();

//                             let filters = listview.get_filters_for_args();

//                             frappe.call({
//                                 method: "kenz_trading.api.bulk_print.get_purchase_invoice_names",
//                                 args: { filters: filters },
//                                 freeze: true,
//                                 freeze_message: __("Preparing Combined PDF... Please wait..."),
//                                 callback: function(res) {

//                                     if (res.message && res.message.length) {

//                                         let names = res.message;

//                                         window.open(
//                                             frappe.urllib.get_full_url(
//                                                 "/api/method/frappe.utils.print_format.download_multi_pdf?"
//                                                 + "doctype=Purchase Invoice"
//                                                 + "&name=" + JSON.stringify(names)
//                                                 + "&format=" + selected_format
//                                                 + "&no_letterhead=0"
//                                             )
//                                         );

//                                     } else {
//                                         frappe.msgprint("No Submitted Purchase Invoices found.");
//                                     }
//                                 }
//                             });

//                         }
//                     });

//                     d.show();

//                 });

//             }

//         });

//     }
// };






if (!frappe.listview_settings["Purchase Invoice"]) {
    frappe.listview_settings["Purchase Invoice"] = {};
}

frappe.listview_settings["Purchase Invoice"].onload = function(listview) {

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
                                        doc_type: "Purchase Invoice"
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
                            method: "kenz_trading.api.bulk_print.get_purchase_invoice_names",
                            args: { filters: filters },
                            freeze: true,
                            freeze_message: __("Preparing Combined PDF... Please wait..."),
                            callback: function(res) {

                                if (res.message && res.message.length) {

                                    let names = res.message;

                                    window.open(
                                        frappe.urllib.get_full_url(
                                            "/api/method/frappe.utils.print_format.download_multi_pdf?"
                                            + "doctype=Purchase Invoice"
                                            + "&name=" + JSON.stringify(names)
                                            + "&format=" + selected_format
                                            + "&no_letterhead=0"
                                        )
                                    );

                                } else {
                                    frappe.msgprint("No Submitted Purchase Invoices found.");
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