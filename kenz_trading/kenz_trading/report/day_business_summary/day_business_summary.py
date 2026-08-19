import frappe
from frappe import _
from frappe.utils import flt


# ============================================================
# MAIN EXECUTE
# ============================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    data = []
    columns = get_columns()

    # ========================================================
    # SECTION STYLES
    # ========================================================

    sales_style = "background-color:#d1f2eb; font-weight:bold;"
    purchase_style = "background-color:#f5b7b1; font-weight:bold;"
    neutral_style = "background-color:#d6eaf8; font-weight:bold;"
    red_style = "background-color:#71FC0F; font-weight:bold;"

    # ========================================================
    # SECTIONS
    # ========================================================

    sections = [
        ("Sales Summary", get_sales_summary(filters), sales_style),
        ("Purchase Summary", get_purchase_summary(filters), purchase_style),
        ("Sales Details", get_sales_details(filters), sales_style),
        ("Sales Return Details", get_sales_return_details(filters), sales_style),
        ("Purchase Details", get_purchase_details(filters), purchase_style),
        ("Purchase Return", get_purchase_return(filters), purchase_style),
        ("Cash & Bank Summary", get_cash_bank_summary(filters), neutral_style),
        ("Receipts", get_receipt_details(filters), neutral_style),
        ("Payments", get_payment_details(filters), red_style),
        ("Contra (Journal Entry)", get_contra_details(filters), neutral_style),
    ]

    # ========================================================
    # BUILD REPORT
    # ========================================================

    for title, rows, style in sections:

        # Section header
        data.append({
            "sl_no": "",
            "voucher_no": f"<div style='{style}'>&nbsp;▶ {title}</div>",
            "voucher_type": "",
            "particulars": "",
            "reference": "",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": "",
        })

        # No records
        if not rows:

            data.append({
                "sl_no": "",
                "voucher_no": "No records found",
                "voucher_type": "",
                "particulars": "",
                "reference": "",
                "cash": "",
                "bank": "",
                "cheque": "",
                "credit": "",
                "total": "",
            })

        else:

            for row in rows:

                voucher_no = str(row.get("voucher_no", ""))

                # Total row formatting
                if "Total" in voucher_no:

                    row["voucher_no"] = f"<b>{voucher_no}</b>"

                    if row.get("total") is not None:
                        row["total"] = flt(row["total"], 2)

                data.append(row)

        # Empty row after section
        data.append({
            "sl_no": "",
            "voucher_no": "",
            "voucher_type": "",
            "particulars": "",
            "reference": "",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": "",
        })

    return columns, data


# ============================================================
# COLUMNS
# ============================================================

def get_columns():

    return [

        {
            "label": _("SL No"),
            "fieldname": "sl_no",
            "fieldtype": "Int",
            "width": 50,
        },

        {
            "label": _("Voucher / Invoice No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },

        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Link",
            "options": "DocType",
            "hidden": 1,
        },

        {
            "label": _("Particulars"),
            "fieldname": "particulars",
            "fieldtype": "Data",
            "width": 180,
        },

        {
            "label": _("Reference"),
            "fieldname": "reference",
            "fieldtype": "Data",
            "width": 100,
        },

        {
            "label": _("Cash"),
            "fieldname": "cash",
            "fieldtype": "Currency",
            "width": 100,
        },

        {
            "label": _("Bank"),
            "fieldname": "bank",
            "fieldtype": "Currency",
            "width": 100,
        },

        {
            "label": _("Cheque"),
            "fieldname": "cheque",
            "fieldtype": "Currency",
            "width": 100,
        },

        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 100,
        },

        {
            "label": _("Total Amount"),
            "fieldname": "total",
            "fieldtype": "Currency",
            "width": 120,
        },
    ]


# ============================================================
# COMMON PARAMS
# ============================================================

def get_params(filters):

    return {
        "company": filters.get("company"),
        "posting_date": filters.get("posting_date"),
        "user": filters.get("user"),
    }


# ============================================================
# COMMON USER CONDITION
# ============================================================

