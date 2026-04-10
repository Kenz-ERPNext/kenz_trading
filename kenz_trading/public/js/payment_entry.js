frappe.ui.form.on("Payment Entry", {
    refresh(frm) {
        if (frm.doc.mode_of_payment === "Cash") {
            frm.set_value("reference_no", "Cash");
            frm.set_value("reference_date", frappe.datetime.get_today());
        } else {
            // Optional: clear values if not cash
            frm.set_value("reference_no", "");
            frm.set_value("reference_date", "");
        }
        // console.log("Payment Entry JS Loaded");
        // frappe.msgprint("hii");
    },

    mode_of_payment(frm) {
        if (frm.doc.mode_of_payment === "Cash") {
            frm.set_value("reference_no", "Cash");
            frm.set_value("reference_date", frappe.datetime.get_today());
        } else {
            // Optional: clear values if not cash
            frm.set_value("reference_no", "");
            frm.set_value("reference_date", "");
        }
    }
});