frappe.ui.form.on("Sales Order", {

    refresh: function(frm) {
        apply_uom_filter_for_all_rows(frm);
    },

    onload: function(frm) {
        apply_uom_filter_for_all_rows(frm);
    }
});


frappe.ui.form.on("Sales Order Item", {

    item_code: function (frm, cdt, cdn) {
        apply_uom_filter_for_row(frm, cdt, cdn);
    }
});


/* ============================================================
   COMMON FUNCTIONS
   ============================================================ */

// ✅ Apply filter for ONE ROW
function apply_uom_filter_for_row(frm, cdt, cdn) {

    let row = locals[cdt][cdn];
    if (!row.item_code) return;

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Item",
            name: row.item_code
        },
        callback: function (r) {

            if (r.message) {

                let allowed_uoms = [];

                // Stock UOM
                if (r.message.stock_uom) {
                    allowed_uoms.push(r.message.stock_uom);
                }

                // UOM table
                (r.message.uoms || []).forEach(d => {
                    if (d.uom && !allowed_uoms.includes(d.uom)) {
                        allowed_uoms.push(d.uom);
                    }
                });

                let grid_row = frm.fields_dict["items"].grid.grid_rows_by_docname[cdn];

                if (grid_row) {
                    grid_row.get_field("uom").get_query = function () {
                        return {
                            filters: [
                                ["UOM", "name", "in", allowed_uoms]
                            ]
                        };
                    };
                }

                // Reset invalid UOM
                if (row.uom && !allowed_uoms.includes(row.uom)) {
                    frappe.model.set_value(cdt, cdn, "uom", "");
                }

                frm.refresh_field("items");
            }
        }
    });
}


// ✅ Apply filter for ALL ROWS (important after save)
function apply_uom_filter_for_all_rows(frm) {

    (frm.doc.items || []).forEach(row => {
        apply_uom_filter_for_row(frm, row.doctype, row.name);
    });
}