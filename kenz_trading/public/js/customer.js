

function is_valid(val) {
    return val && val.trim() !== "" && val.trim().toUpperCase() !== "NULL";
}

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
        if (is_valid(cr)) {
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
        // Clean "NULL" strings from fields on load
        if (!is_valid(frm.doc.custom_vat_registration_number)) {
            if (frm.doc.custom_vat_registration_number && frm.doc.custom_vat_registration_number.trim().toUpperCase() === "NULL") {
                frm.set_value("custom_vat_registration_number", "");
            }
        }
        if (!is_valid(frm.doc.tax_id)) {
            if (frm.doc.tax_id && frm.doc.tax_id.trim().toUpperCase() === "NULL") {
                frm.set_value("tax_id", "");
            }
        }
        if (!is_valid(frm.doc.custom_cr_no)) {
            if (frm.doc.custom_cr_no && frm.doc.custom_cr_no.trim().toUpperCase() === "NULL") {
                frm.set_value("custom_cr_no", "");
            }
        }

        // Clean "NULL" from Additional IDs rows
        let dirty = false;
        (frm.doc.custom_additional_ids || []).forEach(row => {
            if (row.value && row.value.trim().toUpperCase() === "NULL") {
                row.value = "";
                dirty = true;
            }
        });
        if (dirty) {
            frm.refresh_field("custom_additional_ids");
        }

        // Sync on load only if values are valid
        if (is_valid(frm.doc.custom_vat_registration_number) && !frm.doc.tax_id) {
            frm.trigger("custom_vat_registration_number");
        }
        if (is_valid(frm.doc.custom_cr_no)) {
            frm.trigger("custom_cr_no");
        }
    }
});
