import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def make_sales_invoice(quotation):
    if not quotation:
        frappe.throw("Quotation is required")

    doc = get_mapped_doc(
        "Quotation",
        quotation,
        {
            "Quotation": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "party_name": "customer",
                    "name": "quotation"
                }
            },
            "Quotation Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "name": "quotation_item",
                    "parent": "quotation"
                }
            }
        }
    )

    doc.ignore_pricing_rule = 1
    doc.set_missing_values()
    doc.calculate_taxes_and_totals()

    return doc
