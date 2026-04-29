"""
Data contract shared by all reconciliation phases.

An AllocationProposal represents one *intended* allocation of money
from a source document (Payment Entry or Return Invoice) to a target
invoice. Proposals are produced by the phase modules, validated by
safeguards, optionally executed (live mode), and always recorded
in the audit log.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


PHASE_FLAG_FIX_SI_RETURNS = "flag_fix_si_returns"
PHASE_FLAG_FIX_PI_RETURNS = "flag_fix_pi_returns"
PHASE_RECONCILE_RECEIVE_PES = "reconcile_receive_pes"
PHASE_RECONCILE_PAY_PES = "reconcile_pay_pes"
PHASE_NET_LEFTOVER_SI_RETURNS = "net_leftover_si_returns"
PHASE_NET_LEFTOVER_PI_RETURNS = "net_leftover_pi_returns"

ALL_PHASES = (
	PHASE_FLAG_FIX_SI_RETURNS,
	PHASE_FLAG_FIX_PI_RETURNS,
	PHASE_RECONCILE_RECEIVE_PES,
	PHASE_RECONCILE_PAY_PES,
	PHASE_NET_LEFTOVER_SI_RETURNS,
	PHASE_NET_LEFTOVER_PI_RETURNS,
)


@dataclass
class AllocationProposal:
	phase: str
	party_type: str  # "Customer" | "Supplier"
	party: str
	source_doctype: str  # "Payment Entry" | "Sales Invoice" | "Purchase Invoice"
	source_name: str
	source_remaining: float
	target_doctype: str  # "Sales Invoice" | "Purchase Invoice"
	target_name: str
	target_outstanding: float
	allocated_amount: float
	currency: str
	company: str
	source_posting_date: date
	target_posting_date: date
	mode_of_payment: Optional[str] = None
	notes: str = ""

	@property
	def proposal_id(self) -> str:
		"""Stable identifier used in savepoint names."""
		return f"{self.phase}:{self.source_name}->{self.target_name}"
