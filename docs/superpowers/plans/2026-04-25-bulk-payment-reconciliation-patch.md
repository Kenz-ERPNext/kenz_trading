# Bulk Payment Reconciliation Patch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a re-runnable Frappe patch that reconciles unlinked customer/supplier Payment Entries against outstanding invoices and force-unchecks `update_outstanding_for_self` on Sales/Purchase Invoice returns, producing an Excel summary report as the primary output.

**Architecture:** A `kenz_trading.events.reconciliation` package with five focused modules (safeguards, audit, return_flag_fixer, pe_reconciler, return_netter) coordinated by a runner module. The runner exposes whitelisted endpoints and is called by a `bench migrate` patch in dry-run mode by default. All accounting writes go through ERPNext's `PaymentReconciliation` controller and `update_outstanding_amt` to preserve GL integrity.

**Tech Stack:** Python 3.10, Frappe v15, ERPNext v15, `openpyxl` (via `frappe.utils.xlsxutils.make_xlsx`), MySQL/MariaDB.

**Spec:** [docs/superpowers/specs/2026-04-25-bulk-payment-reconciliation-patch-design.md](../specs/2026-04-25-bulk-payment-reconciliation-patch-design.md)

**Target site (initial):** `faris.kenzcloudx.com` (bench root: `/Users/sammishthundiyil/frappe-bench-kenz`).

---

## Conventions & Setup Notes

- **Indentation:** tabs (per `pyproject.toml` ruff config).
- **Bench commands:** all run from `/Users/sammishthundiyil/frappe-bench-kenz` and use `--site faris.kenzcloudx.com`.
- **Imports:** `import frappe` at top of every module; ERPNext imports inside functions to avoid load-order issues during migrations.
- **Existing reference patterns:** `kenz_trading/patches/backfill_cash_payment_entries.py` and `kenz_trading/events/payment_entry_audit.py` — follow these patterns (print-based progress, `frappe.log_error` on exceptions, per-row commit/rollback).
- **Test strategy:** Pure-function modules (`safeguards.py`, `audit.py` row builders) get unit tests. Modules that touch ERPNext's `PaymentReconciliation` controller get smoke tests (dry-run only) executed against `faris.kenzcloudx.com`. We do **not** create real PEs/invoices in test fixtures because the Frappe test framework setup for `kenz_trading` is currently empty.
- **Test runner:** `bench --site faris.kenzcloudx.com run-tests --app kenz_trading --module kenz_trading.events.reconciliation.tests.test_<module>`.

---

## File Structure

```
kenz_trading/
├── kenz_trading/
│   ├── patches.txt                                      # MODIFY: append patch entry
│   └── patches/
│       └── reconcile_outstanding_payments.py            # CREATE: patch entry (dry-run by default)
└── kenz_trading/
    └── events/
        └── reconciliation/
            ├── __init__.py                              # CREATE: empty
            ├── proposal.py                              # CREATE: AllocationProposal dataclass + enums
            ├── safeguards.py                            # CREATE: pure validation functions
            ├── audit.py                                 # CREATE: Excel writer + row builders
            ├── return_flag_fixer.py                     # CREATE: phases 1-2
            ├── pe_reconciler.py                         # CREATE: phases 3-4
            ├── return_netter.py                         # CREATE: phases 5-6
            ├── runner.py                                # CREATE: orchestration + whitelisted endpoints
            └── tests/
                ├── __init__.py                          # CREATE: empty
                ├── test_safeguards.py                   # CREATE: unit tests
                └── test_audit.py                        # CREATE: unit tests
```

Each module has one responsibility:
- `proposal.py` — data contract.
- `safeguards.py` — pure validation, no Frappe DB calls.
- `audit.py` — file writer, no business logic.
- `return_flag_fixer.py` / `pe_reconciler.py` / `return_netter.py` — one phase pair each.
- `runner.py` — composition + entry points.

---

## Task 1: Create `AllocationProposal` data contract

**Files:**
- Create: `kenz_trading/events/reconciliation/__init__.py`
- Create: `kenz_trading/events/reconciliation/proposal.py`
- Create: `kenz_trading/events/reconciliation/tests/__init__.py`

- [ ] **Step 1: Create empty package init files**

```bash
mkdir -p /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading/kenz_trading/events/reconciliation/tests
```

Create `kenz_trading/events/reconciliation/__init__.py` (empty file).
Create `kenz_trading/events/reconciliation/tests/__init__.py` (empty file).

- [ ] **Step 2: Create `proposal.py` with the `AllocationProposal` dataclass**

