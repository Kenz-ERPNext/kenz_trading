// Copyright (c) 2025, TBO and contributors
// For license information, please see license.txt

 

frappe.ui.form.on("Kenza Settings", {
	refresh(frm) {

	},

    create_tax_category: function(frm) {

        cur_frm.call({
                    doc: cur_frm.doc,
                    method: "create_tc",
                    args: {},
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Tax Category Created: <b>" + r.message + "</b>");
                        }
                    }
                });
           
    },

    create_tax_template: function(frm) {

        cur_frm.call({
                    doc: cur_frm.doc,
                    method: "create_tt",
                    args: {},
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Tax Template Created: <b>" + r.message + "</b>");
                        }
                    }
                });
           
    },

    create_template__account_head: function(frm) {

        cur_frm.call({
                    doc: cur_frm.doc,
                    method: "create_ah",
                    args: {},
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Account Head Created: <b>" + r.message + "</b>");
                        }
                    }
                });
           
    },
}); 
