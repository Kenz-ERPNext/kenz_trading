import json

import frappe


def execute():
    """after_migrate: show Item's Barcodes section at the end of the Details tab instead of the
    Inventory tab. Only that section moves; the rest of the site's own field order is kept."""
    fields = frappe.get_meta("Item", cached=False).fields
    order = [f.fieldname for f in fields]
    types = {f.fieldname: f.fieldtype for f in fields}

    if "sb_barcodes" not in order or "details" not in order:
        return

    def next_break(start, fieldtypes):
        return next((i for i in range(start + 1, len(order)) if types[order[i]] in fieldtypes), len(order))

    start = order.index("sb_barcodes")
    if order.index("details") < start < next_break(order.index("details"), ("Tab Break",)):
        return  # already in Details

    end = next_break(start, ("Section Break", "Tab Break"))
    section = order[start:end]
    del order[start:end]

    target = next_break(order.index("details"), ("Tab Break",))
    order[target:target] = section

    frappe.make_property_setter(
        {
            "doctype": "Item",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": json.dumps(order),
        },
        is_system_generated=False,
    )
    frappe.clear_cache(doctype="Item")
