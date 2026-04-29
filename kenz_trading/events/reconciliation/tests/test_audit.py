import unittest
from datetime import date

from kenz_trading.events.reconciliation.audit import (
	AuditBuffer,
	RECONCILED_HEADER,
	SKIPPED_HEADER,
	FAILED_HEADER,
	SUMMARY_HEADER,
	FLAG_FLIP_HEADER,
)
from kenz_trading.events.reconciliation.proposal import (
	AllocationProposal,
	PHASE_RECONCILE_RECEIVE_PES,
	PHASE_FLAG_FIX_SI_RETURNS,
)


def _proposal():
	return AllocationProposal(
		phase=PHASE_RECONCILE_RECEIVE_PES,
		party_type="Customer",
		party="C-1",
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


class TestAuditBuffer(unittest.TestCase):
	def test_records_reconciled_row(self):
		buf = AuditBuffer(mode="dry_run")
		buf.reconciled(_proposal())
		self.assertEqual(len(buf.reconciled_rows), 1)
		row = buf.reconciled_rows[0]
		self.assertEqual(row[0], PHASE_RECONCILE_RECEIVE_PES)
		self.assertEqual(row[2], "C-1")
		self.assertEqual(row[5], "SI-1")

	def test_records_skipped_with_reason(self):
		buf = AuditBuffer(mode="dry_run")
		buf.skipped(_proposal(), reason="currency_mismatch")
		self.assertEqual(len(buf.skipped_rows), 1)
		self.assertEqual(buf.skipped_rows[0][-1], "currency_mismatch")

	def test_records_failed_with_exception(self):
		buf = AuditBuffer(mode="live")
		try:
			raise ValueError("boom")
		except ValueError as e:
			buf.failed(_proposal(), e, traceback_text="trace excerpt")
		self.assertEqual(len(buf.failed_rows), 1)
		self.assertEqual(buf.failed_rows[0][-3], "ValueError")
		self.assertEqual(buf.failed_rows[0][-2], "boom")

	def test_summary_aggregates_per_phase(self):
		buf = AuditBuffer(mode="live")
		p = _proposal()
		buf.reconciled(p)
		buf.reconciled(p)
		buf.skipped(p, reason="date_order")
		summary = buf.build_summary_rows()
		# one row per phase touched
		self.assertEqual(len(summary), 1)
		row = summary[0]
		# columns: phase, mode, attempted, succeeded, skipped, failed, amount, parties, started, finished
		self.assertEqual(row[0], PHASE_RECONCILE_RECEIVE_PES)
		self.assertEqual(row[1], "live")
		self.assertEqual(row[2], 3)  # attempted
		self.assertEqual(row[3], 2)  # succeeded
		self.assertEqual(row[4], 1)  # skipped
		self.assertEqual(row[5], 0)  # failed
		self.assertAlmostEqual(row[6], 1000.0)  # amount

	def test_flag_flip_row_recorded(self):
		buf = AuditBuffer(mode="live")
		buf.flag_flip(
			phase=PHASE_FLAG_FIX_SI_RETURNS,
			return_doc="SR/FA2672",
			return_against="INV/FA/18725",
			original_before=500.0,
			original_after=400.0,
			return_before=-100.0,
			return_after=0.0,
		)
		self.assertEqual(len(buf.flag_flip_rows), 1)


class TestHeaders(unittest.TestCase):
	def test_headers_have_expected_columns(self):
		self.assertIn("phase", SUMMARY_HEADER)
		self.assertIn("allocated_amount", RECONCILED_HEADER)
		self.assertIn("skip_reason", SKIPPED_HEADER)
		self.assertIn("exception_class", FAILED_HEADER)
		self.assertIn("return_doc", FLAG_FLIP_HEADER)