def get_user_condition(alias, filters):

    if filters.get("user"):
        return f" AND {alias}.owner = %(user)s "

    return ""


# ============================================================
# SALES SUMMARY
# ============================================================

def get_sales_summary(filters):

    params = get_params(filters)

    user_condition = get_user_condition("si", filters)

    # ========================================================
    # 1. GROSS NORMAL SALES
    # ========================================================

    gross_sales = frappe.db.sql(
        f"""
        SELECT IFNULL(SUM(si.base_grand_total), 0)

        FROM `tabSales Invoice` si

        WHERE si.docstatus = 1
            AND si.is_return = 0
            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s
            {user_condition}
        """,
        params,
    )[0][0]

    gross_sales = flt(gross_sales)

    # ========================================================
    # 2. SALES RETURNS
    #
    # ERPNext return invoice has negative base_grand_total.
    # Therefore ABS() is required.
    # ========================================================

    sales_returns = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(ABS(si.base_grand_total)),
            0
        )

        FROM `tabSales Invoice` si

        WHERE si.docstatus = 1
            AND si.is_return = 1
            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s
            {user_condition}
        """,
        params,
    )[0][0]

    sales_returns = flt(sales_returns)

    # ========================================================
    # 3. CASH SALES
    #
    # Only payments allocated against NORMAL sales invoices.
    # ========================================================

    cash_sales = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabSales Invoice` si

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = si.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE si.docstatus = 1
            AND si.is_return = 0

            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cash%%'

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    cash_sales = flt(cash_sales)

    # ========================================================
    # 4. BANK SALES
    # ========================================================

    bank_sales = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabSales Invoice` si

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = si.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE si.docstatus = 1
            AND si.is_return = 0

            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'bank%%'

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    bank_sales = flt(bank_sales)

    # ========================================================
    # 5. CHEQUE SALES
    # ========================================================

    cheque_sales = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabSales Invoice` si

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = si.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE si.docstatus = 1
            AND si.is_return = 0

            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cheque%%'

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    cheque_sales = flt(cheque_sales)

    # ========================================================
    # 6. CREDIT SALES
    #
    # Credit = invoice amount - all allocated payments.
    #
    # Important:
    # We calculate this per invoice, then SUM.
    # ========================================================

    credit_sales = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(
                GREATEST(
                    si.base_grand_total
                    -
                    IFNULL(
                        (
                            SELECT SUM(per2.allocated_amount)

                            FROM `tabPayment Entry Reference` per2

                            INNER JOIN `tabPayment Entry` pe2
                                ON pe2.name = per2.parent

                            WHERE per2.reference_doctype = 'Sales Invoice'
                                AND per2.reference_name = si.name

                                AND pe2.docstatus = 1
                                AND pe2.payment_type = 'Receive'
                        ),
                        0
                    ),
                    0
                )
            ),
            0
        )

        FROM `tabSales Invoice` si

        WHERE si.docstatus = 1
            AND si.is_return = 0

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    credit_sales = flt(credit_sales)

    # ========================================================
    # 7. RETURN CASH REFUNDS
    # ========================================================

    sales_return_cash = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabSales Invoice` si

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = si.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE si.docstatus = 1
            AND si.is_return = 1

            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cash%%'

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    sales_return_cash = flt(sales_return_cash)

    # ========================================================
    # 8. RETURN BANK REFUNDS
    # ========================================================

    sales_return_bank = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabSales Invoice` si

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = si.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE si.docstatus = 1
            AND si.is_return = 1

            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'bank%%'

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    sales_return_bank = flt(sales_return_bank)

    # ========================================================
    # 9. RETURN CHEQUE REFUNDS
    # ========================================================

    sales_return_cheque = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabSales Invoice` si

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = si.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE si.docstatus = 1
            AND si.is_return = 1

            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cheque%%'

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    sales_return_cheque = flt(sales_return_cheque)

    # ========================================================
    # 10. CREDIT SALES RETURNS
    #
    # Return invoice is negative in ERPNext.
    #
    # Example:
    #
    # Return = -215
    #
    # ABS(-215) = 215
    #
    # If refund = 0:
    #
    # Credit Return = 215
    #
    # If refund = 100:
    #
    # Credit Return = 215 - 100 = 115
    # ========================================================

    sales_return_credit = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(
                GREATEST(
                    ABS(si.base_grand_total)
                    -
                    IFNULL(
                        (
                            SELECT SUM(per2.allocated_amount)

                            FROM `tabPayment Entry Reference` per2

                            INNER JOIN `tabPayment Entry` pe2
                                ON pe2.name = per2.parent

                            WHERE per2.reference_doctype = 'Sales Invoice'
                                AND per2.reference_name = si.name

                                AND pe2.docstatus = 1
                                AND pe2.payment_type = 'Pay'
                        ),
                        0
                    ),
                    0
                )
            ),
            0
        )

        FROM `tabSales Invoice` si

        WHERE si.docstatus = 1
            AND si.is_return = 1

            AND si.company = %(company)s
            AND si.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    sales_return_credit = flt(sales_return_credit)

    # ========================================================
    # 11. FINAL GROSS SALES
    #
    # This should equal:
    #
    # Cash + Bank + Cheque + Credit
    #
    # Normally this equals invoice total.
    # ========================================================

    calculated_gross_sales = (
        cash_sales
        + bank_sales
        + cheque_sales
        + credit_sales
    )

    # ========================================================
    # 12. FINAL SALES RETURNS
    #
    # This should equal:
    #
    # Cash Refund
    # + Bank Refund
    # + Cheque Refund
    # + Credit Return
    # ========================================================

    calculated_sales_returns = (
        sales_return_cash
        + sales_return_bank
        + sales_return_cheque
        + sales_return_credit
    )

    # ========================================================
    # 13. NET SALES
    #
    # Gross Sales - Sales Returns
    # ========================================================

    total_net_sales = (
        calculated_gross_sales
        - calculated_sales_returns
    )

    # ========================================================
    # RETURN REPORT ROWS
    # ========================================================

    return [

        {
            "voucher_no": "Cash Sales",
            "cash": cash_sales,
            "bank": 0,
            "cheque": 0,
            "credit": 0,
            "total": cash_sales,
        },

        {
            "voucher_no": "Bank Sales",
            "cash": 0,
            "bank": bank_sales,
            "cheque": 0,
            "credit": 0,
            "total": bank_sales,
        },

        {
            "voucher_no": "Cheque Sales",
            "cash": 0,
            "bank": 0,
            "cheque": cheque_sales,
            "credit": 0,
            "total": cheque_sales,
        },

        {
            "voucher_no": "Credit Sales",
            "cash": 0,
            "bank": 0,
            "cheque": 0,
            "credit": credit_sales,
            "total": credit_sales,
        },

        {
            "voucher_no": "Gross Sales",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": calculated_gross_sales,
        },

        {
            "voucher_no": "Sales Return - Cash",
            "cash": sales_return_cash,
            "bank": 0,
            "cheque": 0,
            "credit": 0,
            "total": sales_return_cash,
        },

        {
            "voucher_no": "Sales Return - Bank",
            "cash": 0,
            "bank": sales_return_bank,
            "cheque": 0,
            "credit": 0,
            "total": sales_return_bank,
        },

        {
            "voucher_no": "Sales Return - Cheque",
            "cash": 0,
            "bank": 0,
            "cheque": sales_return_cheque,
            "credit": 0,
            "total": sales_return_cheque,
        },

        {
            "voucher_no": "Sales Return - Credit",
            "cash": 0,
            "bank": 0,
            "cheque": 0,
            "credit": sales_return_credit,
            "total": sales_return_credit,
        },

        {
            "voucher_no": "Total Sales Returns",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": calculated_sales_returns,
        },

        {
            "voucher_no": "Total Net Sales",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": total_net_sales,
        },
    ]


# ============================================================
# PURCHASE SUMMARY
# ============================================================

def get_purchase_summary(filters):

    params = get_params(filters)

    user_condition = get_user_condition("pi", filters)

    # --------------------------------------------------------
    # GROSS PURCHASE
    # --------------------------------------------------------

    gross_purchase = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(pi.base_grand_total),
            0
        )

        FROM `tabPurchase Invoice` pi

        WHERE pi.docstatus = 1
            AND pi.is_return = 0
            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s
            {user_condition}
        """,
        params,
    )[0][0]

    gross_purchase = flt(gross_purchase)

    # --------------------------------------------------------
    # PURCHASE RETURN
    # --------------------------------------------------------

    purchase_returns = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(ABS(pi.base_grand_total)),
            0
        )

        FROM `tabPurchase Invoice` pi

        WHERE pi.docstatus = 1
            AND pi.is_return = 1
            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s
            {user_condition}
        """,
        params,
    )[0][0]

    purchase_returns = flt(purchase_returns)

    # --------------------------------------------------------
    # CASH PURCHASE
    # --------------------------------------------------------

    cash_purchase = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Purchase Invoice'
            AND per.reference_name = pi.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE pi.docstatus = 1
            AND pi.is_return = 0

            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cash%%'

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    cash_purchase = flt(cash_purchase)

    # --------------------------------------------------------
    # BANK PURCHASE
    # --------------------------------------------------------

    bank_purchase = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Purchase Invoice'
            AND per.reference_name = pi.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE pi.docstatus = 1
            AND pi.is_return = 0

            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'bank%%'

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    bank_purchase = flt(bank_purchase)

    # --------------------------------------------------------
    # CHEQUE PURCHASE
    # --------------------------------------------------------

    cheque_purchase = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Purchase Invoice'
            AND per.reference_name = pi.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE pi.docstatus = 1
            AND pi.is_return = 0

            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cheque%%'

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    cheque_purchase = flt(cheque_purchase)

    # --------------------------------------------------------
    # CREDIT PURCHASE
    # --------------------------------------------------------

    credit_purchase = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(
                GREATEST(
                    pi.base_grand_total
                    -
                    IFNULL(
                        (
                            SELECT SUM(per2.allocated_amount)

                            FROM `tabPayment Entry Reference` per2

                            INNER JOIN `tabPayment Entry` pe2
                                ON pe2.name = per2.parent

                            WHERE per2.reference_doctype = 'Purchase Invoice'
                                AND per2.reference_name = pi.name

                                AND pe2.docstatus = 1
                                AND pe2.payment_type = 'Pay'
                        ),
                        0
                    ),
                    0
                )
            ),
            0
        )

        FROM `tabPurchase Invoice` pi

        WHERE pi.docstatus = 1
            AND pi.is_return = 0
            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    credit_purchase = flt(credit_purchase)

    # --------------------------------------------------------
    # PURCHASE RETURN CASH
    # --------------------------------------------------------

    purchase_return_cash = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Purchase Invoice'
            AND per.reference_name = pi.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE pi.docstatus = 1
            AND pi.is_return = 1

            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cash%%'

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    purchase_return_cash = flt(purchase_return_cash)

    # --------------------------------------------------------
    # PURCHASE RETURN BANK
    # --------------------------------------------------------

    purchase_return_bank = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Purchase Invoice'
            AND per.reference_name = pi.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE pi.docstatus = 1
            AND pi.is_return = 1

            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'bank%%'

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    purchase_return_bank = flt(purchase_return_bank)

    # --------------------------------------------------------
    # PURCHASE RETURN CHEQUE
    # --------------------------------------------------------

    purchase_return_cheque = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(per.allocated_amount),
            0
        )

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_doctype = 'Purchase Invoice'
            AND per.reference_name = pi.name

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE pi.docstatus = 1
            AND pi.is_return = 1

            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND LOWER(TRIM(pe.mode_of_payment))
                LIKE 'cheque%%'

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    purchase_return_cheque = flt(purchase_return_cheque)

    # --------------------------------------------------------
    # PURCHASE RETURN CREDIT
    # --------------------------------------------------------

    purchase_return_credit = frappe.db.sql(
        f"""
        SELECT IFNULL(
            SUM(
                GREATEST(
                    ABS(pi.base_grand_total)
                    -
                    IFNULL(
                        (
                            SELECT SUM(per2.allocated_amount)

                            FROM `tabPayment Entry Reference` per2

                            INNER JOIN `tabPayment Entry` pe2
                                ON pe2.name = per2.parent

                            WHERE per2.reference_doctype = 'Purchase Invoice'
                                AND per2.reference_name = pi.name

                                AND pe2.docstatus = 1
                                AND pe2.payment_type = 'Receive'
                        ),
                        0
                    ),
                    0
                )
            ),
            0
        )

        FROM `tabPurchase Invoice` pi

        WHERE pi.docstatus = 1
            AND pi.is_return = 1

            AND pi.company = %(company)s
            AND pi.posting_date = %(posting_date)s

            {user_condition}
        """,
        params,
    )[0][0]

    purchase_return_credit = flt(purchase_return_credit)

    # --------------------------------------------------------
    # CALCULATE
    # --------------------------------------------------------

    calculated_gross_purchase = (
        cash_purchase
        + bank_purchase
        + cheque_purchase
        + credit_purchase
    )

    calculated_purchase_returns = (
        purchase_return_cash
        + purchase_return_bank
        + purchase_return_cheque
        + purchase_return_credit
    )

    total_net_purchase = (
        calculated_gross_purchase
        - calculated_purchase_returns
    )

    return [

        {
            "voucher_no": "Cash Purchases",
            "cash": cash_purchase,
            "bank": 0,
            "cheque": 0,
            "credit": 0,
            "total": cash_purchase,
        },

        {
            "voucher_no": "Bank Purchases",
            "cash": 0,
            "bank": bank_purchase,
            "cheque": 0,
            "credit": 0,
            "total": bank_purchase,
        },

        {
            "voucher_no": "Cheque Purchases",
            "cash": 0,
            "bank": 0,
            "cheque": cheque_purchase,
            "credit": 0,
            "total": cheque_purchase,
        },

        {
            "voucher_no": "Credit Purchases",
            "cash": 0,
            "bank": 0,
            "cheque": 0,
            "credit": credit_purchase,
            "total": credit_purchase,
        },

        {
            "voucher_no": "Gross Purchases",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": calculated_gross_purchase,
        },

        {
            "voucher_no": "Purchase Return - Cash",
            "cash": purchase_return_cash,
            "bank": 0,
            "cheque": 0,
            "credit": 0,
            "total": purchase_return_cash,
        },

        {
            "voucher_no": "Purchase Return - Bank",
            "cash": 0,
            "bank": purchase_return_bank,
            "cheque": 0,
            "credit": 0,
            "total": purchase_return_bank,
        },

        {
            "voucher_no": "Purchase Return - Cheque",
            "cash": 0,
            "bank": 0,
            "cheque": purchase_return_cheque,
            "credit": 0,
            "total": purchase_return_cheque,
        },

        {
            "voucher_no": "Purchase Return - Credit",
            "cash": 0,
            "bank": 0,
            "cheque": 0,
            "credit": purchase_return_credit,
            "total": purchase_return_credit,
        },

        {
            "voucher_no": "Total Purchase Returns",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": calculated_purchase_returns,
        },

        {
            "voucher_no": "Total Net Purchases",
            "cash": "",
            "bank": "",
            "cheque": "",
            "credit": "",
            "total": total_net_purchase,
        },
    ]


# ============================================================
# SALES DETAILS
# ============================================================

def get_sales_details(filters):

    params = get_params(filters)

    user_condition = get_user_condition("si", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY si.posting_date, si.name
            ) AS sl_no,

            si.name AS voucher_no,

            'Sales Invoice' AS voucher_type,

            si.customer AS particulars,

            '' AS reference,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Sales Invoice'
                    AND per.reference_name = si.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Receive'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cash%%'

            ), 0) AS cash,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Sales Invoice'
                    AND per.reference_name = si.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Receive'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'bank%%'

            ), 0) AS bank,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Sales Invoice'
                    AND per.reference_name = si.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Receive'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cheque%%'

            ), 0) AS cheque,

            GREATEST(

                si.base_grand_total

                -

                IFNULL((
                    SELECT SUM(per2.allocated_amount)

                    FROM `tabPayment Entry Reference` per2

                    INNER JOIN `tabPayment Entry` pe2
                        ON pe2.name = per2.parent

                    WHERE per2.reference_doctype = 'Sales Invoice'
                        AND per2.reference_name = si.name

                        AND pe2.docstatus = 1
                        AND pe2.payment_type = 'Receive'

                ), 0),

                0

            ) AS credit,

            si.base_grand_total AS total,

            si.owner AS account

        FROM `tabSales Invoice` si

        WHERE si.docstatus = 1
            AND si.is_return = 0

            AND si.posting_date = %(posting_date)s
            AND si.company = %(company)s

            {user_condition}

        ORDER BY si.posting_date, si.name

        """,
        params,
        as_dict=True,
    )


