"""
Phases 3 & 4: reconcile unlinked customer Receive PEs against outstanding
Sales Invoices, and unlinked supplier Pay PEs against outstanding Purchase
Invoices. FIFO per party (oldest invoice first). Goes through ERPNext's
PaymentReconciliation controller — no raw GL writes.
"""

from datetime import date
from typing import List

import frappe
from frappe.utils import flt, getdate

from kenz_trading.events.reconciliation.audit import AuditBuffer
from kenz_trading.events.reconciliation.proposal import (
	AllocationProposal,
	PHASE_RECONCILE_RECEIVE_PES,
	PHASE_RECONCILE_PAY_PES,
)
from kenz_trading.events.reconciliation.safeguards import run_safeguards


_CUSTOMER_RECEIVABLE_DEFAULT_FIELD = "default_receivable_account"
_SUPPLIER_PAYABLE_DEFAULT_FIELD = "default_payable_account"


def _company_default_account(company: str, party_type: str) -> str:
	"""Return the receivable/payable account for the company."""
	field = (
		_CUSTOMER_RECEIVABLE_DEFAULT_FIELD
		if party_type == "Customer"
		else _SUPPLIER_PAYABLE_DEFAULT_FIELD
	)
	return frappe.db.get_value("Company", company, field)


def _parties_with_unallocated(party_type: str, payment_type: str) -> List[dict]:
	"""
	Parties that have at least one submitted PE with unallocated_amount > 0.
	Returns list of {party, company} so we can drive PaymentReconciliation
	per (party, company) pair.
	"""
	return frappe.db.sql(
		"""
		SELECT DISTINCT party, company
		FROM `tabPayment Entry`
		WHERE docstatus = 1
			AND party_type = %(pt)s
			AND payment_type = %(payt)s
			AND unallocated_amount > 0
		""",
		{"pt": party_type, "payt": payment_type},
		as_dict=True,
	)


def _reconcile_party(
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

	receivable_payable_account = _company_default_account(company, party_type)
	if not receivable_payable_account:
		return

	pr = frappe.get_doc({
		"doctype": "Payment Reconciliation",
		"company": company,
		"party_type": party_type,
		"party": party,
		"receivable_payable_account": receivable_payable_account,
	})

	# Populate `invoices` and `payments` child tables via the controller.
	pr.get_unreconciled_entries()

	if not pr.get("invoices") or not pr.get("payments"):
		return

	# FIFO: invoices already come back sorted by posting_date asc from the
	# controller; payments by posting_date asc also.
	pr.allocate_entries({
		"invoices": [i.as_dict() for i in pr.get("invoices")],
		"payments": [p.as_dict() for p in pr.get("payments")],
	})

	# After allocate_entries, pr.allocation has the proposed pairings.
	allocations = pr.get("allocation") or []
	if not allocations:
		return

	# Translate each allocation row to an AllocationProposal for audit.
	proposals = []
	for alloc in allocations:
		alloc_dict = alloc.as_dict()
		invoice_name = alloc_dict.get("invoice_number")
		invoice_doctype = alloc_dict.get("invoice_type", "Sales Invoice" if party_type == "Customer" else "Purchase Invoice")

		invoice_meta = frappe.db.get_value(
			invoice_doctype,
			invoice_name,
			["posting_date", "currency", "outstanding_amount"],
			as_dict=True,
		) or {}

		pe_meta = frappe.db.get_value(
			"Payment Entry",
			alloc_dict.get("reference_name"),
			["posting_date", "mode_of_payment", "unallocated_amount"],
			as_dict=True,
		) or {}

		p = AllocationProposal(
			phase=phase,
			party_type=party_type,
			party=party,
			source_doctype="Payment Entry",
			source_name=alloc_dict.get("reference_name"),
			source_remaining=flt(pe_meta.get("unallocated_amount") or 0),
			target_doctype=invoice_doctype,
			target_name=invoice_name,
			target_outstanding=flt(invoice_meta.get("outstanding_amount") or 0),
			allocated_amount=flt(alloc_dict.get("allocated_amount") or 0),
			currency=invoice_meta.get("currency") or "",
			company=company,
			source_posting_date=getdate(pe_meta.get("posting_date") or date.today()),
			target_posting_date=getdate(invoice_meta.get("posting_date") or date.today()),
			mode_of_payment=pe_meta.get("mode_of_payment"),
		)

		ok, reason = run_safeguards(p, target_currency=p.currency, target_company=company)
		if not ok:
			audit.skipped(p, reason)
			# Drop this row from the controller's allocation so reconcile() skips it.
			alloc.allocated_amount = 0
		else:
			proposals.append((p, alloc))

	if dry_run:
		for p, _ in proposals:
			audit.reconciled(p)  # treat as "would reconcile" in dry-run
		return

	# Live: execute reconcile() and record outcomes.
	savepoint = f"sp_{phase}_{party.replace(' ', '_')}"
	try:
		frappe.db.savepoint(savepoint)
		pr.reconcile()
		frappe.db.commit()
		for p, _ in proposals:
			audit.reconciled(p)
	except Exception as e:
		frappe.db.rollback(save_point=savepoint)
		frappe.log_error(
			title=f"reconcile_party failed: {party}",
			message=frappe.get_traceback(),
		)
		# Mark all proposals for this party as failed
		for p, _ in proposals:
			audit.failed(p, e)


def run_phase_receive(audit: AuditBuffer, dry_run: bool) -> None:
	parties = _parties_with_unallocated("Customer", "Receive")
	for row in parties:
		_reconcile_party(
			party_type="Customer",
			party=row["party"],
			company=row["company"],
			phase=PHASE_RECONCILE_RECEIVE_PES,
			audit=audit,
			dry_run=dry_run,
		)


def run_phase_pay(audit: AuditBuffer, dry_run: bool) -> None:
	parties = _parties_with_unallocated("Supplier", "Pay")
	for row in parties:
		_reconcile_party(
			party_type="Supplier",
			party=row["party"],
			company=row["company"],
			phase=PHASE_RECONCILE_PAY_PES,
			audit=audit,
			dry_run=dry_run,
		)
