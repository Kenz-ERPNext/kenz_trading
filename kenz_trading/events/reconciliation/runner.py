"""
Reconciliation runner — orchestrates all six phases, supports dry-run vs
live, and exposes whitelisted endpoints for partial / per-party runs.

The Excel summary report is the primary output. The runner returns a dict
with the file path, basename, download URL, and per-phase counts.
"""

from typing import Optional

import frappe

from kenz_trading.events.reconciliation.audit import AuditBuffer
from kenz_trading.events.reconciliation.proposal import (
	ALL_PHASES,
	PHASE_FLAG_FIX_SI_RETURNS, PHASE_FLAG_FIX_PI_RETURNS,
	PHASE_RECONCILE_RECEIVE_PES, PHASE_RECONCILE_PAY_PES,
	PHASE_NET_LEFTOVER_SI_RETURNS, PHASE_NET_LEFTOVER_PI_RETURNS,
)
from kenz_trading.events.reconciliation import (
	return_flag_fixer, pe_reconciler, return_netter,
)


_PHASE_FUNCS = {
	PHASE_FLAG_FIX_SI_RETURNS: return_flag_fixer.run_phase_si,
	PHASE_FLAG_FIX_PI_RETURNS: return_flag_fixer.run_phase_pi,
	PHASE_RECONCILE_RECEIVE_PES: pe_reconciler.run_phase_receive,
	PHASE_RECONCILE_PAY_PES: pe_reconciler.run_phase_pay,
	PHASE_NET_LEFTOVER_SI_RETURNS: return_netter.run_phase_si,
	PHASE_NET_LEFTOVER_PI_RETURNS: return_netter.run_phase_pi,
}


def _finalize(audit: AuditBuffer, dry_run: bool) -> dict:
	path = audit.write_excel()
	basename = path.rsplit("/", 1)[-1]
	site = frappe.local.site
	download_url = f"/private/files/{basename}"

	mode = "dry_run" if dry_run else "live"
	summary = audit.build_summary_rows()
	totals = {
		"reconciled": len(audit.reconciled_rows),
		"skipped": len(audit.skipped_rows),
		"failed": len(audit.failed_rows),
		"flag_flips": len(audit.flag_flip_rows),
	}

	print(f"[reconciliation] mode={mode} site={site}")
	print(f"[reconciliation] file={path}")
	print(f"[reconciliation] totals={totals}")
	for row in summary:
		print(f"[reconciliation]  phase={row[0]} att={row[2]} ok={row[3]} skip={row[4]} fail={row[5]} amt={row[6]:.2f}")

	if dry_run:
		print(
			"[reconciliation] DRY-RUN COMPLETE. To commit, run:\n"
			f"  bench --site {site} execute "
			f"kenz_trading.events.reconciliation.runner.run_all --kwargs \"{{'dry_run': 0}}\""
		)

	return {
		"mode": mode,
		"path": path,
		"basename": basename,
		"download_url": download_url,
		"totals": totals,
		"summary": [dict(zip(
			("phase", "mode", "attempted", "succeeded", "skipped", "failed",
			 "amount_reconciled", "parties_touched", "started_at", "finished_at"),
			row,
		)) for row in summary],
	}


@frappe.whitelist()
def run_all(dry_run: int = 1) -> dict:
	"""Run all six phases in order. Default is dry-run."""
	dry_run = int(dry_run)
	audit = AuditBuffer(mode="dry_run" if dry_run else "live")
	for phase in ALL_PHASES:
		_PHASE_FUNCS[phase](audit, bool(dry_run))
	return _finalize(audit, bool(dry_run))


@frappe.whitelist()
def run_phase(phase: str, dry_run: int = 1) -> dict:
	"""Run a single phase by name. See proposal.ALL_PHASES."""
	dry_run = int(dry_run)
	if phase not in _PHASE_FUNCS:
		frappe.throw(f"Unknown phase: {phase}. Valid: {list(_PHASE_FUNCS.keys())}")
	audit = AuditBuffer(mode="dry_run" if dry_run else "live")
	_PHASE_FUNCS[phase](audit, bool(dry_run))
	return _finalize(audit, bool(dry_run))


