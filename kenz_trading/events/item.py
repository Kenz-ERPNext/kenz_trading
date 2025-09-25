import frappe

def get_permission_query_conditions_for_item(user=None):
    if not user:
        user = frappe.session.user

    # Full access for Administrator
    if user == "Administrator":
        return None

    # Get allowed branches from Kenza Settings
    settings = frappe.get_single("Kenza Settings")
    allowed_branches = [
        u.branch for u in settings.user_default_branch if u.user == user
    ]

    if not allowed_branches:
        return "1=0"

    branch_list = "', '".join(allowed_branches)
    return f"""
        `tabItem`.name IN (
            SELECT parent FROM `tabBranches`
            WHERE branch IN ('{branch_list}')
        )
    """


def has_permission_for_item(doc, user=None):
    if not user:
        user = frappe.session.user

    # Admin can do anything
    if user == "Administrator":
        return True

    # Get allowed branches
    settings = frappe.get_single("Kenza Settings")
    allowed_branches = [u.branch for u in settings.user_default_branch if u.user == user]

    if not allowed_branches:
        return False

    # If any branch in the Item matches allowed branches → allow
    for b in doc.custom_branches:
        if b.branch in allowed_branches:
            return True

    return False
