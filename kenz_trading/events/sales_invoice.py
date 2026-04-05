import json
import frappe
from frappe.utils import getdate, nowtime, flt
from frappe import _
from num2words import num2words

# Will be set by monkey_patches.apply() to store the original ERPNext item_query
_original_item_query = None

@frappe.whitelist()
def get_default_branch(user):
    branch = frappe.db.get_value("User Permission", {"user":user,"allow":"Branch"}, "for_value")
    return branch if branch else None

 
@frappe.whitelist()
def get_uoms(item_code):
    uoms = frappe.get_all("UOM Conversion Detail", filters={"parent": item_code}, fields=["uom", "conversion_factor"])
    return uoms


def apply_payment_mode_rules(doc, method=None):
    """
    Keep Sales Invoice payment behaviour aligned with the custom Payment Mode field.

    - Cash  -> Normal invoice (not POS). A separate Payment Entry is created on submit.
    - Credit -> Normal credit invoice with no payments so it stays Unpaid.
    """

    # Skip credit-note scenarios
    if doc.is_return:
        return

    # Nothing to do if the custom field is empty
    if not getattr(doc, "custom_payment_mode", None):
        return

    if doc.custom_payment_mode == "Cash":
        # Cash invoices are NOT POS - a separate Payment Entry will be created on submit
        doc.is_pos = 0
        doc.set("payments", [])

    elif doc.custom_payment_mode == "Credit":
        # Credit invoices should behave like standard credit sales
        doc.is_pos = 0
        doc.set("payments", [])


 

def create_payment_entry_for_cash(doc, method=None):
    """
    Auto-create a separate Payment Entry for Cash invoices on submit.
    """
    if doc.is_return:
        return

    if not getattr(doc, "custom_payment_mode", None) or doc.custom_payment_mode != "Cash":
        return

    mode_of_payment = doc.get("custom_mode_of_payment") or "Cash"
    if not frappe.db.exists("Mode of Payment", mode_of_payment):
        frappe.throw(_("Please select a valid Mode of Payment for cash invoices."))

    paid_account = None
    if doc.company:
        paid_account = frappe.db.get_value(
            "Mode of Payment Account",
            {"parent": mode_of_payment, "company": doc.company},
            "default_account",
        )

    if not paid_account:
        frappe.throw(
            _(
                "Default Account is required for Mode of Payment {0} in Company {1}."
            ).format(mode_of_payment, doc.company or "")
        )

    payable_amount = flt(doc.rounded_total or doc.grand_total or 0)

    if payable_amount <= 0:
        return

    # Get the debit_to account from the Sales Invoice
    debit_to = doc.debit_to

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.party_type = "Customer"
    pe.party = doc.customer
    pe.company = doc.company
    pe.posting_date = doc.posting_date
    pe.mode_of_payment = mode_of_payment
    pe.paid_from = debit_to
    pe.paid_to = paid_account
    pe.paid_amount = payable_amount
    pe.received_amount = payable_amount
    pe.reference_no = doc.name
    pe.reference_date = doc.posting_date

    pe.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": doc.name,
        "total_amount": doc.grand_total,
        "outstanding_amount": payable_amount,
        "allocated_amount": payable_amount,
    })

    pe.insert(ignore_permissions=True)
    pe.submit()

    frappe.msgprint(
        _("Payment Entry {0} created for Cash Invoice {1}").format(
            frappe.utils.get_link_to_form("Payment Entry", pe.name), doc.name
        ),
        alert=True,
    )


