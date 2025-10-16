frappe.ui.form.on('Purchase Invoice', {
    onload(frm) {
        if (frm.doc.update_stock) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Warehouse",
                    filters: { "custom_is_default": 1},
                    fields: ["name"],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
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
            frm.set_value('set_warehouse', '');
            frm.refresh_field('set_warehouse');
        }
    }
});
