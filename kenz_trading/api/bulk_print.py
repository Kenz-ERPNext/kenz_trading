

# import frappe
# @frappe.whitelist()
# def bulk_print_sales_invoice(filters=None):
#     import json
#     import io
#     import zipfile
#     import time

#     if isinstance(filters, str):
#         filters = json.loads(filters)

#     if not filters:
#         filters = []

#     if isinstance(filters, dict):
#         filters = [["Sales Invoice", key, "=", value] for key, value in filters.items()]

#     # Only submitted
#     filters.append(["Sales Invoice", "docstatus", "=", 1])

#     invoices = frappe.get_all(
#         "Sales Invoice",
#         filters=filters,
#         pluck="name"
#     )

#     if not invoices:
#         frappe.throw("No Submitted Sales Invoices found")

#     zip_buffer = io.BytesIO()

#     with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
#         for inv in invoices:
#             html = frappe.get_print("Sales Invoice", inv)
#             pdf = frappe.utils.pdf.get_pdf(html)
#             zipf.writestr(f"{inv}.pdf", pdf)

#     zip_buffer.seek(0)

#     file_name = f"Bulk_Sales_Invoices_{int(time.time())}.zip"

#     file_doc = frappe.get_doc({
#         "doctype": "File",
#         "file_name": file_name,
#         "is_private": 0,
#         "content": zip_buffer.read()
#     })
#     file_doc.save(ignore_permissions=True)

#     return file_doc.file_url

 

import frappe
import json

@frappe.whitelist()
def get_sales_invoice_names(filters=None):

    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = []

    if isinstance(filters, dict):
        filters = [["Sales Invoice", key, "=", value] for key, value in filters.items()]

    filters.append(["Sales Invoice", "docstatus", "=", 1])

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        pluck="name"
    )

    return invoices




@frappe.whitelist()
def get_purchase_invoice_names(filters=None):

    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = []

    if isinstance(filters, dict):
        filters = [["Purchase Invoice", key, "=", value] for key, value in filters.items()]

    filters.append(["Purchase Invoice", "docstatus", "=", 1])

    invoices = frappe.get_all(
        "Purchase Invoice",
        filters=filters,
        pluck="name"
    )

    return invoices


@frappe.whitelist()
def get_payment_entry_names(filters=None):

    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = []

    if isinstance(filters, dict):
        filters = [["Payment Entry", key, "=", value] for key, value in filters.items()]

    filters.append(["Payment Entry", "docstatus", "=", 1])

    entries = frappe.get_all(
        "Payment Entry",
        filters=filters,
        pluck="name"
    )

    return entries


@frappe.whitelist()
def get_stock_entry_names(filters=None):

    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = []

    if isinstance(filters, dict):
        filters = [["Stock Entry", key, "=", value] for key, value in filters.items()]

    filters.append(["Stock Entry", "docstatus", "=", 1])

    entries = frappe.get_all(
        "Stock Entry",
        filters=filters,
        pluck="name"
    )

    return entries