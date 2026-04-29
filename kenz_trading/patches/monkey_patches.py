"""
Monkey patches applied via the `before_request` hook in hooks.py.

Currently active:
  - Document.round_floats_in: tolerate unknown kwargs (e.g.
    `do_not_round_fields`) that newer ERPNext (>=15.100) passes but
    older Frappe (<=15.95) does not accept. Without this, every Sales
    Order / Sales Invoice / Purchase Invoice save fails with
    `TypeError: Document.round_floats_in() got an unexpected keyword
    argument 'do_not_round_fields'`.

Disabled (kept here for reference):
  - erpnext.controllers.queries.item_query override (custom_item_query).
    Removed because the function definition was deleted from
    sales_invoice.py. To re-enable, restore the function from git
    history before the 'comment item query' commits and uncomment the
    Patch 1 block in `apply()`.
"""

from frappe.model.document import Document

_patched = False


def apply():
	global _patched
	if _patched:
		return

	# Patch round_floats_in to drop unknown kwargs.
	# Capture the original ONCE so re-applies don't recurse.
	original_round_floats_in = Document.round_floats_in

	def _safe_round_floats_in(self, doc, fieldnames=None, **kwargs):
		# Silently drop kwargs that the installed Frappe doesn't accept
		# (e.g. do_not_round_fields, introduced in newer Frappe versions).
		return original_round_floats_in(self, doc, fieldnames=fieldnames)

	Document.round_floats_in = _safe_round_floats_in

	_patched = True
