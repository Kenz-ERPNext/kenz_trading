import erpnext.controllers.queries
from frappe.model.document import Document
from kenz_trading.events.sales_invoice import custom_item_query
import kenz_trading.events.sales_invoice as si_module

_patched = False


def apply():
    pass



    # """
    # Monkey patches applied on every request:
    # 1. erpnext.controllers.queries.item_query -> our custom_item_query for
    #    link field search (shows all items).
    # 2. Document.round_floats_in -> wrapper that tolerates unknown kwargs
    #    (e.g. do_not_round_fields) introduced by newer ERPNext commits that
    #    don't match the installed Frappe version on Frappe Cloud.
    # """
    # global _patched
    # if _patched:
    #     return

    # # --- Patch 1: item_query override ---
    # si_module._original_item_query = erpnext.controllers.queries.item_query
    # erpnext.controllers.queries.item_query = custom_item_query

    # # --- Patch 2: tolerate unknown kwargs on round_floats_in ---
    # _original_round_floats_in = Document.round_floats_in

    # def _safe_round_floats_in(self, doc, fieldnames=None, **kwargs):
    #     # Drop unknown kwargs (e.g. do_not_round_fields) that newer ERPNext
    #     # versions may pass but the installed Frappe doesn't support.
    #     return _original_round_floats_in(self, doc, fieldnames=fieldnames)

    # Document.round_floats_in = _safe_round_floats_in

    # _patched = True