@frappe.whitelist()
def on_submits(doc, method):


    # # =====================================================
    # # ✅ DELIVERY NOTE AUTO CREATE (NEW)
    # # =====================================================
    if frappe.db.get_single_value("Kenza Settings", "enable_auto_create_dn"):

        if frappe.db.exists("Delivery Note Item", {"against_sales_invoice": doc.name}):
            return

        available_items = []
        pending_items = []

        for item in doc.items:
            if not item.item_code or not item.warehouse:
                continue

            available_qty = frappe.db.get_value(
                "Bin",
                {"item_code": item.item_code, "warehouse": item.warehouse},
                "actual_qty"
            ) or 0

            available_qty = float(available_qty)

            if available_qty >= item.qty:
                available_items.append((item, item.qty))

            elif available_qty > 0:
                available_items.append((item, available_qty))
                pending_items.append((item, item.qty - available_qty))

            else:
                pending_items.append((item, item.qty))

        if available_items:
            dn = frappe.new_doc("Delivery Note")
            dn.customer = doc.customer
            dn.company = doc.company
            dn.posting_date = doc.posting_date

            for item, qty in available_items:
                dn.append("items", {
                    "item_code": item.item_code,
                    "qty": qty,
                    "rate": item.rate,
                    "warehouse": item.warehouse,
                    "against_sales_invoice": doc.name,
                    "si_detail": item.name
                })

            dn.insert(ignore_permissions=True)
            dn.submit()

        if pending_items:
            dn = frappe.new_doc("Delivery Note")
            dn.customer = doc.customer
            dn.company = doc.company
            dn.posting_date = doc.posting_date

            for item, qty in pending_items:
                dn.append("items", {
                    "item_code": item.item_code,
                    "qty": qty,
                    "rate": item.rate,
                    "warehouse": item.warehouse,
                    "against_sales_invoice": doc.name,
                    "si_detail": item.name
                })

            dn.insert(ignore_permissions=True)
        frappe.msgprint("Delivery Note Created")






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


    value = frappe.db.get_single_value("Kenza Settings", "enable_auto_create_dn")
    # frappe.msgprint(f"DN Setting Value: {value}")




   



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
    pass

    # value = frappe.db.get_single_value("Kenza Settings", "enable_auto_create_dn")
    # frappe.msgprint(f"DN Setting Value: {value}")


    # pass
#     user_branch = frappe.defaults.get_user_default("Branch")

#     for row in doc.items:
#         branch_rows = frappe.db.get_all(
#             "Branches",
#             filters={"parent": row.item_code},
#             pluck="branch"
#         )

#         # OPEN item → allowed
#         if not branch_rows:
#             continue

#         if user_branch not in branch_rows:
#             frappe.throw(
#                 f"Item {row.item_code} not allowed for Branch {user_branch}"
#             )


@frappe.whitelist()
def get_item_details_for_sales_invoice(item_code, customer=None, company=None, currency=None):
    """
    Get item details including pricing information for sales invoice
    """
    if not item_code:
        return {}

    item_code = str(item_code).strip()
    if not item_code or len(item_code) < 2:
        return {}

    try:
        if not frappe.db.exists("Item", item_code):
            return {}

        item = frappe.get_doc("Item", item_code)
        if not item or not item.is_sales_item:
            return {}

        result = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "stock_uom": item.stock_uom,
            "is_stock_item": item.is_stock_item,
            "standard_rate": item.standard_rate or 0,
            "item_group": item.item_group,
            "brand": item.brand,
        }

        if company:
            try:
                company_doc = frappe.get_doc("Company", company)
                if company_doc.default_income_account:
                    result["income_account"] = company_doc.default_income_account
            except Exception as e:
                frappe.log_error(f"Error getting company default income account: {str(e)}")

        if customer and company:
            try:
                customer_doc = frappe.get_doc("Customer", customer)
                price_list = customer_doc.default_price_list

                if not price_list:
                    company_doc = frappe.get_doc("Company", company)
                    price_list = company_doc.default_selling_price_list

                if not price_list:
                    selling_settings = frappe.get_single("Selling Settings")
                    if selling_settings and selling_settings.selling_price_list:
                        price_list = selling_settings.selling_price_list

                if price_list:
                    item_price = frappe.db.get_value(
                        "Item Price",
                        {"item_code": item_code, "price_list": price_list, "selling": 1},
                        "price_list_rate",
                    )

                    if item_price:
                        result["rate"] = item_price
                        result["price_list"] = price_list
                        result["price_list_rate"] = item_price
                    else:
                        result["rate"] = item.standard_rate or 0
                else:
                    result["rate"] = item.standard_rate or 0
            except Exception as e:
                frappe.log_error(f"Error getting pricing details: {str(e)}")
                result["rate"] = item.standard_rate or 0
        else:
            result["rate"] = item.standard_rate or 0

        if item.is_stock_item and company:
            try:
                from erpnext.stock.utils import get_stock_balance

                stock_qty = get_stock_balance(item_code, company=company)
                result["stock_qty"] = stock_qty
            except Exception as e:
                frappe.log_error(f"Error getting stock quantity: {str(e)}")
                result["stock_qty"] = 0

        return result

    except Exception as e:
        frappe.log_error(f"Error in get_item_details_for_sales_invoice: {str(e)}")
        return {}


