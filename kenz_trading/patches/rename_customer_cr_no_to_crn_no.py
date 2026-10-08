import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
    """Customer.custom_cr_no was renamed to custom_crn_no so it matches the field name pos_api
    looks for. Move the existing data/column over, and drop the old field so only one remains."""
    if not frappe.db.exists("Custom Field", "Customer-custom_cr_no"):
        return

    if frappe.db.exists("Custom Field", "Customer-custom_crn_no"):
        # Both fields already exist (new one synced from fixtures first): copy the data across
        # for customers that don't have a CRN yet, then remove the old field.
        if frappe.db.has_column("Customer", "custom_cr_no") and frappe.db.has_column("Customer", "custom_crn_no"):
            frappe.db.sql(
                """update `tabCustomer` set custom_crn_no = custom_cr_no
                where ifnull(custom_crn_no, '') = '' and ifnull(custom_cr_no, '') != ''"""
            )
        frappe.delete_doc("Custom Field", "Customer-custom_cr_no", ignore_permissions=True, force=True)
    else:
        frappe.reload_doctype("Customer")
        rename_field("Customer", "custom_cr_no", "custom_crn_no")

    frappe.db.delete("Property Setter", {"name": "Customer-custom_cr_no-allow_in_quick_entry"})
    frappe.clear_cache(doctype="Customer")
