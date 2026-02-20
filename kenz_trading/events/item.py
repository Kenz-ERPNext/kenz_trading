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






# def get_permission_query_conditions(user):
#     if not user:
#         user = frappe.session.user

#     # Admin full access
#     if user == "Administrator":
#         return ""

#     # Check if user has any User Permission for Branch
#     user_permissions = frappe.get_all(
#         "User Permission",
#         filters={
#             "user": user,
#             "allow": "Branch"
#         },
#         fields=["for_value"]
#     )

#     # If no User Permission → allow all items
#     if not user_permissions:
#         return ""

#     # Get all allowed branches
#     allowed_branches = [frappe.db.escape(p.for_value) for p in user_permissions]

#     allowed_branches_str = ", ".join(allowed_branches)

#     # Apply restriction
#     return f"""
#     (
#         NOT EXISTS (
#             SELECT 1
#             FROM `tabBranches` ib
#             WHERE ib.parent = `tabItem`.name
#         )
#         OR
#         EXISTS (
#             SELECT 1
#             FROM `tabBranches` ib
#             WHERE
#                 ib.parent = `tabItem`.name
#                 AND ib.branch IN ({allowed_branches_str})
#         )
#     )
#     """



# def item_has_permission(doc, ptype, user):

#     user_branch = frappe.get_cached_value('User', user, 'default_branch') or frappe.defaults.get_user_default('Branch')
#     allowed_branches = frappe.db.get_all(
#         "Branches",
#         filters={"parent": doc.name},
#         pluck="branch"
#     )

#     if not allowed_branches:
#         return True

#     return user_branch in allowed_branches




def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    # Administrator full access
    if user == "Administrator":
        return ""

    # Check if user has any User Permission for Branch
    user_permissions = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Branch"
        },
        fields=["for_value"]
    )

    # ✅ If no User Permission → allow everything
    if not user_permissions:
        return ""

    # Get allowed branches
    allowed_branches = [frappe.db.escape(p.for_value) for p in user_permissions]
    allowed_branches_str = ", ".join(allowed_branches)

    return f"""
    (
        NOT EXISTS (
            SELECT 1
            FROM `tabBranches` ib
            WHERE ib.parent = `tabItem`.name
        )
        OR
        EXISTS (
            SELECT 1
            FROM `tabBranches` ib
            WHERE
                ib.parent = `tabItem`.name
                AND ib.branch IN ({allowed_branches_str})
        )
    )
    """




def item_has_permission(doc, ptype, user):
    if not user:
        user = frappe.session.user

    # Administrator full access
    if user == "Administrator":
        return True

    # 🔹 Check if user has any Branch User Permission
    user_permissions = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Branch"
        },
        pluck="for_value"
    )

    # ✅ If no User Permission → allow everything
    if not user_permissions:
        return True

    # Get branches linked to Item
    item_branches = frappe.db.get_all(
        "Branches",
        filters={"parent": doc.name},
        pluck="branch"
    )

    # If item has no branches → allow
    if not item_branches:
        return True

    # Check intersection
    return any(branch in user_permissions for branch in item_branches)