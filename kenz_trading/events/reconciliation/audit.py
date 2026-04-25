"""
Audit buffer and Excel writer for reconciliation runs.

Buffers in memory during a run; emits a single Excel workbook at the
end with five sheets: Summary, Reconciled, Skipped, Failed, Flag Flips.
"""

import os
import traceback
from collections import defaultdict
from datetime import datetime
from typing import List, Tuple

import frappe
from frappe.utils import get_site_path
from frappe.utils.xlsxutils import make_xlsx

from kenz_trading.events.reconciliation.proposal import AllocationProposal


SUMMARY_HEADER = (
	"phase", "mode", "attempted", "succeeded", "skipped", "failed",
	"amount_reconciled", "parties_touched", "started_at", "finished_at",
)

RECONCILED_HEADER = (
	"phase", "party_type", "party", "source_doc", "source_type",
	"target_invoice", "allocated_amount", "mode_of_payment",
	"source_date", "target_date",
)

SKIPPED_HEADER = RECONCILED_HEADER + ("skip_reason",)

FAILED_HEADER = RECONCILED_HEADER + (
	"exception_class", "exception_message", "traceback_excerpt",
)

FLAG_FLIP_HEADER = (
	"phase", "return_doc", "return_against",
	"original_outstanding_before", "original_outstanding_after",
	"return_outstanding_before", "return_outstanding_after",
)


def _proposal_to_row(p: AllocationProposal) -> Tuple:
	return (
		p.phase, p.party_type, p.party,
		p.source_name, p.source_doctype,
		p.target_name, float(p.allocated_amount),
		p.mode_of_payment or "",
		p.source_posting_date.isoformat() if p.source_posting_date else "",
		p.target_posting_date.isoformat() if p.target_posting_date else "",
	)


class AuditBuffer:
	def __init__(self, mode: str):
		self.mode = mode  # "dry_run" or "live"
		self.started_at = datetime.now()
		self.finished_at = None
		self.reconciled_rows: List[Tuple] = []
		self.skipped_rows: List[Tuple] = []
		self.failed_rows: List[Tuple] = []
		self.flag_flip_rows: List[Tuple] = []
		# track parties per phase for summary
		self._parties_per_phase = defaultdict(set)

	def reconciled(self, p: AllocationProposal) -> None:
		self.reconciled_rows.append(_proposal_to_row(p))
		self._parties_per_phase[p.phase].add(p.party)

	def skipped(self, p: AllocationProposal, reason: str) -> None:
		self.skipped_rows.append(_proposal_to_row(p) + (reason,))
		self._parties_per_phase[p.phase].add(p.party)

	def failed(self, p: AllocationProposal, exc: Exception, traceback_text: str = "") -> None:
		excerpt = (traceback_text or traceback.format_exc())[-1500:]
		self.failed_rows.append(
			_proposal_to_row(p) + (type(exc).__name__, str(exc), excerpt)
		)
		self._parties_per_phase[p.phase].add(p.party)

	def flag_flip(
		self,
		phase: str,
		return_doc: str,
		return_against: str,
		original_before: float,
		original_after: float,
		return_before: float,
		return_after: float,
	) -> None:
		self.flag_flip_rows.append((
			phase, return_doc, return_against,
			float(original_before), float(original_after),
			float(return_before), float(return_after),
		))

	def build_summary_rows(self) -> List[Tuple]:
		"""One row per phase that had any activity."""
		per_phase = defaultdict(lambda: {"attempted": 0, "succeeded": 0, "skipped": 0, "failed": 0, "amount": 0.0})
		for row in self.reconciled_rows:
			ph = row[0]
			per_phase[ph]["attempted"] += 1
			per_phase[ph]["succeeded"] += 1
			per_phase[ph]["amount"] += float(row[6])
		for row in self.skipped_rows:
			ph = row[0]
			per_phase[ph]["attempted"] += 1
			per_phase[ph]["skipped"] += 1
		for row in self.failed_rows:
			ph = row[0]
			per_phase[ph]["attempted"] += 1
			per_phase[ph]["failed"] += 1

		started = self.started_at.isoformat()
		finished = (self.finished_at or datetime.now()).isoformat()

		summary = []
		for phase, agg in per_phase.items():
			summary.append((
				phase, self.mode,
				agg["attempted"], agg["succeeded"], agg["skipped"], agg["failed"],
				agg["amount"], len(self._parties_per_phase[phase]),
				started, finished,
			))
		return summary

	def write_excel(self, filename: str = None) -> str:
		"""
		Write the workbook to <site>/private/files and return the
		absolute path. Caller may also build a download URL from the
		basename.
		"""
		self.finished_at = datetime.now()
		ts = self.finished_at.strftime("%Y%m%d_%H%M%S")
		filename = filename or f"reconciliation_audit_{ts}.xlsx"

		sheets = {
			"Summary": [list(SUMMARY_HEADER)] + [list(r) for r in self.build_summary_rows()],
			"Reconciled": [list(RECONCILED_HEADER)] + [list(r) for r in self.reconciled_rows],
			"Skipped": [list(SKIPPED_HEADER)] + [list(r) for r in self.skipped_rows],
			"Failed": [list(FAILED_HEADER)] + [list(r) for r in self.failed_rows],
			"Flag Flips": [list(FLAG_FLIP_HEADER)] + [list(r) for r in self.flag_flip_rows],
		}

		# make_xlsx accepts only one sheet at a time pre-v15. Compose manually.
		import openpyxl
		wb = openpyxl.Workbook()
		# remove default sheet
		wb.remove(wb.active)
		for name, rows in sheets.items():
			ws = wb.create_sheet(title=name)
			for row in rows:
				ws.append(row)

		out_dir = get_site_path("private", "files")
		os.makedirs(out_dir, exist_ok=True)
		path = os.path.join(out_dir, filename)
		wb.save(path)
		return path
