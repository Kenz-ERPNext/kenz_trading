// Copyright (c) 2025, TBO and contributors
// For license information, please see license.txt

frappe.query_reports["Day Business Summary"] = {
	"filters": [

		{
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "posting_date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch"
        },
        {
            fieldname: "user",
            label: __("User"),
            fieldtype: "Link",
            options: "User"
        }

	]
};
 