frappe.ui.form.on('Purchase Invoice', {
    update_stock: function(frm) {
        if (frm.doc.update_stock) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Warehouse",
                    filters: { "name": "Stores - A"},
                    fields: ["name"],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        // Warehouse exists, set it in the field
                        frm.set_value('set_warehouse', r.message[0].name);
                        frm.refresh_field('set_warehouse');
                        frappe.show_alert({
                            message: 'Warehouse set to: ' + r.message.name,
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint(__('Warehouse "Stores - A" not found.'));
                    }
                }
            });
        } else {
            // If checkbox unchecked, clear the warehouse
            frm.set_value('set_warehouse', '');
            frm.refresh_field('set_warehouse');
        }
    }
});


