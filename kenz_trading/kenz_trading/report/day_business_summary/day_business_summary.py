


import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    data = []
    columns = get_columns()

    # Collect data from all sections
    sections = [
        ("Sales Summary", get_sales_summary(filters)),
        ("Purchase Summary", get_purchase_summary(filters)),
        ("Cash & Bank Summary", get_cash_bank_summary(filters)),
        ("Sales Details", get_sales_details(filters)),
        ("Sales Return Details", get_sales_return_details(filters)),
        ("Purchase Details", get_purchase_details(filters)),
        ("Purchase Return", get_purchase_return(filters)),
        ("Receipts", get_receipt_details(filters)),
        ("Payments", get_payment_details(filters)),
        ("Contra (Journal Entry)", get_contra_details(filters))
    ]

    # Build data
    for title, rows in sections:
        if rows:
            data.append({
                "sl_no": "",
                "voucher_no": _("▶ ") + title,
                "particulars": "",
                "reference": "",
                "cash": "",
                "bank": "",
                "cheque": "",
                "total": "",
                "account": ""
            })
            data += rows
            data.append({
                "sl_no": "",
                "voucher_no": "",
                "particulars": "",
                "reference": "",
                "cash": "",
                "bank": "",
                "cheque": "",
                "total": "",
                "account": ""
            })

    return columns, data


# -------------------------------
# Column Setup
# -------------------------------

