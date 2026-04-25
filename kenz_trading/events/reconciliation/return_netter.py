"""
Phases 5 & 6: net leftover SI/PI returns (those with no usable
return_against) against positive invoices for the same party. Reuses
the PaymentReconciliation controller — credit/debit notes are exposed
in its `payments` collection (see PaymentReconciliation.get_dr_or_cr_notes).
"""

import re
from datetime import date
from typing import List

import frappe
from frappe.utils import flt, getdate

from kenz_trading.events.reconciliation.audit import AuditBuffer
from kenz_trading.events.reconciliation.proposal import (
	AllocationProposal,
	PHASE_NET_LEFTOVER_SI_RETURNS,
	PHASE_NET_LEFTOVER_PI_RETURNS,
)
from kenz_trading.events.reconciliation.safeguards import run_safeguards


def _candidate_parties(doctype: str) -> List[dict]:
	"""
	Parties that still have at least one submitted return with non-zero
	outstanding AFTER phase 1/2 — i.e. its `return_against` was missing
	or cancelled.
	"""
	party_field = "customer" if doctype == "Sales Invoice" else "supplier"
	return frappe.db.sql(
		f"""
		SELECT DISTINCT {party_field} AS party, company
		FROM `tab{doctype}`
		WHERE docstatus = 1
			AND is_return = 1
			AND outstanding_amount != 0
			AND (
				return_against IS NULL OR return_against = ''
				OR NOT EXISTS (
					SELECT 1 FROM `tab{doctype}` orig
					WHERE orig.name = `tab{doctype}`.return_against
						AND orig.docstatus = 1
				)
			)
		""",
		as_dict=True,
	)


def _net_party(
	doctype: str,
	party_type: str,
	party: str,
	company: str,
	phase: str,
	audit: AuditBuffer,
	dry_run: bool,
) -> None:
	from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import (
		PaymentReconciliation,
	)

	field = "default_receivable_account" if party_type == "Customer" else "default_payable_account"
	receivable_payable_account = frappe.db.get_value("Company", company, field)
	if not receivable_payable_account:
		return

	pr = frappe.get_doc({
		"doctype": "Payment Reconciliation",
		"company": company,
		"party_type": party_type,
		"party": party,
		"receivable_payable_account": receivable_payable_account,
	})
	pr.get_unreconciled_entries()

	# Filter `payments` to only credit/debit notes (skip plain PEs — phase 3/4 handled those)
	cn_payments = [p for p in (pr.get("payments") or []) if p.reference_type == doctype]
	if not cn_payments or not pr.get("invoices"):
		return

	pr.set("payments", cn_payments)
	pr.allocate_entries({
		"invoices": [i.as_dict() for i in pr.get("invoices")],
		"payments": [p.as_dict() for p in cn_payments],
	})

	allocations = pr.get("allocation") or []
	if not allocations:
		return

	# Filter to same-doctype targets only — skip Journal Entry etc.
	allocations = [a for a in allocations if (a.invoice_type or doctype) == doctype]
	if not allocations:
		return

	proposals = []
	for alloc in allocations:
		ad = alloc.as_dict()
		inv_meta = frappe.db.get_value(
			doctype,
			ad.get("invoice_number"),
			["posting_date", "currency", "outstanding_amount"],
			as_dict=True,
		) or {}
		src_meta = frappe.db.get_value(
			doctype,
			ad.get("reference_name"),
			["posting_date", "outstanding_amount"],
			as_dict=True,
		) or {}

		p = AllocationProposal(
			phase=phase,
			party_type=party_type,
			party=party,
			source_doctype=doctype,
			source_name=ad.get("reference_name"),
			source_remaining=abs(flt(src_meta.get("outstanding_amount") or 0)),
			target_doctype=doctype,
			target_name=ad.get("invoice_number"),
			target_outstanding=flt(inv_meta.get("outstanding_amount") or 0),
			allocated_amount=flt(ad.get("allocated_amount") or 0),
			currency=inv_meta.get("currency") or "",
			company=company,
			source_posting_date=getdate(src_meta.get("posting_date") or date.today()),
			target_posting_date=getdate(inv_meta.get("posting_date") or date.today()),
			mode_of_payment=None,
		)

		ok, reason = run_safeguards(p, target_currency=p.currency, target_company=company)
		if not ok:
			audit.skipped(p, reason)
			alloc.allocated_amount = 0
		else:
			proposals.append((p, alloc))

	if dry_run:
		for p, _ in proposals:
			audit.reconciled(p)
		return

	safe_party = re.sub(r"[^a-zA-Z0-9_]", "_", party)
	savepoint = f"sp_{phase}_{safe_party}"
	try:
		frappe.db.savepoint(savepoint)
		pr.reconcile()
		frappe.db.commit()
		for p, _ in proposals:
			audit.reconciled(p)
	except Exception as e:
		frappe.db.rollback(save_point=savepoint)
		frappe.log_error(
			title=f"return_netter failed: {party}",
			message=frappe.get_traceback(),
		)
		for p, _ in proposals:
			audit.failed(p, e)


def run_phase_si(audit: AuditBuffer, dry_run: bool) -> None:
	for row in _candidate_parties("Sales Invoice"):
		_net_party(
			"Sales Invoice", "Customer", row["party"], row["company"],
			PHASE_NET_LEFTOVER_SI_RETURNS, audit, dry_run,
		)


def run_phase_pi(audit: AuditBuffer, dry_run: bool) -> None:
	for row in _candidate_parties("Purchase Invoice"):
		_net_party(
			"Purchase Invoice", "Supplier", row["party"], row["company"],
			PHASE_NET_LEFTOVER_PI_RETURNS, audit, dry_run,
		)
