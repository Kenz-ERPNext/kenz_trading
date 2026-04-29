"""Hooks for Purchase Invoice doctype."""


def force_uncheck_update_outstanding_for_self(doc, method=None):
	"""
	When a Credit-mode Purchase Invoice return (Debit Note) has a
	`return_against` set, force-clear `update_outstanding_for_self` so the
	debit note reduces the original invoice's outstanding directly.

	Cash / Bank returns are skipped — the refund Payment Entry handles
	netting via direct allocation.
	"""
	if not doc.get("is_return"):
		return
	if not doc.get("return_against"):
		return
	if doc.get("custom_payment_mode") != "Credit":
		return
	if doc.get("update_outstanding_for_self"):
		doc.update_outstanding_for_self = 0
