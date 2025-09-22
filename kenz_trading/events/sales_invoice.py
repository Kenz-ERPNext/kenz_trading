import frappe

@frappe.whitelist()
def get_default_branch(user):
    branch = frappe.db.get_value("User Permission", {"user":user,"allow":"Branch"}, "for_value")
    return branch if branch else None