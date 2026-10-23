import frappe


@frappe.whitelist()
def change_language(language):
    if language not in ("en", "ar"):
        frappe.throw("Invalid language")

    frappe.db.set_value(
        "User",
        frappe.session.user,
        "language",
        language
    )

    frappe.db.commit()

    # Clear user/session cache
    frappe.clear_cache(user=frappe.session.user)

    return True


@frappe.whitelist()
def get_current_language():
    return frappe.db.get_value(
        "User",
        frappe.session.user,
        "language"
    )