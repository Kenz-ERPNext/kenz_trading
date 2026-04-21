# Copyright (c) 2026, TBO and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 140},
        {"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 110},
        {"label": _("Default UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
        {"label": _("All UOMs"), "fieldname": "all_uoms", "fieldtype": "Data", "width": 180},
        {"label": _("Purchase Rate"), "fieldname": "purchase_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Selling Rate"), "fieldname": "selling_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("VAT %"), "fieldname": "vat_rate", "fieldtype": "Float", "width": 80},
        {"label": _("Item Tax Template"), "fieldname": "item_tax_template", "fieldtype": "Link", "options": "Item Tax Template", "width": 160},
        {"label": _("Disabled"), "fieldname": "disabled", "fieldtype": "Check", "width": 80},
    ]


def get_data(filters):
    conditions = ["i.disabled = 0"]
    params = {}

    if filters.get("item_group"):
        conditions.append("i.item_group = %(item_group)s")
        params["item_group"] = filters["item_group"]

    if filters.get("brand"):
        conditions.append("i.brand = %(brand)s")
        params["brand"] = filters["brand"]

    if filters.get("item_code"):
        conditions.append("i.name = %(item_code)s")
        params["item_code"] = filters["item_code"]

    if filters.get("show_disabled"):
        conditions = [c for c in conditions if c != "i.disabled = 0"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Base item list
    items = frappe.db.sql(
        f"""
        SELECT
            i.name AS item_code,
            i.item_name,
            i.item_group,
            i.brand,
            i.stock_uom,
            i.disabled,
            i.last_purchase_rate,
            i.valuation_rate,
            i.standard_rate
        FROM `tabItem` i
        WHERE {where_clause}
        ORDER BY i.item_code
        """,
        params,
        as_dict=True,
    )

    if not items:
        return []

    item_codes = [it.item_code for it in items]

    # All UOMs from UOM Conversion Detail
    uom_map = {}
    uom_rows = frappe.db.sql(
        """
        SELECT parent, uom, conversion_factor
        FROM `tabUOM Conversion Detail`
        WHERE parent IN %(codes)s
        ORDER BY conversion_factor
        """,
        {"codes": tuple(item_codes)},
        as_dict=True,
    )
    for r in uom_rows:
        uom_map.setdefault(r.parent, []).append(f"{r.uom} (x{r.conversion_factor})")

    # Selling Rate from Item Price (selling price list)
    selling_price_list = (
        filters.get("selling_price_list")
        or frappe.db.get_single_value("Selling Settings", "selling_price_list")
        or "Standard Selling"
    )
    selling_prices = frappe.db.sql(
        """
        SELECT item_code, MAX(price_list_rate) AS rate
        FROM `tabItem Price`
        WHERE selling = 1
            AND price_list = %(pl)s
            AND item_code IN %(codes)s
        GROUP BY item_code
        """,
        {"pl": selling_price_list, "codes": tuple(item_codes)},
        as_dict=True,
    )
    selling_map = {r.item_code: r.rate for r in selling_prices}

    # Purchase Rate from Item Price (buying price list) - fallback to last_purchase_rate
    buying_price_list = (
        filters.get("buying_price_list")
        or frappe.db.get_single_value("Buying Settings", "buying_price_list")
        or "Standard Buying"
    )
    buying_prices = frappe.db.sql(
        """
        SELECT item_code, MAX(price_list_rate) AS rate
        FROM `tabItem Price`
        WHERE buying = 1
            AND price_list = %(pl)s
            AND item_code IN %(codes)s
        GROUP BY item_code
        """,
        {"pl": buying_price_list, "codes": tuple(item_codes)},
        as_dict=True,
    )
    buying_map = {r.item_code: r.rate for r in buying_prices}

    # Latest valuation_rate from Bin (per item, use weighted avg or max)
    bin_rates = frappe.db.sql(
        """
        SELECT item_code, AVG(NULLIF(valuation_rate, 0)) AS rate
        FROM `tabBin`
        WHERE item_code IN %(codes)s
        GROUP BY item_code
        """,
        {"codes": tuple(item_codes)},
        as_dict=True,
    )
    bin_map = {r.item_code: r.rate for r in bin_rates}

    # VAT % and Item Tax Template from Item Tax child table
    item_vat_map, item_template_map = _get_item_vat_map(item_codes)

    data = []
    for it in items:
        uoms = uom_map.get(it.item_code, [])
        purchase_rate = buying_map.get(it.item_code) or it.last_purchase_rate or 0
        valuation_rate = bin_map.get(it.item_code) or it.valuation_rate or 0
        selling_rate = selling_map.get(it.item_code) or it.standard_rate or 0
        vat_rate = item_vat_map.get(it.item_code, 0)

        data.append({
            "item_code": it.item_code,
            "item_name": it.item_name,
            "item_group": it.item_group,
            "brand": it.brand,
            "stock_uom": it.stock_uom,
            "all_uoms": ", ".join(uoms) if uoms else it.stock_uom,
            "purchase_rate": purchase_rate,
            "valuation_rate": valuation_rate,
            "selling_rate": selling_rate,
            "vat_rate": vat_rate,
            "item_tax_template": item_template_map.get(it.item_code),
            "disabled": it.disabled,
        })

    return data


def _get_item_vat_map(item_codes):
    """
    Resolve VAT % and template name for each item from the Item Tax child
    table (tabItem Tax) which lives on the Item document.

    Returns: (vat_map, template_map)
      vat_map      -> {item_code: avg_tax_rate_%}
      template_map -> {item_code: item_tax_template}
    """
    if not item_codes:
        return {}, {}

    rows = frappe.db.sql(
        """
        SELECT parent AS item_code, item_tax_template
        FROM `tabItem Tax`
        WHERE parent IN %(codes)s
            AND item_tax_template IS NOT NULL
        """,
        {"codes": tuple(item_codes)},
        as_dict=True,
    )
    item_template = {r.item_code: r.item_tax_template for r in rows}

    if not item_template:
        return {}, {}

    templates = list({t for t in item_template.values() if t})
    template_rates = frappe.db.sql(
        """
        SELECT parent AS template, AVG(tax_rate) AS rate
        FROM `tabItem Tax Template Detail`
        WHERE parent IN %(templates)s
        GROUP BY parent
        """,
        {"templates": tuple(templates)},
        as_dict=True,
    )
    template_rate_map = {r.template: r.rate for r in template_rates}

    vat_map = {item: template_rate_map.get(template, 0) for item, template in item_template.items()}
    return vat_map, item_template
