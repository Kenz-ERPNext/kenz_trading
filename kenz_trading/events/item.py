import frappe
from erpnext.stock.doctype.item.item import Item
import re




# KENZ SETTINGS BASED USER BRANCH SETTING////////////////////////

# def get_permission_query_conditions(user=None):
#     if not user:
#         user = frappe.session.user

#     # Full access for Administrator
#     if user == "Administrator":
#         return None

#     settings = frappe.get_single("Kenza Settings")
#     allowed_branches = [
#         u.branch for u in settings.user_default_branch if u.user == user
#     ]

#     if not allowed_branches:
#         return None

#     branch_list = "', '".join(allowed_branches)

#     return f"""
#         (`tabItem`.name IN (
#             SELECT parent FROM `tabBranches`
#             WHERE branch IN ('{branch_list}')
#         )
#         OR `tabItem`.name NOT IN (
#             SELECT DISTINCT parent FROM `tabBranches`
#         ))
#     """
 




def get_permission_query_conditions(user):
    if user == "Administrator":
        return ""

    # Set user for testing
    user = "s@gmail.com"
    user_branch = frappe.defaults.get_user_default("Branch", user)
    print("User Branch:", user_branch)

    if not user_branch:
        return ""

    # Fetch all items with their assigned branches
    items_with_branches = frappe.db.sql("""
        SELECT ib.parent as item, GROUP_CONCAT(ib.branch) as branches
        FROM `tabBranches` ib
        GROUP BY ib.parent
    """, as_dict=True)

    # Print which items user can access
    for item in items_with_branches:
        item_branches = item['branches'].split(",")  # List of branches
        if user_branch in item_branches:
            print(f"User can access Item: {item['item']} - Assigned Branches: {item['branches']}")
        else:
            print(f"User CANNOT access Item: {item['item']} - Assigned Branches: {item['branches']}")

    # SQL condition for Frappe permission
    return f"""
        (
            -- Items with no branch restriction
            NOT EXISTS (
                SELECT 1
                FROM `tabBranches` ib
                WHERE ib.parent = `tabItem`.name
            )
            OR
            -- Items allowed for user's branch
            EXISTS (
                SELECT 1
                FROM `tabBranches` ib
                WHERE
                    ib.parent = `tabItem`.name
                    AND ib.branch = '{user_branch}'
            )
        )
    """



# def get_permission_query_conditions(user):
#     if user == "Administrator":
#         return ""

#     # user = "s@gmail.com"
#     user_branch = frappe.defaults.get_user_default("Branch", user)
#     print("User Branch:", user_branch)

#     if not user_branch:
#         return ""

#     items_with_branches = frappe.db.sql("""
#         SELECT ib.parent as item, GROUP_CONCAT(ib.branch) as branches
#         FROM `tabBranches` ib
#         GROUP BY ib.parent
#     """, as_dict=True)

#     for item in items_with_branches:
#         print(f"Item: {item['item']} - Assigned Branches: {item['branches']}")

#     return f"""
#         (
#             -- Items with no branch restriction
#             NOT EXISTS (
#                 SELECT 1
#                 FROM `tabBranches` ib
#                 WHERE ib.parent = `tabItem`.name
#             )

#             OR

#             -- Items allowed for user's branch
#             EXISTS (
#                 SELECT 1
#                 FROM `tabBranches` ib
#                 WHERE
#                     ib.parent = `tabItem`.name
#                     AND ib.branch = '{user_branch}'
#             )
#         )
#     """




def item_has_permission(doc, ptype, user):

    user_branch = frappe.get_cached_value('User', user, 'default_branch') or frappe.defaults.get_user_default('Branch')
    allowed_branches = frappe.db.get_all(
        "Branches",
        filters={"parent": doc.name},
        pluck="branch"
    )

    if not allowed_branches:
        return True

    return user_branch in allowed_branches




