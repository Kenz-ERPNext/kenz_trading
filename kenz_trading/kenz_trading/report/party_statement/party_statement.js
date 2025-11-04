// Copyright (c) 2025, TBO and contributors
// For license information, please see license.txt

frappe.query_reports["Party Statement"] = {
	"filters": [
		{
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            // reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            // reqd: 1,
        },
        {
            fieldname: "party",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            // reqd: 1,
        }

	]
};
 