"""
Pure validation for AllocationProposals. No Frappe DB calls — all data
must already be on the proposal. This makes the rules trivially testable
and forces the phase modules to be explicit about what they fetched.
"""

from typing import Tuple

from kenz_trading.events.reconciliation.proposal import AllocationProposal


TOLERANCE = 0.01  # single-fils rounding tolerance


def run_safeguards(
	proposal: AllocationProposal,
	target_currency: str = None,
	target_company: str = None,
) -> Tuple[bool, str]:
	"""
	Returns (ok, reason). reason is "" on success, otherwise a short
	machine-readable code that maps to a Skip Reason in the audit log.
	"""
	if target_currency is not None and proposal.currency != target_currency:
		return False, "currency_mismatch"

	if target_company is not None and proposal.company != target_company:
		return False, "company_mismatch"

	if proposal.source_posting_date < proposal.target_posting_date:
		return False, "date_order"

	if abs(proposal.target_outstanding) <= TOLERANCE:
		return False, "already_settled"

	if abs(proposal.source_remaining) <= TOLERANCE:
		return False, "no_unallocated"

	cap = min(abs(proposal.source_remaining), abs(proposal.target_outstanding))
	if abs(proposal.allocated_amount) > cap + TOLERANCE:
		return False, "overallocation"

	return True, ""
