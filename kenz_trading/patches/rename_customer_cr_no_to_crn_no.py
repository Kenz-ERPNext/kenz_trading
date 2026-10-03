import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
    """Customer.custom_cr_no was renamed to custom_crn_no so it matches the field name pos_api
    looks for. Move the existing data/column over before the fixture creates the new field."""
    if not frappe.db.exists("Custom Field", "Customer-custom_cr_no"):
        return
    if frappe.db.exists("Custom Field", "Customer-custom_crn_no"):
        frappe.delete_doc("Custom Field", "Customer-custom_cr_no", ignore_permissions=True, force=True)
        return

    frappe.reload_doctype("Customer")
    rename_field("Customer", "custom_cr_no", "custom_crn_no")
    frappe.db.delete("Property Setter", {"name": "Customer-custom_cr_no-allow_in_quick_entry"})
    frappe.clear_cache(doctype="Customer")