# ============================================================
# SALES RETURN DETAILS
# ============================================================

def get_sales_return_details(filters):

    params = get_params(filters)

    user_condition = get_user_condition("si", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY si.posting_date, si.name
            ) AS sl_no,

            si.name AS voucher_no,

            'Sales Invoice' AS voucher_type,

            si.customer AS particulars,

            si.return_against AS reference,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Sales Invoice'
                    AND per.reference_name = si.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Pay'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cash%%'

            ), 0) AS cash,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Sales Invoice'
                    AND per.reference_name = si.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Pay'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'bank%%'

            ), 0) AS bank,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Sales Invoice'
                    AND per.reference_name = si.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Pay'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cheque%%'

            ), 0) AS cheque,

            GREATEST(

                ABS(si.base_grand_total)

                -

                IFNULL((
                    SELECT SUM(per2.allocated_amount)

                    FROM `tabPayment Entry Reference` per2

                    INNER JOIN `tabPayment Entry` pe2
                        ON pe2.name = per2.parent

                    WHERE per2.reference_doctype = 'Sales Invoice'
                        AND per2.reference_name = si.name

                        AND pe2.docstatus = 1
                        AND pe2.payment_type = 'Pay'

                ), 0),

                0

            ) AS credit,

            ABS(si.base_grand_total) AS total,

            si.owner AS account

        FROM `tabSales Invoice` si

        WHERE si.docstatus = 1
            AND si.is_return = 1

            AND si.posting_date = %(posting_date)s
            AND si.company = %(company)s

            {user_condition}

        ORDER BY si.posting_date, si.name

        """,
        params,
        as_dict=True,
    )


# ============================================================
# PURCHASE DETAILS
# ============================================================

def get_purchase_details(filters):

    params = get_params(filters)

    user_condition = get_user_condition("pi", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY pi.posting_date, pi.name
            ) AS sl_no,

            pi.name AS voucher_no,

            'Purchase Invoice' AS voucher_type,

            pi.supplier AS particulars,

            pi.bill_no AS reference,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Purchase Invoice'
                    AND per.reference_name = pi.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Pay'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cash%%'

            ), 0) AS cash,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Purchase Invoice'
                    AND per.reference_name = pi.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Pay'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'bank%%'

            ), 0) AS bank,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Purchase Invoice'
                    AND per.reference_name = pi.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Pay'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cheque%%'

            ), 0) AS cheque,

            GREATEST(

                pi.base_grand_total

                -

                IFNULL((
                    SELECT SUM(per2.allocated_amount)

                    FROM `tabPayment Entry Reference` per2

                    INNER JOIN `tabPayment Entry` pe2
                        ON pe2.name = per2.parent

                    WHERE per2.reference_doctype = 'Purchase Invoice'
                        AND per2.reference_name = pi.name

                        AND pe2.docstatus = 1
                        AND pe2.payment_type = 'Pay'

                ), 0),

                0

            ) AS credit,

            pi.base_grand_total AS total,

            pi.owner AS account

        FROM `tabPurchase Invoice` pi

        WHERE pi.docstatus = 1
            AND pi.is_return = 0

            AND pi.posting_date = %(posting_date)s
            AND pi.company = %(company)s

            {user_condition}

        ORDER BY pi.posting_date, pi.name

        """,
        params,
        as_dict=True,
    )


