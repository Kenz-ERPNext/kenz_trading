// frappe.listview_settings["Sales Invoice"] = {
//     onload: function(listview) {

//         listview.page.add_inner_button("Bulk Print Separate", function() {

//             let filters = listview.get_filters_for_args();

//             frappe.call({
//                 method: "kenz_trading.api.bulk_print.bulk_print_sales_invoice",
//                 args: { filters: filters },
//                 freeze: true,
//                 freeze_message: __("Preparing ZIP file... Please wait..."),
//                 callback: function(r) {

//                     if (r.message) {

//                         let url = r.message;

//                         // Force download
//                         let link = document.createElement("a");
//                         link.href = url;
//                         link.download = "";
//                         document.body.appendChild(link);
//                         link.click();
//                         document.body.removeChild(link);

//                         frappe.show_alert({
//                             message: __("Download Ready"),
//                             indicator: "green"
//                         });
//                     } else {
//                         frappe.msgprint("No file returned from server.");
//                     }
//                 }
//             });

//         });
//     }
// };





frappe.listview_settings["Sales Invoice"] = {
    onload: function(listview) {

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Kenza Settings",
                fieldname: "enable_bulk_edit"
            },
            callback: function(r) {

                if (r.message && r.message.enable_bulk_edit) {

                    listview.page.add_inner_button("Bulk Print Separate", function() {

                        let filters = listview.get_filters_for_args();

                        frappe.call({
                            method: "kenz_trading.api.bulk_print.bulk_print_sales_invoice",
                            args: { filters: filters },
                            freeze: true,
                            freeze_message: __("Preparing ZIP file... Please wait..."),
                            callback: function(r) {

                                if (r.message) {

                                    let link = document.createElement("a");
                                    link.href = r.message;
                                    link.download = "";
                                    document.body.appendChild(link);
                                    link.click();
                                    document.body.removeChild(link);

                                    frappe.show_alert({
                                        message: __("Download Ready"),
                                        indicator: "green"
                                    });

                                } else {
                                    frappe.msgprint("No file returned from server.");
                                }
                            }
                        });

                    });

                }
            }
        });

    }
};