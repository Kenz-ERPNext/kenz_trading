import frappe
from frappe import _

def validate_warehouse(doc, method):
    """
    Ensure only one warehouse can have custom_is_default enabled at a time
    """
    if doc.custom_is_default:
        # Check if another warehouse already has custom_is_default enabled
        existing_default = frappe.db.sql("""
            SELECT name 
            FROM `tabWarehouse` 
            WHERE custom_is_default = 1 
            AND name != %s
            AND company = %s
        """, (doc.name, doc.company), as_dict=True)
        
        if existing_default:
            frappe.throw(
                _("Warehouse '{0}' is already set as default. Please uncheck it first before setting '{1}' as default.").format(
                    existing_default[0].name, doc.name
                )
            )


@frappe.whitelist()
def get_default_warehouse(company=None):
    """
    Get the default warehouse for a company
    """
    if not company:
        company = frappe.defaults.get_user_default("Company")
    
    warehouse = frappe.db.get_value(
        "Warehouse",
        filters={
            "custom_is_default": 1,
            "company": company,
            "disabled": 0
        },
        fieldname="name"
    )
    
    return warehouse
