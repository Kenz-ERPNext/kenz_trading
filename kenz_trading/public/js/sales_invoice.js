frappe.ui.form.on("Sales Invoice", { 
    custom_payment_mode: function (frm) {
        set_pos_value(frm);
    },
    customer: function (frm) {
        frm.set_value("custom_session_user", frappe.session.user);
    },

});

function set_pos_value(frm) {
    if (frm.doc.custom_payment_mode === "Credit") {
        frm.set_value("is_pos", 0);
    } else {
        frm.set_value("is_pos", 1);
    }
}