# ============================================================
# PURCHASE RETURN
# ============================================================

def get_purchase_return(filters):

    params = get_params(filters)

    user_condition = get_user_condition("pi", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY pi.posting_date, pi.name
            ) AS sl_no,

            pi.name AS voucher_no,

            'Purchase Invoice' AS voucher_type,

            pi.supplier AS particulars,

            pi.return_against AS reference,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Purchase Invoice'
                    AND per.reference_name = pi.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Receive'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cash%%'

            ), 0) AS cash,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Purchase Invoice'
                    AND per.reference_name = pi.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Receive'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'bank%%'

            ), 0) AS bank,

            IFNULL((
                SELECT SUM(per.allocated_amount)

                FROM `tabPayment Entry Reference` per

                INNER JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent

                WHERE per.reference_doctype = 'Purchase Invoice'
                    AND per.reference_name = pi.name

                    AND pe.docstatus = 1
                    AND pe.payment_type = 'Receive'

                    AND LOWER(TRIM(pe.mode_of_payment))
                        LIKE 'cheque%%'

            ), 0) AS cheque,

            GREATEST(

                ABS(pi.base_grand_total)

                -

                IFNULL((
                    SELECT SUM(per2.allocated_amount)

                    FROM `tabPayment Entry Reference` per2

                    INNER JOIN `tabPayment Entry` pe2
                        ON pe2.name = per2.parent

                    WHERE per2.reference_doctype = 'Purchase Invoice'
                        AND per2.reference_name = pi.name

                        AND pe2.docstatus = 1
                        AND pe2.payment_type = 'Receive'

                ), 0),

                0

            ) AS credit,

            ABS(pi.base_grand_total) AS total,

            pi.owner AS account

        FROM `tabPurchase Invoice` pi

        WHERE pi.docstatus = 1
            AND pi.is_return = 1

            AND pi.posting_date = %(posting_date)s
            AND pi.company = %(company)s

            {user_condition}

        ORDER BY pi.posting_date, pi.name

        """,
        params,
        as_dict=True,
    )


# ============================================================
# CASH & BANK SUMMARY
# ============================================================

def get_cash_bank_summary(filters):

    params = get_params(filters)

    user_condition = get_user_condition("gle", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY gle.account
            ) AS sl_no,

            gle.account AS voucher_no,

            '' AS voucher_type,

            '' AS particulars,

            '' AS reference,

            CASE

                WHEN LOWER(gle.account) LIKE '%%cash%%'

                THEN SUM(gle.debit) - SUM(gle.credit)

                ELSE 0

            END AS cash,

            CASE

                WHEN LOWER(gle.account) LIKE '%%bank%%'

                THEN SUM(gle.debit) - SUM(gle.credit)

                ELSE 0

            END AS bank,

            0 AS cheque,

            0 AS credit,

            SUM(gle.debit) - SUM(gle.credit) AS total,

            '' AS account

        FROM `tabGL Entry` gle

        WHERE gle.posting_date = %(posting_date)s
            AND gle.company = %(company)s

            AND (
                LOWER(gle.account) LIKE '%%cash%%'
                OR LOWER(gle.account) LIKE '%%bank%%'
            )

            {user_condition}

        GROUP BY gle.account

        ORDER BY gle.account

        """,
        params,
        as_dict=True,
    )


