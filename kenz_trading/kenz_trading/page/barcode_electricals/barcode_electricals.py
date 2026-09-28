import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_item_rate(item_code: str, uom: str | None = None) -> float:
	frappe.has_permission("Item", ptype="select", throw=True)

	filters = {"item_code": item_code, "selling": 1}
	if uom:
		filters["uom"] = uom
		rate = frappe.db.get_value("Item Price", filters, "price_list_rate", order_by="valid_from desc")
		if rate is not None:
			return flt(rate)

	rate = frappe.db.get_value(
		"Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate", order_by="valid_from desc"
	)
	if rate is not None:
		return flt(rate)

	return flt(frappe.db.get_value("Item", item_code, "standard_rate") or 0)
