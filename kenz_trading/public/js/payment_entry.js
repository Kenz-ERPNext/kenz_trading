


// frappe.ui.form.on("Payment Entry", {
//     refresh(frm) {
//         set_cash_defaults(frm);
//     },

//     mode_of_payment(frm) {
//         set_cash_defaults(frm);
//     }
// });

// function set_cash_defaults(frm) {
//     if (frm.doc.mode_of_payment === "Cash") {

//         // Set reference_no only if empty
//         if (!frm.doc.reference_no) {
//             frm.set_value("reference_no", "Cash");
//         }

//         // Set reference_date only if empty
//         if (!frm.doc.reference_date) {
//             frm.set_value("reference_date", frappe.datetime.get_today());
//         }
//     }
// }