# ============================================================
# RECEIPTS
# ============================================================

def get_receipt_details(filters):

    params = get_params(filters)

    user_condition = get_user_condition("pe", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY pe.posting_date, pe.name
            ) AS sl_no,

            pe.name AS voucher_no,

            'Payment Entry' AS voucher_type,

            pe.party AS particulars,

            '' AS reference,

            CASE

                WHEN LOWER(TRIM(pe.mode_of_payment))
                    LIKE 'cash%%'

                THEN pe.paid_amount

                ELSE 0

            END AS cash,

            CASE

                WHEN LOWER(TRIM(pe.mode_of_payment))
                    LIKE 'bank%%'

                THEN pe.paid_amount

                ELSE 0

            END AS bank,

            CASE

                WHEN LOWER(TRIM(pe.mode_of_payment))
                    LIKE 'cheque%%'

                THEN pe.paid_amount

                ELSE 0

            END AS cheque,

            0 AS credit,

            pe.paid_amount AS total,

            pe.paid_to AS account

        FROM `tabPayment Entry` pe

        WHERE pe.docstatus = 1
            AND pe.payment_type = 'Receive'

            AND pe.posting_date = %(posting_date)s
            AND pe.company = %(company)s

            {user_condition}

        ORDER BY pe.posting_date, pe.name

        """,
        params,
        as_dict=True,
    )


# ============================================================
# PAYMENTS
# ============================================================

def get_payment_details(filters):

    params = get_params(filters)

    user_condition = get_user_condition("pe", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY pe.posting_date, pe.name
            ) AS sl_no,

            pe.name AS voucher_no,

            'Payment Entry' AS voucher_type,

            pe.party AS particulars,

            '' AS reference,

            CASE

                WHEN LOWER(TRIM(pe.mode_of_payment))
                    LIKE 'cash%%'

                THEN pe.paid_amount

                ELSE 0

            END AS cash,

            CASE

                WHEN LOWER(TRIM(pe.mode_of_payment))
                    LIKE 'bank%%'

                THEN pe.paid_amount

                ELSE 0

            END AS bank,

            CASE

                WHEN LOWER(TRIM(pe.mode_of_payment))
                    LIKE 'cheque%%'

                THEN pe.paid_amount

                ELSE 0

            END AS cheque,

            0 AS credit,

            pe.paid_amount AS total,

            pe.paid_from AS account

        FROM `tabPayment Entry` pe

        WHERE pe.docstatus = 1
            AND pe.payment_type = 'Pay'

            AND pe.posting_date = %(posting_date)s
            AND pe.company = %(company)s

            {user_condition}

        ORDER BY pe.posting_date, pe.name

        """,
        params,
        as_dict=True,
    )


