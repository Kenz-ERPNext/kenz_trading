import frappe


def execute():
    """One-time cleanup: an earlier release shipped Customer's custom_additional_ids field
    unconditionally, pointing at ksa_compliance's "Additional Buyer IDs" doctype. On any site
    without ksa_compliance installed, that doctype doesn't exist, and this field alone was
    enough to break every Customer page ("DocType Additional Buyer IDs not found"). It's been
    removed from custom/customer.json so it won't be recreated, but bench migrate never
    deletes a field just because it left the fixture file - sites that already had it need
    this to actually remove the existing row.
    """
    if frappe.db.exists("DocType", "Additional Buyer IDs"):
        return  # ksa_compliance is installed here - the field is meant to work, leave it alone

    if frappe.db.exists("Custom Field", "Customer-custom_additional_ids"):
        frappe.delete_doc(
            "Custom Field", "Customer-custom_additional_ids", ignore_permissions=True, force=True
        )
        frappe.clear_cache(doctype="Customer")
        print("Removed broken Custom Field: Customer-custom_additional_ids")
