import frappe
from frappe.utils import getdate, nowtime, flt, cint, round_based_on_smallest_currency_fraction
from frappe import _
from num2words import num2words

@frappe.whitelist()
def get_default_branch(user):
    branch = frappe.db.get_value("User Permission", {"user":user,"allow":"Branch"}, "for_value")
    return branch if branch else None

 
@frappe.whitelist()
def get_uoms(item_code):
    uoms = frappe.get_all("UOM Conversion Detail", filters={"parent": item_code}, fields=["uom", "conversion_factor"])
    return uoms




@frappe.whitelist()
def on_submits(doc, method):
    # Fix inclusive tax rounding and force-save to database.
    # The validate/before_submit hooks may not persist because ERPNext
    # recalculates after hooks run.  on_submit runs after db_update(),
    # so we correct values here and write them directly to the database.
    _force_fix_inclusive_tax_on_submit(doc)

    # ✅ Item Variants section
    if frappe.db.get_single_value("Kenza Settings", "activate_item_variant_save"):
        for row in doc.items:
            if not row.custom_remark or not row.item_code:
                continue

            # Avoid duplicate variant for same invoice + remark
            variant = frappe.db.get_value(
                "Item Variants",
                {"variant_name": row.custom_remark, "main_item": row.item_code},
                "name"
            )

            if not variant:
                iv = frappe.new_doc("Item Variants")
                iv.variant_name = row.custom_remark
                iv.main_item = row.item_code
                iv.customer = doc.customer
            else:
                iv = frappe.get_doc("Item Variants", variant)

            # ✅ Add row to Variant List child table
            iv.append("variant_list", {
                "invoice_no": doc.name,
                "rate": row.rate,
                "date": getdate(doc.posting_date),
                "time": nowtime()
            })

            iv.save(ignore_permissions=True)

    # ✅ Payment Entry section (independent)
    if not frappe.db.get_single_value("Kenza Settings", "auto_create_payment"):
        return

    if doc.is_return:
        return

    if not doc.custom_mode_of_payment:
        return

    if not doc.outstanding_amount or doc.outstanding_amount <= 0:
        return

    paid_to_account = frappe.db.get_value(
        "Mode of Payment Account",
        {
            "parent": doc.custom_mode_of_payment,   # Mode of Payment
            "company": doc.company
        },
        "default_account"
    )

    if not paid_to_account:
        frappe.throw(
            f"Default Account not set for Mode of Payment <b>{doc.custom_mode_of_payment}</b>"
        )

    paid_from_account = frappe.db.get_value(
        "Company",
        doc.company,
        "default_receivable_account"
    )

    if not paid_from_account:
        frappe.throw(
            f"Default Receivable Account not set for Company <b>{doc.company}</b>"
        )

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.posting_date = doc.posting_date
    pe.mode_of_payment = doc.custom_mode_of_payment
    pe.party_type = "Customer"
    pe.party = doc.customer
    pe.paid_to = paid_to_account
    pe.paid_to_account_currency = doc.currency
    pe.paid_from = paid_from_account
    pe.paid_from_account_currency = doc.currency
    pe.paid_amount = doc.outstanding_amount
    pe.received_amount = doc.outstanding_amount
    pe.source_exchange_rate = 1
    pe.target_exchange_rate = 1

    if doc.custom_mode_of_payment == "Cheque":
        pe.reference_no = doc.custom_cheque_number
        pe.reference_date = doc.custom_cheque_date
    else:
        pe.reference_no = doc.name
        pe.reference_date = doc.posting_date

    pe.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": doc.name,
        "total_amount": doc.grand_total,
        "outstanding_amount": doc.outstanding_amount,
        "allocated_amount": doc.outstanding_amount
    })

    pe.insert()
    pe.submit()

    frappe.msgprint(f"Payment Entry <b>{pe.name}</b> created successfully", indicator="green")


   



