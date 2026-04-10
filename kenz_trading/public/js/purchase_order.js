frappe.ui.form.on("Purchase Order", {

    refresh(frm) {
        // Item search handled by monkey patch on erpnext.controllers.queries.item_query
    },

    items_on_form_rendered(frm) {
    },
});
