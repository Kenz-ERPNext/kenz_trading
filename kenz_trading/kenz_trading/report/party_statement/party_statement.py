import frappe
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": "Transaction Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": "Transaction No", "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
        {"label": "Transaction Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 140},
        {"label": "Transaction Amount", "fieldname": "transaction_amount", "fieldtype": "Currency", "width": 150},
        {"label": "Paid Amount", "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 120},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 120},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Payment Entry Ref", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 180},
    ]


def get_data(filters):
    if not filters.get("party"):
        frappe.throw("Please select a Party (Customer)")

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    party = filters.get("party")

    data = []

    # ---- Fetch Sales Invoices ----
    sales_invoices = frappe.db.sql("""
        SELECT 
            name AS voucher_no,
            posting_date,
            'Sales Invoice' AS voucher_type,
            grand_total AS transaction_amount,
            outstanding_amount,
            status
        FROM `tabSales Invoice`
        WHERE customer = %s
            AND posting_date BETWEEN %s AND %s
            AND docstatus = 1
        ORDER BY posting_date
    """, (party, from_date, to_date), as_dict=True)

    balance = 0
    for si in sales_invoices:
        # Find paid amount from Payment Entries
        paid_amount = frappe.db.sql("""
            SELECT SUM(allocated_amount) 
            FROM `tabPayment Entry Reference`
            WHERE reference_name = %s
        """, (si.voucher_no,))[0][0] or 0

        debit = si.transaction_amount
        credit = paid_amount
        balance += (debit - credit)

        payment_ref = frappe.db.get_value(
            "Payment Entry Reference",
            {"reference_name": si.voucher_no},
            "parent"
        )

        data.append({
            "posting_date": si.posting_date,
            "voucher_no": si.voucher_no,
            "voucher_type": si.voucher_type,
            "transaction_amount": si.transaction_amount,
            "paid_amount": paid_amount,
            "debit": debit,
            "credit": credit,
            "balance": balance,
            "status": si.status,
            "payment_entry": payment_ref,
        })

    return data