@frappe.whitelist()
def get_last_variant_transactions(customer, item_code):

    # ✅ Check Kenza Settings checkbox first
    show_table = frappe.db.get_single_value(
        "Kenza Settings",
        "show_item_variant_table"
    )

    # If checkbox is NOT enabled, return empty list
    if not show_table:
        return []

    return frappe.db.sql("""
        SELECT 
            iv.variant_name,
            IFNULL(vl.invoice_no, vl.name) AS s_invoice_no,
            vl.rate,
            vl.date AS submitted_date,
            vl.time AS submitted_time
        FROM `tabItem Variants` iv
        INNER JOIN `tabVariant List` vl
            ON vl.parent = iv.name
        INNER JOIN (
            SELECT 
                parent,
                MAX(CONCAT(date,' ',time)) AS last_dt
            FROM `tabVariant List`
            GROUP BY parent
        ) latest
            ON latest.parent = vl.parent
            AND CONCAT(vl.date,' ',vl.time) = latest.last_dt
        WHERE 
            iv.customer = %s
            AND iv.main_item = %s
        ORDER BY vl.date DESC, vl.time DESC
    """, (customer, item_code), as_dict=True)



@frappe.whitelist()
def get_last_sales_details(customer=None, item_code=None, warehouse=None, from_date=None, to_date=None):



    condition = " WHERE si.docstatus = 1 "
    filters = []

    if customer:
        condition += " AND si.customer = %s"
        filters.append(customer)

    if item_code:
        condition += " AND sii.item_code = %s"
        filters.append(item_code)

    if warehouse:
        condition += " AND sii.warehouse = %s"
        filters.append(warehouse)

    if from_date and to_date:
        condition += " AND si.posting_date BETWEEN %s AND %s"
        filters.append(from_date)
        filters.append(to_date)

    query = f"""
        SELECT
            si.posting_date,
            si.name,
            si.customer,
            sii.item_code,
            sii.qty,
            sii.amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        {condition}
        ORDER BY si.posting_date DESC
    """

    return frappe.db.sql(query, filters, as_dict=True)




