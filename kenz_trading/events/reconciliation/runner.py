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
