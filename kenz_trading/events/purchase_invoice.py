"""Hooks for Purchase Invoice doctype."""


def force_uncheck_update_outstanding_for_self(doc, method=None):
	"""
	When a Purchase Invoice return (Debit Note) has a `return_against`
	set, the debit note should reduce the original invoice's outstanding
	rather than carrying its own. Forcefully clears
	`update_outstanding_for_self` to keep books in sync with the bulk
	reconciliation patch.

	Standalone returns (no return_against) are left alone — those need
	their own outstanding because there's no original to reduce.
	"""
	if not doc.get("is_return"):
		return
	if not doc.get("return_against"):
		return
	if doc.get("update_outstanding_for_self"):
		doc.update_outstanding_for_self = 0
