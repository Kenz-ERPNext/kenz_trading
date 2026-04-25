import unittest
from datetime import date

from kenz_trading.events.reconciliation.proposal import (
	AllocationProposal,
	PHASE_RECONCILE_RECEIVE_PES,
)
from kenz_trading.events.reconciliation.safeguards import run_safeguards


def _proposal(**overrides):
	defaults = dict(
		phase=PHASE_RECONCILE_RECEIVE_PES,
		party_type="Customer",
		party="C-001",
		source_doctype="Payment Entry",
		source_name="PE-1",
		source_remaining=500.0,
		target_doctype="Sales Invoice",
		target_name="SI-1",
		target_outstanding=500.0,
		allocated_amount=500.0,
		currency="SAR",
		company="Faris",
		source_posting_date=date(2026, 4, 10),
		target_posting_date=date(2026, 4, 5),
		mode_of_payment="Cash",
	)
	defaults.update(overrides)
	return AllocationProposal(**defaults)


class TestSafeguards(unittest.TestCase):
	def test_happy_path_passes(self):
		ok, reason = run_safeguards(_proposal())
		self.assertTrue(ok)
		self.assertEqual(reason, "")

	def test_currency_mismatch_skipped(self):
		ok, reason = run_safeguards(_proposal(currency="USD"), target_currency="SAR")
		self.assertFalse(ok)
		self.assertEqual(reason, "currency_mismatch")

	def test_company_mismatch_skipped(self):
		ok, reason = run_safeguards(_proposal(company="Faris"), target_company="Other")
		self.assertFalse(ok)
		self.assertEqual(reason, "company_mismatch")

	def test_pe_dated_before_invoice_skipped(self):
		ok, reason = run_safeguards(
			_proposal(
				source_posting_date=date(2026, 4, 1),
				target_posting_date=date(2026, 4, 5),
			)
		)
		self.assertFalse(ok)
		self.assertEqual(reason, "date_order")

	def test_zero_target_outstanding_skipped(self):
		ok, reason = run_safeguards(_proposal(target_outstanding=0.0))
		self.assertFalse(ok)
		self.assertEqual(reason, "already_settled")

	def test_zero_source_remaining_skipped(self):
		ok, reason = run_safeguards(_proposal(source_remaining=0.0))
		self.assertFalse(ok)
		self.assertEqual(reason, "no_unallocated")

	def test_allocation_capped_at_min_within_tolerance(self):
		# allocated_amount must be <= min(source_remaining, target_outstanding) + 0.01
		p = _proposal(source_remaining=100.0, target_outstanding=80.0, allocated_amount=80.005)
		ok, reason = run_safeguards(p)
		self.assertTrue(ok, f"expected pass, got {reason}")

	def test_overallocation_skipped(self):
		p = _proposal(source_remaining=100.0, target_outstanding=80.0, allocated_amount=90.0)
		ok, reason = run_safeguards(p)
		self.assertFalse(ok)
		self.assertEqual(reason, "overallocation")