@frappe.whitelist()
def get_all_sales_items(use_cache=True):
    """
    Get ALL sales items for dropdown - comprehensive list without pagination.
    Implements caching for performance optimization.
    """
    cache_key = "all_sales_items_for_invoice"

    if use_cache:
        cached_items = frappe.cache().get_value(cache_key)
        if cached_items:
            return cached_items

    try:
        query = """
            SELECT
                item_code,
                item_name,
                COALESCE(standard_rate, 0) as standard_rate,
                stock_uom,
                item_group,
                brand,
                modified
            FROM `tabItem`
            WHERE is_sales_item = 1
            AND disabled = 0
            ORDER BY item_code ASC
        """

        all_items = frappe.db.sql(query, as_dict=True)

        if use_cache and all_items:
            frappe.cache().set_value(cache_key, all_items, expires_in_sec=1800)

        return all_items

    except Exception as e:
        frappe.log_error(f"Error getting all sales items: {str(e)}")
        return []


@frappe.whitelist()
def clear_items_cache():
    """Clear the cached items list"""
    cache_key = "all_sales_items_for_invoice"
    frappe.cache().delete_value(cache_key)
    return {"status": "success", "message": "Items cache cleared"}


@frappe.whitelist()
def custom_item_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Override of erpnext.controllers.queries.item_query.
    Routes sales item queries to our custom function that shows ALL items.
    Falls through to ERPNext default for everything else (Stock Ledger, reports, etc.)
    """
    if isinstance(filters, str):
        filters = json.loads(filters)

    # Only override for sales item contexts (Sales Invoice, Sales Order, Quotation, etc.)
    if filters and (filters.get("is_sales_item") or filters.get("is_purchase_item")):
        return get_all_sales_items_for_link_field(doctype, txt, searchfield, start, page_len, filters)

    # Fall through to ERPNext default
    return _original_item_query(doctype, txt, searchfield, start, page_len, filters)


@frappe.whitelist()
def get_all_sales_items_for_link_field(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query function for Link fields to show all items.
    Bypasses ERPNext default filters (customer, has_variants, etc.).
    Items starting with the search text appear first.
    """
    if isinstance(filters, str):
        filters = json.loads(filters)

    start = int(start or 0)
    # Show all matching items instead of Frappe's default page_length of 10
    page_len = 999

    conditions = ["i.disabled = 0"]

    # Apply sales/purchase filter based on context
    if filters and filters.get("is_purchase_item"):
        conditions.append("i.is_purchase_item = 1")
    else:
        conditions.append("i.is_sales_item = 1")

    if txt:
        conditions.append(
            "(i.name LIKE %(txt)s OR i.item_name LIKE %(txt)s OR i.item_group LIKE %(txt)s)"
        )

    where_clause = " AND ".join(conditions)

    # Order: exact match first, then starts-with, then contains
    order_clause = "i.name ASC"
    if txt:
        order_clause = """
            CASE
                WHEN i.name = %(exact_txt)s OR i.item_name = %(exact_txt)s THEN 0
                WHEN i.item_name LIKE %(starts_txt)s THEN 1
                WHEN i.name LIKE %(starts_txt)s THEN 2
                ELSE 3
            END,
            i.item_name ASC
        """

    query = f"""
        SELECT
            i.name AS item_code,
            i.item_name,
            i.item_group,
            i.brand,
            i.stock_uom,
            COALESCE(i.standard_rate, 0) AS standard_rate
        FROM `tabItem` i
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT %(page_len)s OFFSET %(start)s
    """

    params = {
        "txt": f"%{txt}%" if txt else "%",
        "exact_txt": txt or "",
        "starts_txt": f"{txt}%" if txt else "%",
        "start": start,
        "page_len": page_len,
    }

    items = frappe.db.sql(query, params, as_dict=True)

    # Get total count for this search
    count_query = f"""
        SELECT COUNT(*) as total
        FROM `tabItem` i
        WHERE {where_clause}
    """
    total = frappe.db.sql(count_query, params, as_dict=True)[0].total

    results = []
    for item in items:
        item_name = item.get("item_name", "")
        item_group = item.get("item_group", "")

        # Mark items whose name starts with the search text
        display_info = item_group
        if txt and item_name.lower().startswith(txt.lower()):
            display_info = f"{item_group} | Total: {total} items found"

        results.append([
            item.get("item_code", ""),
            item_name,
            display_info,
            item.get("brand", ""),
            item.get("stock_uom", ""),
            item.get("standard_rate", 0),
        ])

    return results


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