@frappe.whitelist()
def get_last_purchase_details(supplier=None, item_code=None, warehouse=None, from_date=None, to_date=None):

    conditions = []
    values = {}

    if supplier:
        conditions.append("pi.supplier = %(supplier)s")
        values["supplier"] = supplier

    if item_code:
        conditions.append("pii.item_code = %(item_code)s")
        values["item_code"] = item_code

    if warehouse:
        conditions.append("pii.warehouse = %(warehouse)s")
        values["warehouse"] = warehouse

    # ✅ Date range filter
    if from_date and to_date:
        conditions.append("pi.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = from_date
        values["to_date"] = to_date

    elif from_date:
        conditions.append("pi.posting_date >= %(from_date)s")
        values["from_date"] = from_date

    elif to_date:
        conditions.append("pi.posting_date <= %(to_date)s")
        values["to_date"] = to_date

    condition_str = " AND ".join(conditions)
    if condition_str:
        condition_str = " AND " + condition_str

    return frappe.db.sql(f"""
        SELECT
            pi.posting_date,
            pi.name,
            pi.supplier,
            pii.item_code,
            pii.qty,
            pii.amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE
            pi.docstatus = 1
            {condition_str}
        ORDER BY
            pi.posting_date DESC,
            pi.creation DESC
    """, values, as_dict=True)








@frappe.whitelist()
def get_last_purchase_and_sales(item_code, supplier=None, customer=None):
    """
    Fetch last 5 submitted Purchase Invoices and last 5 submitted Sales Invoices for a given item.
    Optionally filter by supplier (for purchases) and customer (for sales).
    If customer filter gives less than 5, fill the remaining from general sales.
    Returns a dict with 'purchases' and 'sales' lists.
    """

    # --- Purchase Section ---
    purchase_filters = """
        WHERE pii.item_code = %(item_code)s AND pi.docstatus = 1
    """
    purchase_params = { "item_code": item_code }
    if supplier:
        purchase_filters += " AND pi.supplier = %(supplier)s"
        purchase_params["supplier"] = supplier

    purchases = frappe.db.sql(f"""
        SELECT 
            pii.item_code,
            pii.parent AS purchase_invoice_no,
            pi.posting_date,
            pi.supplier,
            pii.uom,
            pii.qty,
            pii.rate,
            pi.creation
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        {purchase_filters}
        ORDER BY pi.creation DESC
        LIMIT 5
    """, purchase_params, as_dict=True)

    # --- Sales Section ---
    sales = []
    if customer:
        # First: Get sales invoices filtered by customer
        sales_filtered = frappe.db.sql(f"""
            SELECT 
                sii.item_code,
                sii.parent AS sales_invoice_no,
                si.posting_date,
                cust.customer_name AS customer,
                sii.uom,
                sii.qty,
                sii.rate,
                si.creation
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON si.name = sii.parent
            LEFT JOIN `tabCustomer` cust ON cust.name = si.customer
            WHERE sii.item_code = %(item_code)s AND si.docstatus = 1 AND si.is_return = 0
            AND si.customer = %(customer)s
            ORDER BY si.creation DESC
            LIMIT 5
        """, { "item_code": item_code, "customer": customer }, as_dict=True)

        sales.extend(sales_filtered)

        # Second: If less than 5, fetch more without customer filter
        if len(sales_filtered) < 5:
            fetched_ids = [s["sales_invoice_no"] for s in sales_filtered]
            placeholders = ", ".join(["%s"] * len(fetched_ids)) if fetched_ids else "''"
            extra_sales = frappe.db.sql(f"""
                SELECT 
                    sii.item_code,
                    sii.parent AS sales_invoice_no,
                    si.posting_date,
                    cust.customer_name AS customer,
                    sii.uom,
                    sii.qty,
                    sii.rate,
                    si.creation
                FROM `tabSales Invoice Item` sii
                JOIN `tabSales Invoice` si ON si.name = sii.parent
                LEFT JOIN `tabCustomer` cust ON cust.name = si.customer
                WHERE sii.item_code = %s AND si.docstatus = 1 AND si.is_return = 0
                AND si.name NOT IN ({placeholders})
                ORDER BY si.creation DESC
                LIMIT %s
            """, [item_code] + fetched_ids + [5 - len(sales_filtered)], as_dict=True)

            sales.extend(extra_sales)
    else:
        # No customer filter: fetch latest 5 sales invoices
        sales = frappe.db.sql(f"""
            SELECT 
                sii.item_code,
                sii.parent AS sales_invoice_no,
                si.posting_date,
                cust.customer_name AS customer,
                sii.uom,
                sii.qty,
                sii.rate,
                si.creation
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON si.name = sii.parent
            LEFT JOIN `tabCustomer` cust ON cust.name = si.customer
            WHERE sii.item_code = %(item_code)s AND si.docstatus = 1 AND si.is_return = 0
            ORDER BY si.creation DESC
            LIMIT 5
        """, { "item_code": item_code }, as_dict=True)

    return {
        'purchases': purchases,
        'sales': sales
    }




@frappe.whitelist()
def get_last_sales_invoice_rate(item_code):
    if not item_code:
        return None

    last_rate = frappe.db.sql("""
        SELECT sii.rate
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE sii.item_code=%s
          AND si.docstatus=1
        ORDER BY si.posting_date DESC, si.creation DESC
        LIMIT 1
    """, item_code, as_dict=True)

    if last_rate:
        return last_rate[0].rate
    return None



@frappe.whitelist()
def get_items_by_branch(doctype, txt, searchfield, start, page_len, filters):
    branch = filters.get("branch")

    if not branch:
        return []

    return frappe.db.sql("""
        SELECT
            i.name,
            i.item_name
        FROM `tabItem` i
        INNER JOIN `tabBranches` ib
            ON ib.parent = i.name
        WHERE
            ib.branch = %(branch)s
            AND i.disabled = 0
            AND (
                i.name LIKE %(txt)s
                OR i.item_name LIKE %(txt)s
            )
        ORDER BY i.name
        LIMIT %(page_len)s OFFSET %(start)s
    """, {
        "branch": branch,
        "txt": f"%{txt}%",
        "page_len": page_len,
        "start": start
    })





@frappe.whitelist()
def validate_item_branch(doc, method):
    fix_inclusive_tax_rounding(doc)


def before_submit_fix(doc, method):
    """Re-apply inclusive tax rounding fix just before submit save.

    During submit, ERPNext's calculate_taxes_and_totals() recalculates
    from scratch, reintroducing rounding errors. The validate hook fix
    may be overwritten by other apps' hooks that run later. This
    before_submit hook ensures the fix is the last modification before
    the database write.
    """
    fix_inclusive_tax_rounding(doc)


def _force_fix_inclusive_tax_on_submit(doc):
    """Apply inclusive tax rounding fix and write corrected values directly to DB.

    on_submit runs after the document is already saved to the database.
    We re-run the fix on the in-memory doc, then push the corrected values
    straight into the database using db_set / SQL so nothing can overwrite them.
    """
    if not doc.get("taxes"):
        return

    has_inclusive = any(cint(t.included_in_print_rate) for t in doc.taxes)
    if not has_inclusive:
        return

    # Snapshot values before fix
    old_gt = doc.grand_total

    fix_inclusive_tax_rounding(doc)

    # If grand_total didn't change, nothing to do
    if doc.grand_total == old_gt:
        return

    # Adjust outstanding_amount by the same delta as grand_total
    gt_change = flt(doc.grand_total - old_gt, doc.precision("grand_total"))
    doc.outstanding_amount = flt(
        flt(doc.outstanding_amount) + gt_change, doc.precision("outstanding_amount")
    )

    # Force-write corrected parent fields to the database
    frappe.db.set_value(
        "Sales Invoice",
        doc.name,
        {
            "net_total": doc.net_total,
            "base_net_total": doc.base_net_total,
            "grand_total": doc.grand_total,
            "base_grand_total": doc.base_grand_total,
            "total_taxes_and_charges": doc.total_taxes_and_charges,
            "base_total_taxes_and_charges": doc.base_total_taxes_and_charges,
            "outstanding_amount": doc.outstanding_amount,
            "rounded_total": doc.rounded_total,
            "base_rounded_total": doc.base_rounded_total,
            "rounding_adjustment": doc.rounding_adjustment,
            "base_rounding_adjustment": doc.base_rounding_adjustment,
        },
        update_modified=False,
    )

    # Force-write corrected item rows
    for row in doc.items:
        frappe.db.set_value(
            "Sales Invoice Item",
            row.name,
            {
                "net_amount": row.net_amount,
                "base_net_amount": row.base_net_amount,
                "net_rate": row.net_rate,
                "base_net_rate": row.base_net_rate,
            },
            update_modified=False,
        )

    # Force-write corrected tax rows
    for tax in doc.taxes:
        frappe.db.set_value(
            "Sales Taxes and Charges",
            tax.name,
            {
                "tax_amount": tax.tax_amount,
                "base_tax_amount": tax.base_tax_amount,
                "tax_amount_after_discount_amount": tax.tax_amount_after_discount_amount,
                "base_tax_amount_after_discount_amount": tax.base_tax_amount_after_discount_amount,
                "total": tax.total,
                "base_total": tax.base_total,
            },
            update_modified=False,
        )


def fix_inclusive_tax_rounding(doc):
    """Fix rounding discrepancy for inclusive taxes at row and document level.

    ERPNext back-calculates net_amount per row when tax is included in rate.
    Per-row rounding causes:
    1. Row-level: total_amount (net_amount + tax_amount) != amount (rate * qty)
    2. Doc-level: net_total (sum of per-row net_amounts) drifts from the
       mathematically correct value (grand_total / (1 + rate/100)), making
       total_taxes_and_charges wrong even when grand_total is correct.

    This fixes per-row total_amount, then recalculates net_total and
    total_taxes_and_charges from grand_total using the actual tax rate.
    """
    if not doc.get("taxes"):
        return

    has_inclusive = False
    has_non_inclusive = False
    inclusive_rate = 0.0

    for tax in doc.taxes:
        if cint(tax.included_in_print_rate):
            has_inclusive = True
            inclusive_rate += flt(tax.rate)
        else:
            has_non_inclusive = True

    if not has_inclusive:
        return

    # --- Fix 1: Per-row total_amount ---
    # When all taxes are inclusive, amount (rate * qty) is the correct inclusive
    # total. But net_amount + tax_amount can differ by 0.01 due to rounding in
    # the back-calculation. Adjust tax_amount to absorb the rounding difference
    # so that total_amount == amount.
    if not has_non_inclusive:
        meta = frappe.get_meta(doc.items[0].doctype) if doc.items else None
        if meta and meta.has_field("total_amount"):
            for row in doc.items:
                expected_total = flt(row.amount, row.precision("total_amount"))
                current_total = flt(row.total_amount, row.precision("total_amount"))
                if current_total != expected_total:
                    row.tax_amount = flt(
                        row.amount - row.net_amount, row.precision("tax_amount")
                    )
                    row.total_amount = flt(
                        row.net_amount + row.tax_amount, row.precision("total_amount")
                    )

    # --- Fix 2: Document-level grand_total ---
    # Ensure grand_total = total + non-inclusive taxes
    non_inclusive_tax_amount = 0.0
    for tax in doc.taxes:
        if not cint(tax.included_in_print_rate):
            non_inclusive_tax_amount += flt(tax.tax_amount_after_discount_amount)

    expected_grand_total = flt(doc.total + non_inclusive_tax_amount, doc.precision("grand_total"))
    gt_diff = flt(expected_grand_total - doc.grand_total, doc.precision("grand_total"))

    if gt_diff:
        max_allowed_diff = len(doc.items) * 0.01
        if abs(gt_diff) <= max_allowed_diff:
            doc.grand_total = expected_grand_total
            doc.base_grand_total = flt(
                doc.grand_total * doc.conversion_rate, doc.precision("base_grand_total")
            )

    # --- Fix 3: Net/tax split from grand_total ---
    # When all taxes are inclusive, recalculate the correct tax and net amounts
    # from grand_total using the tax rate, instead of relying on the sum of
    # per-row back-calculated net_amounts which accumulates rounding errors.
    if has_non_inclusive or inclusive_rate <= 0:
        # Mixed inclusive/non-inclusive: fall back to simple recalc
        doc.total_taxes_and_charges = flt(
            doc.grand_total - doc.net_total, doc.precision("total_taxes_and_charges")
        )
        doc.base_total_taxes_and_charges = flt(
            doc.total_taxes_and_charges * doc.conversion_rate,
            doc.precision("base_total_taxes_and_charges"),
        )
        return

    correct_tax = flt(
        doc.grand_total * inclusive_rate / (100 + inclusive_rate),
        doc.precision("total_taxes_and_charges"),
    )
    correct_net = flt(doc.grand_total - correct_tax, doc.precision("net_total"))

    net_diff = flt(correct_net - doc.net_total, doc.precision("net_total"))

    if not net_diff and not gt_diff:
        return

    # Safety: accumulated rounding should not exceed a reasonable bound
    if abs(net_diff) > len(doc.items) * 0.10:
        return

    # Fix document-level amounts
    doc.net_total = correct_net
    doc.base_net_total = flt(
        correct_net * doc.conversion_rate, doc.precision("base_net_total")
    )
    doc.total_taxes_and_charges = correct_tax
    doc.base_total_taxes_and_charges = flt(
        correct_tax * doc.conversion_rate,
        doc.precision("base_total_taxes_and_charges"),
    )

    # Absorb the net rounding difference in the last item row so that
    # net_total == sum of row net_amounts
    if net_diff and doc.items:
        last_item = doc.items[-1]
        last_item.net_amount = flt(
            last_item.net_amount + net_diff, last_item.precision("net_amount")
        )
        last_item.base_net_amount = flt(
            last_item.net_amount * doc.conversion_rate,
            last_item.precision("base_net_amount"),
        )
        if flt(last_item.qty):
            last_item.net_rate = flt(
                last_item.net_amount / last_item.qty, last_item.precision("net_rate")
            )
            last_item.base_net_rate = flt(
                last_item.net_rate * doc.conversion_rate,
                last_item.precision("base_net_rate"),
            )
        last_item.tax_amount = flt(
            last_item.amount - last_item.net_amount, last_item.precision("tax_amount")
        )
        last_item.total_amount = flt(
            last_item.net_amount + last_item.tax_amount,
            last_item.precision("total_amount"),
        )

    # Fix tax rows — distribute correct_tax proportionally across inclusive rows
    for tax in doc.taxes:
        if not cint(tax.included_in_print_rate):
            continue
        if inclusive_rate:
            row_tax = flt(
                correct_tax * flt(tax.rate) / inclusive_rate,
                tax.precision("tax_amount"),
            )
        else:
            row_tax = correct_tax
        tax.tax_amount = row_tax
        tax.tax_amount_after_discount_amount = row_tax
        tax.base_tax_amount = flt(
            row_tax * doc.conversion_rate, tax.precision("base_tax_amount")
        )
        tax.base_tax_amount_after_discount_amount = flt(
            row_tax * doc.conversion_rate,
            tax.precision("base_tax_amount_after_discount_amount"),
        )
        tax.total = flt(doc.grand_total, tax.precision("total"))
        tax.base_total = flt(
            doc.grand_total * doc.conversion_rate, tax.precision("base_total")
        )

    # Recalculate rounded_total and rounding_adjustment
    if doc.meta.get_field("rounded_total") and not doc.is_rounded_total_disabled():
        doc.rounded_total = round_based_on_smallest_currency_fraction(
            doc.grand_total, doc.currency, doc.precision("rounded_total")
        )
        doc.rounding_adjustment = flt(
            doc.rounded_total - doc.grand_total, doc.precision("rounding_adjustment")
        )
        doc.base_rounded_total = flt(
            doc.rounded_total * doc.conversion_rate, doc.precision("base_rounded_total")
        )
        doc.base_rounding_adjustment = flt(
            doc.rounding_adjustment * doc.conversion_rate,
            doc.precision("base_rounding_adjustment"),
        )


@frappe.whitelist()
def item_query_by_branch(doctype, txt, searchfield, start, page_len, filters):
    branch = filters.get("branch")

    return frappe.db.sql("""
        SELECT DISTINCT i.name, i.item_name
        FROM `tabItem` i
        INNER JOIN `tabBranches` ib
            ON ib.parent = i.name
        WHERE
            ib.branch = %(branch)s
            AND (i.name LIKE %(txt)s OR i.item_name LIKE %(txt)s)
        LIMIT %(start)s, %(page_len)s
    """, {
        "branch": branch,
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })


# @frappe.whitelist()
# def customer_query_by_branch(doctype, txt, searchfield, start, page_len, filters):
#     branch = filters.get("branch")

#     return frappe.db.sql("""
#         SELECT DISTINCT c.name, c.customer_name
#         FROM `tabCustomer` c
#         INNER JOIN `tabCustomer Branches` cb
#             ON cb.parent = c.name
#         WHERE
#             cb.branch = %(branch)s
#             AND (c.name LIKE %(txt)s OR c.customer_name LIKE %(txt)s)
#         LIMIT %(start)s, %(page_len)s
#     """, {
#         "branch": branch,
#         "txt": f"%{txt}%",
#         "start": start,
#         "page_len": page_len
#     })


