import frappe


def execute():
    """Purchase Invoice tax_id was briefly made an editable Data field. Drop those property
    setters (fixtures don't delete them) so it goes back to ERPNext's Read Only field."""
    for name in ("Purchase Invoice-tax_id-fieldtype", "Purchase Invoice-tax_id-read_only"):
        if frappe.db.exists("Property Setter", name):
            frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)
    frappe.clear_cache(doctype="Purchase Invoice")
