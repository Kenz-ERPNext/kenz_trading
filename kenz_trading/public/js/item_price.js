frappe.ui.form.on('Item Price', {

    refresh(frm){
        // frappe.msgprint("hii")

    },


    item_code(frm) {
        frm.set_value("uom", null);

        if (!frm.doc.item_code) return;

        frappe.db.get_doc("Item", frm.doc.item_code).then(item => {
            let uoms = [];

            // Stock UOM
            if (item.stock_uom) {
                uoms.push(item.stock_uom);
            }

            // Conversion UOMs
            (item.uoms || []).forEach(row => {
                if (row.uom) {
                    uoms.push(row.uom);
                }
            });

            frm.set_query("uom", () => {
                return {
                    filters: {
                        name: ["in", uoms]
                    }
                };
            });
        });
    }
});
