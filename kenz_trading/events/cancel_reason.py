import frappe
from frappe import _

# Doctypes that need a reason to be cancelled when Kenza Settings > Require Cancel Reason is on
DOCTYPES = ("Sales Invoice", "Purchase Invoice", "Payment Entry", "Stock Entry")

# Spaces not counted; same as MIN_LENGTH in public/js/cancel_reason.js
MIN_LENGTH = 5

# How long a reason entered in the dialog waits for its cancel
REASON_TTL = 15 * 60


def is_enabled():
	return bool(frappe.utils.cint(frappe.db.get_single_value("Kenza Settings", "require_cancel_reason")))


@frappe.whitelist()
def is_reason_required(doctype: str):
	return doctype in DOCTYPES and is_enabled()


@frappe.whitelist(methods=["POST"])
def set_cancel_reason(doctype: str, docnames: str, reason: str):
	"""Hold the reason until the cancel that follows picks it up in before_cancel. It's kept in
	the cache, not on the document, so a cancel that fails leaves nothing behind."""
	if doctype not in DOCTYPES:
		return

	reason = (reason or "").strip()
	if len("".join(reason.split())) < MIN_LENGTH:
		frappe.throw(_("Please enter a reason for cancellation"))

	docnames = frappe.parse_json(docnames)
	for name in docnames:
		frappe.get_doc(doctype, name).check_permission("cancel")
		_hold(doctype, name, reason)

	# the form's "Cancel All" cancels the linked documents first, in the same action
	if len(docnames) == 1:
		for linked in _linked_docs(doctype, docnames[0]):
			if linked.get("doctype") in DOCTYPES:
				_hold(linked["doctype"], linked["name"], reason)


def before_cancel(doc, method=None):
	if not _is_user_cancel(doc) or not is_enabled():
		return

	reason = frappe.cache.get_value(_key(doc.doctype, doc.name), expires=True)
	if not reason:
		frappe.throw(
			_("A reason is required to cancel {0} {1}. Open it and cancel it from there.").format(
				_(doc.doctype), doc.name
			),
			title=_("Cancel Reason Required"),
		)

	if doc.meta.has_field("custom_cancel_reason"):
		doc.custom_cancel_reason = reason
	doc.add_comment("Comment", _("Cancel Reason: {0}").format(frappe.utils.escape_html(reason)))


def on_cancel(doc, method=None):
	frappe.cache.delete_value(_key(doc.doctype, doc.name))


def _is_user_cancel(doc):
	"""True when a user cancels this document from the desk or the standard API. Cancels made by
	other apps' code (e.g. the POS API), by scheduled jobs, or by ERPNext as a side effect of
	cancelling another document have nobody to ask, so they aren't blocked."""
	if getattr(frappe.local, "request", None):
		form = frappe.form_dict
		cmd = form.get("cmd") or ""
		if cmd == "frappe.desk.form.save.cancel":
			return form.get("doctype") == doc.doctype and str(form.get("name")) == str(doc.name)
		return not cmd or cmd.startswith("frappe.")

	# list view bulk cancel of 20+ documents runs as a background job
	job = getattr(frappe.local, "job", None)
	return bool(job and "bulk_action" in str(job.get("method")))


def _linked_docs(doctype, name):
	from frappe.desk.form.linked_with import get_submitted_linked_docs

	return get_submitted_linked_docs(doctype, name).get("docs") or []


def _hold(doctype, name, reason):
	frappe.cache.set_value(_key(doctype, name), reason, expires_in_sec=REASON_TTL)


def _key(doctype, name):
	return f"kenz_cancel_reason:{frappe.session.user}:{doctype}:{name}"
