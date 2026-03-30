

frappe.ui.form.on("Customer", {
    
    // custom_vat_registration_number: function (frm) {
    //     let vat = frm.doc.custom_vat_registration_number;
    //     if (vat) {
    //         // 1️⃣ Set tax_id
    //         frm.set_value("tax_id", vat);

    //         // 2️⃣ Update / Insert TIN in custom_additional_ids
    //         let found = false;
    //         (frm.doc.custom_additional_ids || []).forEach(row => {
    //             if (row.type_name === "Tax Identification Number" && row.type_code === "TIN") {
    //                 row.value = vat;
    //                 found = true;
    //             }
    //         });
    //         if (!found) {
    //             let row = frm.add_child("custom_additional_ids");
    //             row.type_name = "Tax Identification Number";
    //             row.type_code = "TIN";
    //             row.value = vat;
    //         }
    //     }
    //     frm.refresh_field("custom_additional_ids");
    // },

    custom_cr_no: function (frm) {
        let cr = frm.doc.custom_cr_no;
        if (cr) {
            // Update / Insert CRN in custom_additional_ids
            let found = false;
            (frm.doc.custom_additional_ids || []).forEach(row => {
                if (row.type_name === "Commercial Registration Number" && row.type_code === "CRN") {
                    row.value = cr;
                    found = true;
                }
            });
            if (!found) {
                let row = frm.add_child("custom_additional_ids");
                row.type_name = "Commercial Registration Number";
                row.type_code = "CRN";
                row.value = cr;
            }
        }
        frm.refresh_field("custom_additional_ids");
    },

    refresh: function (frm) {
        // Sync on load
        if (frm.doc.custom_vat_registration_number && !frm.doc.tax_id) {
            frm.trigger("custom_vat_registration_number");
        }
        if (frm.doc.custom_cr_no) {
            frm.trigger("custom_cr_no");
        }
    }
});