def get_columns():
    return [
        {"label": _("SL No"), "fieldname": "sl_no", "fieldtype": "Int", "width": 50},
        {"label": _("Voucher / Invoice No"), "fieldname": "voucher_no", "fieldtype": "Data", "width": 200},
        {"label": _("Particulars"), "fieldname": "particulars", "fieldtype": "Data", "width": 200},
        {"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 100},
        {"label": _("Cash"), "fieldname": "cash", "fieldtype": "Currency", "width": 100},
        {"label": _("Bank"), "fieldname": "bank", "fieldtype": "Currency", "width": 100},
        {"label": _("Cheque"), "fieldname": "cheque", "fieldtype": "Currency", "width": 100},
        {"label": _("Total Amount"), "fieldname": "total", "fieldtype": "Currency", "width": 120},
        # {"label": _("Account / Sales By"), "fieldname": "account", "fieldtype": "Data", "width": 150},
    ]


# -------------------------------
# Data Queries
# -------------------------------

def get_sales_summary(filters):
    company = filters.get("company")
    posting_date = filters.get("posting_date")

    # Cash Sales
    cash_sales = frappe.db.sql("""
        SELECT IFNULL(SUM(si.base_grand_total), 0)
        FROM `tabSales Invoice` si
        JOIN `tabPayment Entry Reference` per ON per.reference_name = si.name
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Cash'
        AND si.is_return = 0
        AND si.company = %(company)s
        AND si.posting_date = %(posting_date)s
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Bank Sales
    bank_sales = frappe.db.sql("""
        SELECT IFNULL(SUM(si.base_grand_total), 0)
        FROM `tabSales Invoice` si
        JOIN `tabPayment Entry Reference` per ON per.reference_name = si.name
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Bank'
        AND si.is_return = 0
        AND si.company = %(company)s
        AND si.posting_date = %(posting_date)s
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Credit Sales (no payment entry)
    credit_sales = frappe.db.sql("""
        SELECT IFNULL(SUM(base_grand_total), 0)
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 AND si.is_return = 0
        AND si.company = %(company)s
        AND si.posting_date = %(posting_date)s
        AND si.name NOT IN (
            SELECT reference_name FROM `tabPayment Entry Reference`
            WHERE reference_doctype = 'Sales Invoice'
        )
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Sales Return - Cash
    sales_return_cash = frappe.db.sql("""
        SELECT IFNULL(SUM(si.base_grand_total), 0)
        FROM `tabSales Invoice` si
        JOIN `tabPayment Entry Reference` per ON per.reference_name = si.name
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Cash'
        AND si.is_return = 1
        AND si.company = %(company)s
        AND si.posting_date = %(posting_date)s
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Sales Return - Credit
    sales_return_credit = frappe.db.sql("""
        SELECT IFNULL(SUM(base_grand_total), 0)
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 AND si.is_return = 1
        AND si.company = %(company)s
        AND si.posting_date = %(posting_date)s
        AND si.name NOT IN (
            SELECT reference_name FROM `tabPayment Entry Reference`
            WHERE reference_doctype = 'Sales Invoice'
        )
    """, {"company": company, "posting_date": posting_date})[0][0]

    total_net_sales = (cash_sales + credit_sales + bank_sales) - (sales_return_cash + sales_return_credit)

    # Return formatted list for your report table
    return [
        {"voucher_no": "Cash Sales", "total": cash_sales},
        {"voucher_no": "Credit Sales", "total": credit_sales},
        {"voucher_no": "Bank Sales", "total": bank_sales},
        {"voucher_no": "Sales Return - Cash", "total": sales_return_cash},
        {"voucher_no": "Sales Return - Credit", "total": sales_return_credit},
        {"voucher_no": "Total Net Sales", "total": total_net_sales}
    ]
    return rows




def get_purchase_summary(filters):
    company = filters.get("company")
    posting_date = filters.get("posting_date")

    # Cash Purchases
    cash_purchase = frappe.db.sql("""
        SELECT IFNULL(SUM(pi.base_grand_total), 0)
        FROM `tabPurchase Invoice` pi
        JOIN `tabPayment Entry Reference` per ON per.reference_name = pi.name
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Cash'
        AND pi.is_return = 0
        AND pi.company = %(company)s
        AND pi.posting_date = %(posting_date)s
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Bank Purchases
    bank_purchase = frappe.db.sql("""
        SELECT IFNULL(SUM(pi.base_grand_total), 0)
        FROM `tabPurchase Invoice` pi
        JOIN `tabPayment Entry Reference` per ON per.reference_name = pi.name
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Bank'
        AND pi.is_return = 0
        AND pi.company = %(company)s
        AND pi.posting_date = %(posting_date)s
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Credit Purchases (no payment entry)
    credit_purchase = frappe.db.sql("""
        SELECT IFNULL(SUM(base_grand_total), 0)
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1 AND pi.is_return = 0
        AND pi.company = %(company)s
        AND pi.posting_date = %(posting_date)s
        AND pi.name NOT IN (
            SELECT reference_name FROM `tabPayment Entry Reference`
            WHERE reference_doctype = 'Purchase Invoice'
        )
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Purchase Return - Cash
    purchase_return_cash = frappe.db.sql("""
        SELECT IFNULL(SUM(pi.base_grand_total), 0)
        FROM `tabPurchase Invoice` pi
        JOIN `tabPayment Entry Reference` per ON per.reference_name = pi.name
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Cash'
        AND pi.is_return = 1
        AND pi.company = %(company)s
        AND pi.posting_date = %(posting_date)s
    """, {"company": company, "posting_date": posting_date})[0][0]

    # Purchase Return - Credit
    purchase_return_credit = frappe.db.sql("""
        SELECT IFNULL(SUM(base_grand_total), 0)
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1 AND pi.is_return = 1
        AND pi.company = %(company)s
        AND pi.posting_date = %(posting_date)s
        AND pi.name NOT IN (
            SELECT reference_name FROM `tabPayment Entry Reference`
            WHERE reference_doctype = 'Purchase Invoice'
        )
    """, {"company": company, "posting_date": posting_date})[0][0]

    total_net_purchase = (cash_purchase + credit_purchase + bank_purchase) - (purchase_return_cash + purchase_return_credit)

    return [
        {"voucher_no": "Cash Purchases", "total": cash_purchase},
        {"voucher_no": "Credit Purchases", "total": credit_purchase},
        {"voucher_no": "Bank Purchases", "total": bank_purchase},
        {"voucher_no": "Purchase Return - Cash", "total": purchase_return_cash},
        {"voucher_no": "Purchase Return - Credit", "total": purchase_return_credit},
        {"voucher_no": "Total Net Purchases", "total": total_net_purchase}
    ]



def get_cash_bank_summary(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            account AS voucher_no,
            '' AS particulars,
            '' AS reference,
            SUM(debit) AS cash,
            SUM(credit) AS bank,
            0 AS cheque,
            (SUM(debit) - SUM(credit)) AS total,
            '' AS account
        FROM `tabGL Entry`
        WHERE posting_date = %(posting_date)s
            AND company = %(company)s
            AND account IN ('Cash', 'Bank')
        GROUP BY account
    """, filters, as_dict=True)


def get_sales_details(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            si.name AS voucher_no,
            si.customer AS particulars,
            '' AS reference,
            CASE WHEN si.is_pos = 1 THEN si.grand_total ELSE 0 END AS cash,
            0 AS bank,
            0 AS cheque,
            si.grand_total AS total,
            si.owner AS account
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
            AND si.is_return = 0
            AND si.posting_date = %(posting_date)s
            AND si.company = %(company)s
    """, filters, as_dict=True)


def get_sales_return_details(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            si.name AS voucher_no,
            si.customer AS particulars,
            si.return_against AS reference,
            0 AS cash,
            0 AS bank,
            0 AS cheque,
            si.grand_total AS total,
            '' AS account
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
            AND si.is_return = 1
            AND si.posting_date = %(posting_date)s
            AND si.company = %(company)s
    """, filters, as_dict=True)


def get_purchase_details(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            pi.name AS voucher_no,
            pi.supplier AS particulars,
            pi.bill_no AS reference,
            0 AS cash,
            0 AS bank,
            0 AS cheque,
            pi.grand_total AS total,
            '' AS account
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1
            AND pi.is_return = 0
            AND pi.posting_date = %(posting_date)s
            AND pi.company = %(company)s
    """, filters, as_dict=True)


def get_purchase_return(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            pi.name AS voucher_no,
            pi.supplier AS particulars,
            pi.return_against AS reference,
            0 AS cash,
            0 AS bank,
            0 AS cheque,
            pi.grand_total AS total,
            '' AS account
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1
            AND pi.is_return = 1
            AND pi.posting_date = %(posting_date)s
            AND pi.company = %(company)s
    """, filters, as_dict=True)


def get_receipt_details(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            pe.name AS voucher_no,
            pe.party AS particulars,
            '' AS reference,
            CASE WHEN pe.paid_to LIKE '%%Cash%%' THEN pe.paid_amount ELSE 0 END AS cash,
            CASE WHEN pe.paid_to LIKE '%%Bank%%' THEN pe.paid_amount ELSE 0 END AS bank,
            0 AS cheque,
            pe.paid_amount AS total,
            pe.paid_to AS account
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
            AND pe.payment_type = 'Receive'
            AND pe.posting_date = %(posting_date)s
            AND pe.company = %(company)s
    """, filters, as_dict=True)


def get_payment_details(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            pe.name AS voucher_no,
            pe.party AS particulars,
            '' AS reference,
            CASE WHEN pe.paid_from LIKE '%%Cash%%' THEN pe.paid_amount ELSE 0 END AS cash,
            CASE WHEN pe.paid_from LIKE '%%Bank%%' THEN pe.paid_amount ELSE 0 END AS bank,
            0 AS cheque,
            pe.paid_amount AS total,
            pe.paid_from AS account
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
            AND pe.payment_type = 'Pay'
            AND pe.posting_date = %(posting_date)s
            AND pe.company = %(company)s
    """, filters, as_dict=True)


def get_contra_details(filters):
    return frappe.db.sql("""
        SELECT
            row_number() over() AS sl_no,
            je.name AS voucher_no,
            a.account AS particulars,
            '' AS reference,
            a.credit AS cash,
            a.debit AS bank,
            0 AS cheque,
            (a.debit + a.credit) AS total,
            je.user_remark AS account
        FROM `tabJournal Entry` je
        JOIN `tabJournal Entry Account` a ON a.parent = je.name
        WHERE je.docstatus = 1
            AND je.posting_date = %(posting_date)s
            AND je.company = %(company)s
    """, filters, as_dict=True)












# import frappe
# from frappe import _
# from frappe.utils import flt
# from frappe.utils.data import money_in_words
# from frappe.utils.formatters import format_value

# def execute(filters=None):
#     filters = filters or {}
#     columns = get_columns()
#     data = []

#     # --- Sales Summary Header ---
#     data.append(section_header("▶ Sales Summary"))
#     data += get_sales_summary_rows(filters)

#     # --- Sales Details ---
#     data.append(section_header("▶ Sales Details"))
#     data += get_sales_details(filters)

#     # --- Sales Return ---
#     data.append(section_header("▶ Sales Return"))
#     data += get_sales_return_details(filters)

#     # --- Purchase Summary ---
#     data.append(section_header("▶ Purchase Summary"))
#     data += get_purchase_summary_rows(filters)

#     # --- Purchase Details ---
#     data.append(section_header("▶ Purchase Details"))
#     data += get_purchase_details(filters)

#     # --- Purchase Return ---
#     data.append(section_header("▶ Purchase Return"))
#     data += get_purchase_return(filters)

#     # --- Receipts ---
#     data.append(section_header("▶ Receipt Details"))
#     data += get_receipt_details(filters)

#     # --- Payments ---
#     data.append(section_header("▶ Payment Details"))
#     data += get_payment_details(filters)

#     # --- Contra ---
#     data.append(section_header("▶ Contra Details"))
#     data += get_contra_details(filters)

#     return columns, data


# # ------------------------
# # Columns
# # ------------------------
# def get_columns():
#     return [
#         {"label": _("#"), "fieldname": "sl_no", "fieldtype": "Data", "width": 40},
#         {"label": _("Voucher / Invoice No"), "fieldname": "voucher_no", "fieldtype": "Data", "width": 200},
#         {"label": _("Particulars"), "fieldname": "particulars", "fieldtype": "Data", "width": 240},
#         {"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 120},
#         {"label": _("Cash"), "fieldname": "cash", "fieldtype": "Data", "width": 120},
#         {"label": _("Bank"), "fieldname": "bank", "fieldtype": "Data", "width": 120},
#         {"label": _("Cheque"), "fieldname": "cheque", "fieldtype": "Data", "width": 120},
#         {"label": _("Total Amount"), "fieldname": "total", "fieldtype": "Data", "width": 160},
#         {"label": _("Account / Sales By"), "fieldname": "account", "fieldtype": "Data", "width": 180},
#     ]


# # ------------------------
# # Helper Functions
# # ------------------------
# def section_header(title):
#     return {
#         "sl_no": "",
#         "voucher_no": _(title),
#         "particulars": "",
#         "reference": "",
#         "cash": "",
#         "bank": "",
#         "cheque": "",
#         "total": "",
#         "account": ""
#     }

# def _fmt_currency(amount, currency):
#     """Return formatted currency (hide 0)."""
#     if not amount:
#         return ""
#     try:
#         return format_currency(amount, currency)
#     except Exception:
#         return f"{flt(amount):,.2f} {currency or ''}"

# def _qsum(sql, params):
#     val = frappe.db.sql(sql, params)[0][0] or 0
#     return flt(val, 2)


# # ------------------------
# # SALES SUMMARY
# # ------------------------
# def get_sales_summary_rows(filters):
#     company = filters.get("company")
#     posting_date = filters.get("posting_date")
#     currency = frappe.get_value("Company", company, "default_currency") or ""

#     cash_sales = _qsum("""
#         SELECT SUM(si.base_grand_total)
#         FROM `tabSales Invoice` si
#         JOIN `tabPayment Entry Reference` per ON per.reference_name = si.name
#         JOIN `tabPayment Entry` pe ON pe.name = per.parent
#         WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Cash'
#         AND si.is_return = 0 AND si.company = %(company)s AND si.posting_date = %(posting_date)s
#     """, {"company": company, "posting_date": posting_date})

#     bank_sales = _qsum("""
#         SELECT SUM(si.base_grand_total)
#         FROM `tabSales Invoice` si
#         JOIN `tabPayment Entry Reference` per ON per.reference_name = si.name
#         JOIN `tabPayment Entry` pe ON pe.name = per.parent
#         WHERE pe.docstatus = 1 AND pe.mode_of_payment = 'Bank'
#         AND si.is_return = 0 AND si.company = %(company)s AND si.posting_date = %(posting_date)s
#     """, {"company": company, "posting_date": posting_date})

#     credit_sales = _qsum("""
#         SELECT SUM(si.base_grand_total)
#         FROM `tabSales Invoice` si
#         WHERE si.docstatus = 1 AND si.is_return = 0
#         AND si.company = %(company)s AND si.posting_date = %(posting_date)s
#         AND si.name NOT IN (
#             SELECT reference_name FROM `tabPayment Entry Reference`
#             WHERE reference_doctype = 'Sales Invoice'
#         )
#     """, {"company": company, "posting_date": posting_date})

#     sales_return_cash = _qsum("""
#         SELECT SUM(si.base_grand_total)
#         FROM `tabSales Invoice` si
#         JOIN `tabPayment Entry Reference` per ON per.reference_name = si.name
#         JOIN `tabPayment Entry` pe ON pe.name = per.parent
#         WHERE pe.mode_of_payment = 'Cash' AND si.is_return = 1
#         AND si.company = %(company)s AND si.posting_date = %(posting_date)s
#     """, {"company": company, "posting_date": posting_date})

#     sales_return_credit = _qsum("""
#         SELECT SUM(si.base_grand_total)
#         FROM `tabSales Invoice` si
#         WHERE si.is_return = 1 AND si.company = %(company)s
#         AND si.posting_date = %(posting_date)s
#         AND si.name NOT IN (
#             SELECT reference_name FROM `tabPayment Entry Reference`
#             WHERE reference_doctype = 'Sales Invoice'
#         )
#     """, {"company": company, "posting_date": posting_date})

#     total_net_sales = (cash_sales + credit_sales + bank_sales) - (sales_return_cash + sales_return_credit)

#     return [
#         {"sl_no": 1, "particulars": "Cash Sales", "total": _fmt_currency(cash_sales, currency)},
#         {"sl_no": 2, "particulars": "Credit Sales", "total": _fmt_currency(credit_sales, currency)},
#         {"sl_no": 3, "particulars": "Bank Sales", "total": _fmt_currency(bank_sales, currency)},
#         {"sl_no": 4, "particulars": "Sales Return - Cash", "total": _fmt_currency(sales_return_cash, currency)},
#         {"sl_no": 5, "particulars": "Sales Return - Credit", "total": _fmt_currency(sales_return_credit, currency)},
#         {"sl_no": 6, "particulars": "Total Net Sales", "total": _fmt_currency(total_net_sales, currency)},
#     ]


# # ------------------------
# # PURCHASE SUMMARY
# # ------------------------
# def get_purchase_summary_rows(filters):
#     company = filters.get("company")
#     posting_date = filters.get("posting_date")
#     currency = frappe.get_value("Company", company, "default_currency") or ""

#     cash_purchase = _qsum("""
#         SELECT SUM(pi.base_grand_total)
#         FROM `tabPurchase Invoice` pi
#         JOIN `tabPayment Entry Reference` per ON per.reference_name = pi.name
#         JOIN `tabPayment Entry` pe ON pe.name = per.parent
#         WHERE pe.mode_of_payment = 'Cash' AND pi.is_return = 0
#         AND pi.company = %(company)s AND pi.posting_date = %(posting_date)s
#     """, {"company": company, "posting_date": posting_date})

#     bank_purchase = _qsum("""
#         SELECT SUM(pi.base_grand_total)
#         FROM `tabPurchase Invoice` pi
#         JOIN `tabPayment Entry Reference` per ON per.reference_name = pi.name
#         JOIN `tabPayment Entry` pe ON pe.name = per.parent
#         WHERE pe.mode_of_payment = 'Bank' AND pi.is_return = 0
#         AND pi.company = %(company)s AND pi.posting_date = %(posting_date)s
#     """, {"company": company, "posting_date": posting_date})

#     credit_purchase = _qsum("""
#         SELECT SUM(pi.base_grand_total)
#         FROM `tabPurchase Invoice` pi
#         WHERE pi.docstatus = 1 AND pi.is_return = 0
#         AND pi.company = %(company)s AND pi.posting_date = %(posting_date)s
#         AND pi.name NOT IN (
#             SELECT reference_name FROM `tabPayment Entry Reference`
#             WHERE reference_doctype = 'Purchase Invoice'
#         )
#     """, {"company": company, "posting_date": posting_date})

#     purchase_return_cash = _qsum("""
#         SELECT SUM(pi.base_grand_total)
#         FROM `tabPurchase Invoice` pi
#         JOIN `tabPayment Entry Reference` per ON per.reference_name = pi.name
#         JOIN `tabPayment Entry` pe ON pe.name = per.parent
#         WHERE pe.mode_of_payment = 'Cash' AND pi.is_return = 1
#         AND pi.company = %(company)s AND pi.posting_date = %(posting_date)s
#     """, {"company": company, "posting_date": posting_date})

#     purchase_return_credit = _qsum("""
#         SELECT SUM(pi.base_grand_total)
#         FROM `tabPurchase Invoice` pi
#         WHERE pi.is_return = 1 AND pi.company = %(company)s
#         AND pi.posting_date = %(posting_date)s
#         AND pi.name NOT IN (
#             SELECT reference_name FROM `tabPayment Entry Reference`
#             WHERE reference_doctype = 'Purchase Invoice'
#         )
#     """, {"company": company, "posting_date": posting_date})

#     total_net_purchase = (cash_purchase + credit_purchase + bank_purchase) - (purchase_return_cash + purchase_return_credit)

#     return [
#         {"sl_no": 1, "particulars": "Cash Purchases", "total": _fmt_currency(cash_purchase, currency)},
#         {"sl_no": 2, "particulars": "Credit Purchases", "total": _fmt_currency(credit_purchase, currency)},
#         {"sl_no": 3, "particulars": "Bank Purchases", "total": _fmt_currency(bank_purchase, currency)},
#         {"sl_no": 4, "particulars": "Purchase Return - Cash", "total": _fmt_currency(purchase_return_cash, currency)},
#         {"sl_no": 5, "particulars": "Purchase Return - Credit", "total": _fmt_currency(purchase_return_credit, currency)},
#         {"sl_no": 6, "particulars": "Total Net Purchases", "total": _fmt_currency(total_net_purchase, currency)},
#     ]


# # ------------------------
# # Remaining Sections
# # ------------------------
# def get_sales_details(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, si.name AS voucher_no, si.customer AS particulars,
#                '' AS reference, '' AS cash, '' AS bank, '' AS cheque, si.grand_total AS total, si.owner AS account
#         FROM `tabSales Invoice` si
#         WHERE si.docstatus=1 AND si.is_return=0
#         AND si.posting_date=%(posting_date)s AND si.company=%(company)s
#     """, filters, as_dict=True)

# def get_sales_return_details(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, si.name AS voucher_no, si.customer AS particulars,
#                si.return_against AS reference, '' AS cash, '' AS bank, '' AS cheque, si.grand_total AS total, '' AS account
#         FROM `tabSales Invoice` si
#         WHERE si.docstatus=1 AND si.is_return=1
#         AND si.posting_date=%(posting_date)s AND si.company=%(company)s
#     """, filters, as_dict=True)

# def get_purchase_details(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, pi.name AS voucher_no, pi.supplier AS particulars,
#                pi.bill_no AS reference, '' AS cash, '' AS bank, '' AS cheque, pi.grand_total AS total, '' AS account
#         FROM `tabPurchase Invoice` pi
#         WHERE pi.docstatus=1 AND pi.is_return=0
#         AND pi.posting_date=%(posting_date)s AND pi.company=%(company)s
#     """, filters, as_dict=True)

# def get_purchase_return(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, pi.name AS voucher_no, pi.supplier AS particulars,
#                pi.return_against AS reference, '' AS cash, '' AS bank, '' AS cheque, pi.grand_total AS total, '' AS account
#         FROM `tabPurchase Invoice` pi
#         WHERE pi.docstatus=1 AND pi.is_return=1
#         AND pi.posting_date=%(posting_date)s AND pi.company=%(company)s
#     """, filters, as_dict=True)

# def get_receipt_details(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, pe.name AS voucher_no, pe.party AS particulars,
#                '' AS reference, '' AS cash, '' AS bank, '' AS cheque, pe.paid_amount AS total, pe.paid_to AS account
#         FROM `tabPayment Entry` pe
#         WHERE pe.docstatus=1 AND pe.payment_type='Receive'
#         AND pe.posting_date=%(posting_date)s AND pe.company=%(company)s
#     """, filters, as_dict=True)

# def get_payment_details(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, pe.name AS voucher_no, pe.party AS particulars,
#                '' AS reference, '' AS cash, '' AS bank, '' AS cheque, pe.paid_amount AS total, pe.paid_from AS account
#         FROM `tabPayment Entry` pe
#         WHERE pe.docstatus=1 AND pe.payment_type='Pay'
#         AND pe.posting_date=%(posting_date)s AND pe.company=%(company)s
#     """, filters, as_dict=True)

# def get_contra_details(filters):
#     return frappe.db.sql("""
#         SELECT row_number() over() AS sl_no, je.name AS voucher_no, a.account AS particulars,
#                '' AS reference, '' AS cash, '' AS bank, '' AS cheque, (a.debit + a.credit) AS total, je.user_remark AS account
#         FROM `tabJournal Entry` je
#         JOIN `tabJournal Entry Account` a ON a.parent=je.name
#         WHERE je.docstatus=1 AND je.posting_date=%(posting_date)s AND je.company=%(company)s
#     """, filters, as_dict=True)
