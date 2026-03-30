import frappe
from frappe.utils import getdate, nowtime
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
def get_all_sales_items_for_link_field(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query function for Link fields to show all sales items.
    Replaces the default item query to show comprehensive list.
    """
    try:
        all_items = get_all_sales_items(use_cache=True)

        results = []

        if txt:
            txt_lower = txt.lower()
            filtered_items = []
            for item in all_items:
                item_code = item.get("item_code", "").lower()
                item_name = item.get("item_name", "").lower()

                if item_code == txt_lower or item_name == txt_lower:
                    filtered_items.insert(0, item)
                elif item_code.startswith(txt_lower) or item_name.startswith(txt_lower):
                    filtered_items.append(item)
                elif txt_lower in item_code or txt_lower in item_name:
                    filtered_items.append(item)
            all_items = filtered_items

        for item in all_items:
            results.append(
                [
                    item.get("item_code", ""),
                    item.get("item_name", ""),
                    item.get("item_group", ""),
                    item.get("brand", ""),
                    item.get("stock_uom", ""),
                    item.get("standard_rate", 0),
                ]
            )

        return results

    except Exception as e:
        frappe.log_error(f"Error in get_all_sales_items_for_link_field: {str(e)}")

        try:
            from erpnext.controllers.queries import item_query

            return item_query(doctype, txt, searchfield, start, page_len, filters)
        except ImportError:
            conditions = ["is_sales_item = 1", "disabled = 0"]
            if txt:
                conditions.append(
                    f"({searchfield} like %(txt)s OR item_name like %(txt)s)"
                )

            query = f"""
                SELECT item_code, item_name, item_group, brand, stock_uom, standard_rate
                FROM `tabItem`
                WHERE {' AND '.join(conditions)}
                ORDER BY item_code
                LIMIT %(start)s, %(page_len)s
            """

            return frappe.db.sql(
                query,
                {
                    "txt": f"%{txt}%" if txt else "",
                    "start": int(start) if start else 0,
                    "page_len": int(page_len) if page_len else 20,
                },
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

