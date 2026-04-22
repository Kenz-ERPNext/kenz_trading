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
    ],
    "formatter": function (value, row, column, data, default_formatter) {
        const formatted = default_formatter(value, row, column, data);

        if (column.fieldname !== "uom_selling_rates" || !value) {
            return formatted;
        }

        const parts = String(value)
            .split("|")
            .map((p) => p.trim())
            .filter(Boolean);

        if (!parts.length) {
            return formatted;
        }

        const colors = [
            { bg: "#e8f5e9", text: "#1b5e20" },
            { bg: "#e3f2fd", text: "#0d47a1" },
            { bg: "#fff8e1", text: "#e65100" },
            { bg: "#f3e5f5", text: "#4a148c" },
            { bg: "#e0f2f1", text: "#004d40" }
        ];

        const badges = parts.map((part, idx) => {
            const c = colors[idx % colors.length];
            return `<span style="
                display:inline-block;
                margin:2px 6px 2px 0;
                padding:2px 8px;
                border-radius:999px;
                background:${c.bg};
                color:${c.text};
                font-weight:600;
                white-space:nowrap;
            ">${frappe.utils.escape_html(part)}</span>`;
        });

        return badges.join("");
    }
};
