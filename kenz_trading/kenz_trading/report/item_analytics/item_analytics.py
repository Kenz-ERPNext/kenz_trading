# Copyright (c) 2026, TBO and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 140},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": _("Item Name (Arabic)"), "fieldname": "custom_item_name_in_arabic", "fieldtype": "Data", "width": 220},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 140},
        {"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 110},
        {"label": _("Default UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
        {"label": _("UOM (Selling Rate)"), "fieldname": "uom_selling_rates", "fieldtype": "Data", "width": 320},
        {"label": _("Purchase Rate"), "fieldname": "purchase_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 120},
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
            i.custom_item_name_in_arabic,
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
    # Selling rates from Item Price (row per UOM for each item)
    selling_price_list = (
        filters.get("selling_price_list")
        or frappe.db.get_single_value("Selling Settings", "selling_price_list")
        or "Standard Selling"
    )
    selling_prices = frappe.db.sql(
        """
        SELECT item_code, uom, price_list_rate AS rate, valid_from
        FROM `tabItem Price`
        WHERE selling = 1
            AND price_list = %(pl)s
            AND item_code IN %(codes)s
        ORDER BY item_code, valid_from DESC, creation DESC
        """,
        {"pl": selling_price_list, "codes": tuple(item_codes)},
        as_dict=True,
    )
    selling_map = {}
    for r in selling_prices:
        selling_map.setdefault(r.item_code, []).append(r)

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
        purchase_rate = buying_map.get(it.item_code) or it.last_purchase_rate or 0
        valuation_rate = bin_map.get(it.item_code) or it.valuation_rate or 0
        vat_rate = item_vat_map.get(it.item_code, 0)

        selling_rows = selling_map.get(it.item_code) or []
        data.append({
            "item_code": it.item_code,
            "item_name": _strip_uom_from_item_name(it.item_name, None, it.stock_uom),
            "custom_item_name_in_arabic": it.custom_item_name_in_arabic,
            "item_group": it.item_group,
            "brand": it.brand,
            "stock_uom": it.stock_uom,
            "uom_selling_rates": _build_uom_selling_rates(selling_rows, it.stock_uom, it.standard_rate),
            "purchase_rate": purchase_rate,
            "valuation_rate": valuation_rate,
            "vat_rate": vat_rate,
            "item_tax_template": item_template_map.get(it.item_code),
            "disabled": it.disabled,
        })

    return data


def _build_uom_selling_rates(selling_rows, stock_uom, fallback_rate):
    if not selling_rows:
        return f"{stock_uom} ({_fmt_rate(fallback_rate)})"

    latest_rate_by_uom = {}
    for row in selling_rows:
        uom = row.uom or stock_uom
        # Query is already sorted by valid_from desc, creation desc.
        # Keep first record per UOM => latest valid selling rate.
        if uom not in latest_rate_by_uom:
            latest_rate_by_uom[uom] = row.rate

    parts = []
    for uom in sorted(latest_rate_by_uom):
        parts.append(f"{uom} ({_fmt_rate(latest_rate_by_uom[uom])})")

    return " | ".join(parts)


def _fmt_rate(rate):
    return f"{float(rate or 0):g}"


def _strip_uom_from_item_name(item_name, selling_uom, stock_uom):
    name = (item_name or "").strip()
    if not name:
        return ""

    for uom in {selling_uom, stock_uom}:
        if not uom:
            continue
        pattern = rf"(\s*[-/]\s*{re.escape(uom)}|\s*\({re.escape(uom)}\))$"
        name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

    return name


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
