


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

// Ensure the status indicator (Paid / Return / Credit Note Issued / Unpaid / Overdue ...)
// is present even when this script bundles ahead of ERPNext's standard list config.
// Without this, the list falls back to the docstatus indicator and shows everything as "Submitted".
const _kenz_si_status_colors = {
    Draft: "red",
    Unpaid: "orange",
    Paid: "green",
    Return: "gray",
    "Credit Note Issued": "gray",
    "Unpaid and Discounted": "orange",
    "Partly Paid and Discounted": "yellow",
    "Overdue and Discounted": "red",
    Overdue: "red",
    "Partly Paid": "yellow",
    "Internal Transfer": "darkgrey",
};

if (!frappe.listview_settings["Sales Invoice"].get_indicator) {
    frappe.listview_settings["Sales Invoice"].get_indicator = function (doc) {
        return [__(doc.status), _kenz_si_status_colors[doc.status] || "blue", "status,=," + doc.status];
    };
}

const _kenz_si_extra_fields = ["status", "outstanding_amount", "is_return", "currency", "due_date", "customer_name"];
frappe.listview_settings["Sales Invoice"].add_fields = Array.from(new Set([
    ...(frappe.listview_settings["Sales Invoice"].add_fields || []),
    ..._kenz_si_extra_fields,
]));

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