```python
"""
Data contract shared by all reconciliation phases.

An AllocationProposal represents one *intended* allocation of money
from a source document (Payment Entry or Return Invoice) to a target
invoice. Proposals are produced by the phase modules, validated by
safeguards, optionally executed (live mode), and always recorded
in the audit log.
"""

from dataclasses import dataclass, field
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
```

- [ ] **Step 3: Commit**

```bash
git add kenz_trading/events/reconciliation/__init__.py \
        kenz_trading/events/reconciliation/tests/__init__.py \
        kenz_trading/events/reconciliation/proposal.py
git commit -m "feat(reconciliation): add AllocationProposal data contract"
```

---

## Task 2: Build `safeguards.py` (TDD)

**Files:**
- Create: `kenz_trading/events/reconciliation/tests/test_safeguards.py`
- Create: `kenz_trading/events/reconciliation/safeguards.py`

`safeguards.py` is pure (no Frappe DB calls), so we drive it test-first.

- [ ] **Step 1: Write failing tests**

Create `kenz_trading/events/reconciliation/tests/test_safeguards.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && bench --site faris.kenzcloudx.com run-tests --app kenz_trading --module kenz_trading.events.reconciliation.tests.test_safeguards
```

Expected: ImportError (`safeguards` module does not exist).

- [ ] **Step 3: Implement `safeguards.py`**

Create `kenz_trading/events/reconciliation/safeguards.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && bench --site faris.kenzcloudx.com run-tests --app kenz_trading --module kenz_trading.events.reconciliation.tests.test_safeguards
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add kenz_trading/events/reconciliation/safeguards.py \
        kenz_trading/events/reconciliation/tests/test_safeguards.py
git commit -m "feat(reconciliation): add safeguards with TDD coverage"
```

---

## Task 3: Build `audit.py` (TDD for row builders)

**Files:**
- Create: `kenz_trading/events/reconciliation/tests/test_audit.py`
- Create: `kenz_trading/events/reconciliation/audit.py`

The Excel writer itself depends on `frappe.utils.xlsxutils`, which needs a Frappe context — so we test only the **row-builder** functions in unit tests, then exercise the writer via a smoke run later.

- [ ] **Step 1: Write failing tests**

Create `kenz_trading/events/reconciliation/tests/test_audit.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && bench --site faris.kenzcloudx.com run-tests --app kenz_trading --module kenz_trading.events.reconciliation.tests.test_audit
```

Expected: ImportError.

- [ ] **Step 3: Implement `audit.py`**

Create `kenz_trading/events/reconciliation/audit.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && bench --site faris.kenzcloudx.com run-tests --app kenz_trading --module kenz_trading.events.reconciliation.tests.test_audit
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add kenz_trading/events/reconciliation/audit.py \
        kenz_trading/events/reconciliation/tests/test_audit.py
git commit -m "feat(reconciliation): add AuditBuffer with Excel writer"
```

---

## Task 4: Build `return_flag_fixer.py` (Phases 1 & 2)

**Files:**
- Create: `kenz_trading/events/reconciliation/return_flag_fixer.py`

This module flips `update_outstanding_for_self = 0` on Sales Invoice / Purchase Invoice returns whose `return_against` points to a valid submitted invoice. After flipping, it triggers ERPNext's `update_outstanding_amt` so both the return and the original invoice recompute outstanding via the GL.

- [ ] **Step 1: Implement `return_flag_fixer.py`**

Create `kenz_trading/events/reconciliation/return_flag_fixer.py`:

```python
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
```

- [ ] **Step 2: Lint check**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading && python -m py_compile kenz_trading/events/reconciliation/return_flag_fixer.py
```

Expected: no output (clean compile).

- [ ] **Step 3: Commit**

```bash
git add kenz_trading/events/reconciliation/return_flag_fixer.py
git commit -m "feat(reconciliation): phases 1-2 force-uncheck update_outstanding_for_self on returns"
```

---

## Task 5: Build `pe_reconciler.py` (Phases 3 & 4)

**Files:**
- Create: `kenz_trading/events/reconciliation/pe_reconciler.py`

Wraps ERPNext's `PaymentReconciliation` controller per party.

- [ ] **Step 1: Implement `pe_reconciler.py`**

Create `kenz_trading/events/reconciliation/pe_reconciler.py`:

```python
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
```

- [ ] **Step 2: Compile check**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading && python -m py_compile kenz_trading/events/reconciliation/pe_reconciler.py
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add kenz_trading/events/reconciliation/pe_reconciler.py
git commit -m "feat(reconciliation): phases 3-4 reconcile unlinked PEs via PaymentReconciliation"
```

---

## Task 6: Build `return_netter.py` (Phases 5 & 6)

**Files:**
- Create: `kenz_trading/events/reconciliation/return_netter.py`

