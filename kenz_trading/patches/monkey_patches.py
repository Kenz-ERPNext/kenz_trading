import erpnext.controllers.queries
from kenz_trading.events.sales_invoice import custom_item_query
import kenz_trading.events.sales_invoice as si_module

_patched = False

def apply():
    """
    Monkey-patch erpnext.controllers.queries.item_query so that
    link field search (frappe.desk.search.search_widget) calls our
    custom_item_query instead of the default.
    """
    global _patched
    if _patched:
        return

    # Store original function BEFORE patching so fallback doesn't loop
    si_module._original_item_query = erpnext.controllers.queries.item_query
    erpnext.controllers.queries.item_query = custom_item_query
    _patched = True
