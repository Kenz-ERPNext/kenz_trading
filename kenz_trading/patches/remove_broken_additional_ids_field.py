import frappe

# (Custom Field name, ksa_compliance child doctype it points at)
BROKEN_FIELDS = [
    ("Customer-custom_additional_ids", "Additional Buyer IDs"),
    ("Branch-custom_branch_ids", "Additional Seller IDs"),
]


def execute():
    """One-time cleanup: earlier releases shipped some of ksa_compliance's own custom fields
    unconditionally (Customer's custom_additional_ids, Branch's custom_branch_ids), pointing at
    ksa_compliance's "Additional Buyer IDs" / "Additional Seller IDs" doctypes. On any site
    without ksa_compliance installed, those doctypes don't exist, and the field alone is
    enough to break the whole form ("DocType Additional Seller IDs not found"). They've been
    removed from custom/*.json so they won't be recreated (ksa_compliance syncs them itself
    where it's installed), but bench migrate never deletes a field just because it left the
    fixture file - sites that already had them need this to actually remove the existing row.
    """
    for field_name, options in BROKEN_FIELDS:
        if frappe.db.exists("DocType", options):
            continue  # ksa_compliance is installed here - the field is meant to work, leave it alone

        if frappe.db.exists("Custom Field", field_name):
            frappe.delete_doc("Custom Field", field_name, ignore_permissions=True, force=True)
            frappe.clear_cache(doctype=field_name.split("-", 1)[0])
            print(f"Removed broken Custom Field: {field_name}")
