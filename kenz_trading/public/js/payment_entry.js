frappe.ui.form.on("Payment Entry", {
    refresh(frm) {
        if (frm.doc.mode_of_payment === "Cash") {
            frm.set_value("reference_no", "Cash");
            frm.set_value("reference_date", frappe.datetime.get_today());
        } 
    },

    mode_of_payment(frm) {
        if (frm.doc.mode_of_payment === "Cash") {
            frm.set_value("reference_no", "Cash");
            frm.set_value("reference_date", frappe.datetime.get_today());
        } 
    }
});