// frappe.ui.form.on('Purchase Invoice', {
//     onload(frm) {
//         if (frm.doc.update_stock) {
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Warehouse",
//                     filters: { "custom_is_default": 1},
//                     fields: ["name"],
//                     limit_page_length: 1
//                 },
//                 callback: function(r) {
//                     if (r.message && r.message.length > 0) {
//                         frm.set_value('set_warehouse', r.message[0].name);
//                         frm.refresh_field('set_warehouse');
//                         frappe.show_alert({
//                             message: 'Warehouse set to: ' + r.message.name,
//                             indicator: 'green'
//                         });
//                     } else {
//                         frappe.msgprint(__('Warehouse "Stores - A" not found.'));
//                     }
//                 }
//             });
//         } else {
//             frm.set_value('set_warehouse', '');
//             frm.refresh_field('set_warehouse');
//         }
//     }
// });



frappe.ui.form.on('Purchase Invoice', {
    onload(frm) {
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
                        frm.refresh_field('set_warehouse');
                        frappe.show_alert({
                            message: 'Warehouse set to: ' + r.message[0].name,
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint(__('Warehouse "Stores - A" not found.'));
                    }
                }
            });
        } else {
            frm.set_value('set_warehouse', '');
            frm.refresh_field('set_warehouse');
        }

        // Set paid_amount if invoice is marked as paid
        if (frm.doc.is_paid) {
            frm.set_value('paid_amount', frm.doc.rounded_total || 0);
            frm.refresh_field('paid_amount');
        }
    }
});
