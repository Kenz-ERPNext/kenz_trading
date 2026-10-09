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
    },

    // Typing a Tax ID picks the supplier that has it. Selecting a supplier also fetches
    // its tax_id into this field, so skip when the current supplier already matches.
    tax_id(frm) {
        const tax_id = (frm.doc.tax_id || '').trim();
        if (!tax_id) return;
        frappe.db.get_list('Supplier', {
            filters: { tax_id: tax_id, disabled: 0 },
            fields: ['name'],
            limit: 0
        }).then((suppliers) => {
            const names = suppliers.map((s) => s.name);
            if (names.includes(frm.doc.supplier)) return;
            if (!names.length) {
                frappe.msgprint(__('No supplier found with Tax ID {0}', [tax_id]));
            } else {
                frm.set_value('supplier', names[0]);
            }
        });
    }
});