Handles leftover returns whose `return_against` was missing/cancelled (Phase 1/2 didn't process them). Uses `PaymentReconciliation` again because credit/debit notes appear in its `payments` collection alongside actual PEs.

- [ ] **Step 1: Implement `return_netter.py`**

Create `kenz_trading/events/reconciliation/return_netter.py`:

```python
"""
Phases 5 & 6: net leftover SI/PI returns (those with no usable
return_against) against positive invoices for the same party. Reuses
the PaymentReconciliation controller — credit/debit notes are exposed
in its `payments` collection (see PaymentReconciliation.get_dr_or_cr_notes).
"""

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
```

- [ ] **Step 2: Compile check**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading && python -m py_compile kenz_trading/events/reconciliation/return_netter.py
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add kenz_trading/events/reconciliation/return_netter.py
git commit -m "feat(reconciliation): phases 5-6 net leftover returns against positive invoices"
```

---

## Task 7: Build `runner.py` (orchestration + whitelisted endpoints)

**Files:**
- Create: `kenz_trading/events/reconciliation/runner.py`

- [ ] **Step 1: Implement `runner.py`**

Create `kenz_trading/events/reconciliation/runner.py`:

```python
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
```

- [ ] **Step 2: Compile check**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading && python -m py_compile kenz_trading/events/reconciliation/runner.py
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add kenz_trading/events/reconciliation/runner.py
git commit -m "feat(reconciliation): runner with whitelisted run_all / run_phase / run_for_party"
```

---

## Task 8: Create patch entry and register it

**Files:**
- Create: `kenz_trading/patches/reconcile_outstanding_payments.py`
- Modify: `kenz_trading/patches.txt` (append one line)

- [ ] **Step 1: Create patch file**

Create `kenz_trading/patches/reconcile_outstanding_payments.py`:

```python
"""
Bulk Payment Reconciliation patch.

Runs in DRY-RUN mode by default — produces an Excel summary report at
sites/<site>/private/files/reconciliation_audit_<timestamp>.xlsx without
modifying any data. To commit the proposed allocations, run the runner
explicitly:

    bench --site <site> execute \\
        kenz_trading.events.reconciliation.runner.run_all \\
        --kwargs "{'dry_run': 0}"

Spec: docs/superpowers/specs/2026-04-25-bulk-payment-reconciliation-patch-design.md
"""


def execute():
	from kenz_trading.events.reconciliation.runner import run_all
	result = run_all(dry_run=1)
	print(f"[reconcile_outstanding_payments] audit_file={result['path']}")
	print(f"[reconcile_outstanding_payments] totals={result['totals']}")
```

- [ ] **Step 2: Register patch in `patches.txt`**

Read `kenz_trading/patches.txt` and append `kenz_trading.patches.reconcile_outstanding_payments` to the `[post_model_sync]` section, after `kenz_trading.patches.backfill_cash_payment_entries`.

Expected file contents after edit (post_model_sync section):

```
[post_model_sync]
kenz_trading.patches.backfill_cash_payment_entries
kenz_trading.patches.reconcile_outstanding_payments
```

- [ ] **Step 3: Verify patches.txt**

```bash
cat /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading/kenz_trading/patches.txt
```

Expected output: includes both patch entries under `[post_model_sync]`.

- [ ] **Step 4: Commit**

```bash
git add kenz_trading/patches/reconcile_outstanding_payments.py kenz_trading/patches.txt
git commit -m "feat(reconciliation): register dry-run patch in patches.txt"
```

---

## Task 9: Smoke test on `faris.kenzcloudx.com` (dry-run)

**Files:** none modified — verification only.

- [ ] **Step 1: Run dry-run via bench execute**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com execute \
  kenz_trading.events.reconciliation.runner.run_all \
  --kwargs "{'dry_run': 1}"
```

Expected output: prints per-phase summary lines and the audit file path. No errors.

- [ ] **Step 2: Verify audit Excel exists and has the five sheets**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
python3 -c "
import openpyxl, glob, os
files = sorted(glob.glob('sites/faris.kenzcloudx.com/private/files/reconciliation_audit_*.xlsx'))
assert files, 'no audit file produced'
wb = openpyxl.load_workbook(files[-1], read_only=True)
print('file:', files[-1])
print('sheets:', wb.sheetnames)
for s in wb.sheetnames:
    ws = wb[s]
    print(f'  {s}: {ws.max_row} rows x {ws.max_column} cols')
"
```

Expected: lists `Summary`, `Reconciled`, `Skipped`, `Failed`, `Flag Flips` with non-trivial row counts in at least Summary + (Reconciled or Flag Flips).

- [ ] **Step 3: Sanity-check that no data was modified (dry-run)**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com execute frappe.client.get_count \
  --kwargs "{'doctype': 'Payment Entry', 'filters': [['docstatus','=',1],['party_type','=','Customer'],['unallocated_amount','>',0]]}"
```

Expected: count is **125** (unchanged from pre-run baseline).

- [ ] **Step 4: Verify no errors logged**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com execute frappe.client.get_count \
  --kwargs "{'doctype': 'Error Log', 'filters': [['error', 'like', '%reconciliation%'], ['creation', '>', '2026-04-25']]}"
```

Expected: 0 (or only `flag flip` entries on records that legitimately have a cancelled `return_against`).

- [ ] **Step 5: Commit (no code change, but mark milestone)**

If new reviewer notes are added to the spec or plan during smoke test, commit them. Otherwise no commit.

---

## Task 10: Sub-skill checkpoint — present audit Excel to user for review

This task has no code. Hand the dry-run audit Excel to the user. They will:

1. Open `sites/faris.kenzcloudx.com/private/files/reconciliation_audit_<timestamp>.xlsx`
2. Inspect the **Summary** sheet for per-phase totals
3. Spot-check 5–10 rows in **Reconciled**, **Skipped**, and **Flag Flips** sheets
4. Approve commit or request changes

Only after explicit user approval do we proceed to Task 11.

- [ ] **Step 1: Print audit file path and download URL** for the user.
- [ ] **Step 2: Wait for user approval.**

---

## Task 11: Live execution on `faris.kenzcloudx.com`

**Files:** none modified — execution only.

- [ ] **Step 1: Take a database backup first**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com backup --with-files
```

Expected: backup file path printed.

- [ ] **Step 2: Run live reconciliation**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com execute \
  kenz_trading.events.reconciliation.runner.run_all \
  --kwargs "{'dry_run': 0}"
```

Expected: per-phase summary printed, new audit Excel produced (live mode).

- [ ] **Step 3: Verify outstanding/unallocated counts dropped**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com execute frappe.client.get_count \
  --kwargs "{'doctype': 'Payment Entry', 'filters': [['docstatus','=',1],['party_type','=','Customer'],['unallocated_amount','>',0]]}"
```

Expected: significantly less than 125.

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz && \
bench --site faris.kenzcloudx.com execute frappe.client.get_count \
  --kwargs "{'doctype': 'Sales Invoice', 'filters': [['docstatus','=',1],['outstanding_amount','!=',0]]}"
```

Expected: significantly less than 342.

- [ ] **Step 4: Inspect live audit Excel** — confirm Reconciled sheet shows actual amounts and the Failed sheet is empty (or contains only known-acceptable failures).

- [ ] **Step 5: If everything looks good, push the branch**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/kenz_trading && git push origin faris
```

Expected: push succeeds.

---

## Self-Review Notes

**Spec coverage:**
- §3 scope (6 phases) → Tasks 4, 5, 6 each cover a phase pair.
- §4 safeguards → Task 2 implements all six checks with TDD.
- §5 architecture (one file per responsibility) → Tasks 1–7 mirror the file layout exactly.
- §6 execution flow (savepoint per row) → Tasks 4, 5, 6 each wrap allocations in `frappe.db.savepoint`.
- §7 final Excel output (5 sheets) → Task 3 implements all five sheets with row-builder unit tests.
- §8 dry-run-by-default on `bench migrate` → Task 8 patch entry hardcodes `dry_run=1`; live commit requires explicit `bench execute`.
- §9 AllocationProposal contract → Task 1 implements the dataclass exactly as specified.
- §10 operational plan (review audit then commit) → Tasks 9–11 enforce this with an explicit user-approval checkpoint at Task 10.

**Type consistency check:**
- `AllocationProposal` field names (`source_remaining`, `target_outstanding`, `allocated_amount`, etc.) used identically in `safeguards.py`, `audit.py`, `pe_reconciler.py`, `return_netter.py`.
- Phase constants (`PHASE_*`) imported from `proposal.py` everywhere — no string literals.
- `AuditBuffer` methods (`reconciled`, `skipped`, `failed`, `flag_flip`, `build_summary_rows`, `write_excel`) match between `audit.py` definition and `runner.py`/phase modules' calls.
- ERPNext function names (`update_outstanding_amt`, `PaymentReconciliation.get_unreconciled_entries`, `allocate_entries`, `reconcile`) verified against installed source at `apps/erpnext/erpnext/accounts/doctype/payment_reconciliation/payment_reconciliation.py`.

**Placeholder scan:** none of the steps contain TBD/TODO/handle-edge-cases — every step shows actual code or an exact command with expected output.
