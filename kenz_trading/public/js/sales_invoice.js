frappe.ui.form.on("Sales Invoice", { 
    custom_payment_mode: function (frm) {
        console.log("Custom Payment Mode changed:", frm.doc.custom_payment_mode);   
        if (frm.doc.custom_payment_mode === "Credit") {
            frm.set_value("is_pos", 0);
        } else {
            frm.set_value("is_pos", 1);
        }
    }
});
