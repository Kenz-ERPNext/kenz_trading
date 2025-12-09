// Copyright (c) 2025, TBO and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Kenza Settings", {
// 	refresh(frm) {

// 	},
// });
 
frappe.ui.form.on("Kenza Settings", {
    refresh: function(frm) {
        frm.add_custom_button("Delete All Projects & Tasks", function () {

            frappe.confirm(
                "Are you sure you want to delete ALL Projects and ALL Tasks?<br><br><b>This action cannot be undone.</b>",
                
                function () {
                    // YES
                    cur_frm.call({
			            doc: cur_frm.doc,
                        method: "delete_all_projects_and_tasks",
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(r.message);
                            }
                        }
                    });
                },

                function () {
                    // NO → nothing
                }
            );

        }).addClass("btn-danger");
    }
});