# ============================================================
# CONTRA JOURNAL ENTRY
# ============================================================

def get_contra_details(filters):

    params = get_params(filters)

    user_condition = get_user_condition("je", filters)

    return frappe.db.sql(
        f"""
        SELECT

            ROW_NUMBER() OVER (
                ORDER BY je.posting_date, je.name, a.idx
            ) AS sl_no,

            je.name AS voucher_no,

            'Journal Entry' AS voucher_type,

            a.account AS particulars,

            '' AS reference,

            CASE

                WHEN LOWER(a.account) LIKE '%%cash%%'

                THEN
                    CASE
                        WHEN a.debit > 0
                        THEN a.debit
                        ELSE a.credit
                    END

                ELSE 0

            END AS cash,

            CASE

                WHEN LOWER(a.account) LIKE '%%bank%%'

                THEN
                    CASE
                        WHEN a.debit > 0
                        THEN a.debit
                        ELSE a.credit
                    END

                ELSE 0

            END AS bank,

            0 AS cheque,

            0 AS credit,

            ABS(a.debit - a.credit) AS total,

            je.user_remark AS account

        FROM `tabJournal Entry` je

        INNER JOIN `tabJournal Entry Account` a
            ON a.parent = je.name

        WHERE je.docstatus = 1
            AND je.posting_date = %(posting_date)s
            AND je.company = %(company)s
            AND je.voucher_type = 'Contra Entry'

            {user_condition}

        ORDER BY je.name, a.idx

        """,
        params,
        as_dict=True,
    )