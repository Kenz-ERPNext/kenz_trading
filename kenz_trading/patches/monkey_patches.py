"""
Monkey patches module — currently a no-op.

Previously installed:
  1. erpnext.controllers.queries.item_query -> custom_item_query (showed
     all items in link-field search).
  2. frappe.model.document.Document.round_floats_in -> kwargs-tolerant
     wrapper for older Frappe versions on Frappe Cloud.

Both have been disabled. The `apply` function is kept so the existing
`before_request` hook in hooks.py keeps working without raising.

If you need to re-enable a patch, restore the original imports and body
from git history (commits before 'comment item query') and add the
matching function definitions back into kenz_trading.events.sales_invoice.
"""


def apply():
    pass