@frappe.whitelist()
def run_for_party(party_type: str, party: str, dry_run: int = 1, company: Optional[str] = None) -> dict:
	"""
	Run only the PE reconciliation phases (3 & 4) for a single party.
	Used to retry an individual customer/supplier after reviewing the audit.
	"""
	dry_run = int(dry_run)
	if party_type not in ("Customer", "Supplier"):
		frappe.throw("party_type must be 'Customer' or 'Supplier'")

	audit = AuditBuffer(mode="dry_run" if dry_run else "live")
	if not company:
		# pick the first company that has a PE for this party
		company = frappe.db.get_value(
			"Payment Entry",
			{"docstatus": 1, "party_type": party_type, "party": party, "unallocated_amount": (">", 0)},
			"company",
		)
		if not company:
			frappe.throw(f"No unallocated PE found for {party_type} {party}")

	phase = (
		PHASE_RECONCILE_RECEIVE_PES if party_type == "Customer"
		else PHASE_RECONCILE_PAY_PES
	)
	pe_reconciler._reconcile_party(
		party_type=party_type, party=party, company=company,
		phase=phase, audit=audit, dry_run=bool(dry_run),
	)
	return _finalize(audit, bool(dry_run))


@frappe.whitelist()
def download_audit(filename: str) -> None:
	"""
	Stream a reconciliation_audit_*.xlsx file from sites/<site>/private/files/.
	Filename must start with `reconciliation_audit_` to prevent path traversal.
	"""
	import os
	from frappe.utils import get_site_path

	if not filename.startswith("reconciliation_audit_") or "/" in filename or ".." in filename:
		frappe.throw("Invalid filename")

	path = os.path.join(get_site_path("private", "files"), filename)
	if not os.path.isfile(path):
		frappe.throw(f"File not found: {filename}")

	with open(path, "rb") as f:
		content = f.read()

	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


@frappe.whitelist()
def recover_cash_return_pe(invoice_name: str) -> dict:
	"""
	Recover a Cash/Bank Sales Invoice return whose `update_outstanding_for_self`
	was prematurely set to 0 (so its outstanding got absorbed into the
	original invoice). Restores the flag to 1, recomputes outstanding on
	both the return and the original, then creates the refund Payment Entry
	by invoking the on_submit handler.
	"""
	from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
	from kenz_trading.events.sales_invoice import create_payment_entry_for_cash

	doc = frappe.get_doc("Sales Invoice", invoice_name)
	if not doc.is_return:
		frappe.throw(f"{invoice_name} is not a return invoice")
	if doc.docstatus != 1:
		frappe.throw(f"{invoice_name} must be submitted")
	if doc.get("custom_payment_mode") not in ("Cash", "Bank"):
		frappe.throw(f"{invoice_name} is not a Cash/Bank invoice")

	# Skip if a submitted PE already references this invoice
	if frappe.db.exists(
		"Payment Entry Reference",
		{
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice_name,
			"docstatus": 1,
		},
	):
		return {"invoice": invoice_name, "status": "already_has_pe", "pe": None}

	original_name = doc.return_against
	original_outstanding_before = None
	if original_name:
		original_outstanding_before = frappe.db.get_value(
			"Sales Invoice", original_name, "outstanding_amount"
		)

	# Restore flag and recompute
	frappe.db.set_value(
		"Sales Invoice", invoice_name, "update_outstanding_for_self", 1,
		update_modified=False,
	)

	update_outstanding_amt(
		account=doc.debit_to,
		party_type="Customer",
		party=doc.customer,
		against_voucher_type="Sales Invoice",
		against_voucher=invoice_name,
	)
	if original_name and frappe.db.exists("Sales Invoice", original_name):
		orig = frappe.get_doc("Sales Invoice", original_name)
		update_outstanding_amt(
			account=orig.debit_to,
			party_type="Customer",
			party=orig.customer,
			against_voucher_type="Sales Invoice",
			against_voucher=original_name,
		)

	# Reload the return so doc.outstanding_amount reflects the recompute
	doc.reload()

	# Now create the refund PE via the standard handler
	create_payment_entry_for_cash(doc)
	frappe.db.commit()

	# Find the newly created PE
	pe_name = frappe.db.get_value(
		"Payment Entry Reference",
		{
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice_name,
			"docstatus": 1,
		},
		"parent",
	)

	return {
		"invoice": invoice_name,
		"status": "recovered" if pe_name else "no_pe_created",
		"pe": pe_name,
		"return_outstanding_after": frappe.db.get_value("Sales Invoice", invoice_name, "outstanding_amount"),
		"original": original_name,
		"original_outstanding_before": original_outstanding_before,
		"original_outstanding_after": (
			frappe.db.get_value("Sales Invoice", original_name, "outstanding_amount")
			if original_name else None
		),
	}
