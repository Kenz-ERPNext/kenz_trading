frappe.ui.form.on("Purchase Order", {
    onload(frm) {

        frm.fields_dict["items"].grid.get_field("uom").get_query = function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];

            if (!row.item_code) {
                return {};
            }

            return {
                query: "kenz_trading.events.purchase_order.get_item_uoms",
                filters: {
                    item_code: row.item_code
                }
            };
        };

    }
});