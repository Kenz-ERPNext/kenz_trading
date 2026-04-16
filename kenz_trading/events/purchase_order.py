import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_uoms(doctype, txt, searchfield, start, page_len, filters):

    item_code = filters.get("item_code")

    if not item_code:
        return []

    uoms = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": item_code},
        pluck="uom"
    )

    if not uoms:
        return []

    return frappe.db.sql("""
        SELECT name
        FROM `tabUOM`
        WHERE name IN %(uoms)s
        AND name LIKE %(txt)s
        LIMIT %(start)s, %(page_len)s
    """, {
        "uoms": tuple(uoms),
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })