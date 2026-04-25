"""
Phases 1 & 2: force-uncheck `update_outstanding_for_self` on submitted
SI/PI returns that have a usable `return_against`. After flipping, we
re-trigger ERPNext's outstanding-amount recomputation so the return's
own outstanding goes to zero and the original invoice's outstanding
absorbs the credit.
"""

from typing import List

import frappe
from frappe.utils import flt

from kenz_trading.events.reconciliation.audit import AuditBuffer
from kenz_trading.events.reconciliation.proposal import (
	PHASE_FLAG_FIX_SI_RETURNS,
	PHASE_FLAG_FIX_PI_RETURNS,
)


_SI_RECEIVABLE_FIELD = "debit_to"
_PI_PAYABLE_FIELD = "credit_to"


def _candidate_returns(doctype: str) -> List[dict]:
	"""
	Submitted returns that still carry their own outstanding *and*
	have a return_against pointing to a submitted, non-zero invoice.
	"""
	return frappe.db.sql(
		f"""
		SELECT
			r.name, r.return_against, r.update_outstanding_for_self,
			r.outstanding_amount, r.company, r.currency,
			r.{'customer' if doctype == 'Sales Invoice' else 'supplier'} AS party,
			orig.outstanding_amount AS original_outstanding
		FROM `tab{doctype}` r
		INNER JOIN `tab{doctype}` orig
			ON orig.name = r.return_against AND orig.docstatus = 1
		WHERE r.docstatus = 1
			AND r.is_return = 1
			AND r.return_against IS NOT NULL
			AND r.return_against != ''
			AND r.update_outstanding_for_self = 1
		""",
		as_dict=True,
	)


def _recompute_outstanding(doctype: str, name: str) -> float:
	"""Reload after `update_outstanding_amt` and return new value."""
	from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt

	doc = frappe.get_doc(doctype, name)
	account_field = _SI_RECEIVABLE_FIELD if doctype == "Sales Invoice" else _PI_PAYABLE_FIELD
	party_type = "Customer" if doctype == "Sales Invoice" else "Supplier"
	party_field = "customer" if doctype == "Sales Invoice" else "supplier"

	update_outstanding_amt(
		account=doc.get(account_field),
		party_type=party_type,
		party=doc.get(party_field),
		against_voucher_type=doctype,
		against_voucher=name,
	)
	return flt(frappe.db.get_value(doctype, name, "outstanding_amount"))


def _process(doctype: str, phase: str, audit: AuditBuffer, dry_run: bool) -> None:
	rows = _candidate_returns(doctype)
	for r in rows:
		original_before = flt(r["original_outstanding"])
		return_before = flt(r["outstanding_amount"])

		if dry_run:
			audit.flag_flip(
				phase=phase,
				return_doc=r["name"],
				return_against=r["return_against"],
				original_before=original_before,
				original_after=original_before + return_before,  # projected
				return_before=return_before,
				return_after=0.0,
			)
			continue

		savepoint = f"sp_{phase}_{r['name'].replace('/', '_').replace(' ', '_')}"
		try:
			frappe.db.savepoint(savepoint)
			frappe.db.set_value(
				doctype, r["name"], "update_outstanding_for_self", 0,
				update_modified=False,
			)
			# Recompute on the return itself (now should drop to 0)
			return_after = _recompute_outstanding(doctype, r["name"])
			# Then on the original (should absorb the credit)
			original_after = _recompute_outstanding(doctype, r["return_against"])
			frappe.db.commit()
			audit.flag_flip(
				phase=phase,
				return_doc=r["name"],
				return_against=r["return_against"],
				original_before=original_before,
				original_after=original_after,
				return_before=return_before,
				return_after=return_after,
			)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(
				title=f"reconciliation flag flip failed: {r['name']}",
				message=frappe.get_traceback(),
			)


def run_phase_si(audit: AuditBuffer, dry_run: bool) -> None:
	_process("Sales Invoice", PHASE_FLAG_FIX_SI_RETURNS, audit, dry_run)


def run_phase_pi(audit: AuditBuffer, dry_run: bool) -> None:
	_process("Purchase Invoice", PHASE_FLAG_FIX_PI_RETURNS, audit, dry_run)
