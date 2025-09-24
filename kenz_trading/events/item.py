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

