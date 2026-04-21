// Copyright (c) 2026, TBO and contributors
// For license information, please see license.txt

frappe.query_reports["Item Analytics"] = {
    "filters": [
        {
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Item"
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "brand",
            "label": __("Brand"),
            "fieldtype": "Link",
            "options": "Brand"
        },
        {
            "fieldname": "selling_price_list",
            "label": __("Selling Price List"),
            "fieldtype": "Link",
            "options": "Price List",
            "get_query": function () {
                return { filters: { selling: 1 } };
            }
        },
        {
            "fieldname": "buying_price_list",
            "label": __("Buying Price List"),
            "fieldtype": "Link",
            "options": "Price List",
            "get_query": function () {
                return { filters: { buying: 1 } };
            }
        },
        {
            "fieldname": "show_disabled",
            "label": __("Show Disabled Items"),
            "fieldtype": "Check"
        }
    ]
};
