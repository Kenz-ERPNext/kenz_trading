# Bulk Payment Reconciliation Patch — Design

**Date:** 2026-04-25
**Site (initial target):** `faris.kenzcloudx.com`
**App:** `kenz_trading`
**Author:** Sammish Thundiyil

---

## 1. Problem

After the cash-payment backfill patch (`backfill_cash_payment_entries`), the `faris` site still has a large reconciliation backlog driven by two distinct issues:

1. **Unlinked customer Payment Entries.** 125 submitted PEs with `unallocated_amount > 0` totalling ~264,675 AED exist with no Sales Invoice reference, while 342 Sales Invoices remain outstanding (~458,694 AED). 62 customers appear on both sides — these are reconciliation candidates that were created in the wrong order or via shortcuts that bypassed the invoice → payment link.
2. **Sales Invoice Returns (Credit Notes) with `update_outstanding_for_self = 1`.** 46 outstanding returns carry their own negative outstanding instead of reducing the original invoice's outstanding. The same condition exists on Purchase Invoice Returns (Debit Notes).

Manual reconciliation through ERPNext's `Payment Reconciliation` UI is too slow at this volume. We need a re-runnable patch that performs reconciliation safely, with audit trail and dry-run-first behaviour.

---

## 2. Goals & Non-Goals

**Goals**
- Reconcile unlinked customer Receive PEs against outstanding Sales Invoices using FIFO with safeguards.
- Reconcile unlinked supplier Pay PEs against outstanding Purchase Invoices using FIFO with safeguards.
- Force `update_outstanding_for_self = 0` on Sales Invoice Returns and Purchase Invoice Returns that carry a `return_against` reference, so the return reduces the original invoice's outstanding directly.
- Net leftover SI/PI returns against positive invoices for the same party when `return_against` is missing or the original is cancelled.
- Generate a per-run audit Excel covering reconciled, skipped, and failed allocations.
- Be idempotent — re-running the patch must not double-allocate.
- Default to dry-run on first `bench migrate`; commit only on explicit invocation.

**Non-Goals**
- Multi-currency reconciliation (skip non-base-currency PEs).
- Multi-company netting (skip cross-company allocations).
- Supplier↔Customer netting (parties that are both customer and supplier).
- Journal-Entry-based reconciliations.
- Reversing prior reconciliations.
- UI/dashboard for the audit output.

---

## 3. Scope of Operations

| # | Phase | Source | Target | Direction |
|---|---|---|---|---|
| 1 | `flag_fix_si_returns` | SI Returns where `return_against` set & `update_outstanding_for_self=1` | Original Sales Invoice | Redirect outstanding |
| 2 | `flag_fix_pi_returns` | PI Returns where `return_against` set & `update_outstanding_for_self=1` | Original Purchase Invoice | Redirect outstanding |
| 3 | `reconcile_receive_pes` | Customer PEs, `payment_type=Receive`, `unallocated_amount > 0` | Outstanding Sales Invoices (positive) | FIFO per customer |
| 4 | `reconcile_pay_pes` | Supplier PEs, `payment_type=Pay`, `unallocated_amount > 0` | Outstanding Purchase Invoices (positive) | FIFO per supplier |
| 5 | `net_leftover_si_returns` | Submitted SI Returns with no usable `return_against`, still outstanding | Positive Sales Invoices, same customer | FIFO |
| 6 | `net_leftover_pi_returns` | Submitted PI Returns with no usable `return_against`, still outstanding | Positive Purchase Invoices, same supplier | FIFO |

Phases 1–2 must run first because flipping the flag changes which invoices appear "outstanding" in phases 3–6.

---

## 4. Safeguards

Every proposed allocation must pass **all** the following checks before executing. Any failed check skips the row and writes a reason to the audit log.

| Check | Skip Reason |
|---|---|
| Source and target share the same `currency` | `currency_mismatch` |
| Source and target share the same `company` | `company_mismatch` |
| Source `posting_date >= target.posting_date` | `date_order` |
| Target invoice is `docstatus=1` AND `outstanding_amount != 0` | `already_settled` |
| Source PE/Return is `docstatus=1` AND has remaining unallocated/outstanding | `no_unallocated` |
| For phases 1–2: original invoice (`return_against`) exists, `docstatus=1` | Falls back to FIFO (phase 5/6), not skipped outright |
| Allocation amount = `min(source_remaining, target_outstanding)` | (always capped, partial allocation allowed) |

**Tolerance:** All amount comparisons use a `0.01` rounding tolerance (single fils). Allocations are rounded to 2 decimals.

**Idempotency:** Each run re-queries `unallocated_amount` and `outstanding_amount` live; nothing is cached across runs. Re-running on a fully reconciled site is a no-op.

---

## 5. Architecture

### 5.1 File Layout

```
kenz_trading/
├── patches/
│   └── reconcile_outstanding_payments.py     # patch entry — calls runner.run_all(dry_run=1)
└── events/
    └── reconciliation/
        ├── __init__.py
        ├── runner.py            # orchestration, phase dispatch, audit assembly
        ├── return_flag_fixer.py # Phases 1–2
        ├── pe_reconciler.py     # Phases 3–4
        ├── return_netter.py     # Phases 5–6
        ├── safeguards.py        # Section 4 validations
        └── audit.py             # Excel writer + Frappe error log integration
```

Each module has one clear responsibility, communicates through a small interface (`AllocationProposal` dataclass), and can be tested or invoked independently.

### 5.2 Underlying Mechanisms

- **Phases 1–2 (flag flip):** `frappe.db.set_value("Sales Invoice", name, "update_outstanding_for_self", 0)` followed by ERPNext's `update_outstanding_amt(account, party_type, party, against_voucher_type, against_voucher)` to recompute outstanding for both the return and the original invoice.
- **Phases 3–4 (PE reconciliation):** Instantiate `erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation.PaymentReconciliation` per party. Populate `invoices` and `payments` child tables. Call `allocate_entries(args)` then `reconcile()`. This goes through ERPNext's tested code path — no raw GL writes.
- **Phases 5–6 (leftover return netting):** Same `PaymentReconciliation` controller — credit/debit notes appear alongside payments in its `payments` collection.

No raw `tabGL Entry` mutation. Accounting integrity is preserved by always going through framework APIs.

### 5.3 Whitelisted Endpoints

Each accepts a `dry_run` flag (default `1`).

- `kenz_trading.events.reconciliation.runner.run_all(dry_run=1)`
- `kenz_trading.events.reconciliation.runner.run_phase(phase_name, dry_run=1)`
- `kenz_trading.events.reconciliation.runner.run_for_party(party_type, party, dry_run=1)`

These let an admin run the patch incrementally — one phase or one party at a time — without modifying the patch file.

---

## 6. Execution Flow

```
For each phase in [1..6]:
    proposals = build_proposals(phase)         # apply FIFO, party grouping
    for proposal in proposals:
        ok, reason = run_safeguards(proposal)
        if not ok:
            audit.skip(proposal, reason)
            continue
        if dry_run:
            audit.would_reconcile(proposal)
            continue
        try:
            frappe.db.savepoint(f"sp_{phase}_{proposal.id}")
            execute(proposal)                  # via ERPNext PaymentReconciliation
            frappe.db.commit()
            audit.reconciled(proposal)
        except Exception as e:
            frappe.db.rollback(save_point=f"sp_{phase}_{proposal.id}")
            audit.failed(proposal, e)
            frappe.log_error(title="Reconciliation Patch Failure", message=...)
```

Each allocation is wrapped in its own savepoint — one bad row never blocks the rest of the batch.

---

## 7. Final Output — Summary Report (Excel)

The **primary deliverable** of every patch run (dry-run and live) is a single Excel workbook. The runner returns the file path and a download URL on completion; the patch entry also prints both to the bench log.

**Location:** `sites/<site>/private/files/reconciliation_audit_<YYYYMMDD_HHMMSS>.xlsx`

**Sheet 1 — Summary (the headline report)** — one row per phase plus a grand-total row:

| Column | Example |
|---|---|
| `phase` | `reconcile_receive_pes` |
| `mode` | `dry_run` / `live` |
| `attempted` | 187 |
| `succeeded` | 162 |
| `skipped` | 21 |
| `failed` | 4 |
| `amount_reconciled` | 261,438.55 |
| `parties_touched` | 58 |
| `started_at` / `finished_at` | timestamps |

**Sheet 2 — Reconciled** — every successful allocation: `phase | party_type | party | source_doc | source_type | target_invoice | allocated_amount | mode_of_payment | source_date | target_date`

**Sheet 3 — Skipped** — same columns + `skip_reason` (`currency_mismatch`, `date_order`, `already_settled`, `no_unallocated`, etc.)

**Sheet 4 — Failed** — same columns + `exception_class | exception_message | traceback_excerpt`

**Sheet 5 — Flag Flips** — separate sheet for phases 1–2: `phase | return_doc | return_against | original_outstanding_before | original_outstanding_after | return_outstanding_before | return_outstanding_after`

The Summary sheet alone gives the admin a single-glance pass/fail picture; the detail sheets are for drilling into specific rows. Filename and download URL are also returned by all whitelisted runner endpoints so the file can be fetched programmatically.

---

## 8. Default Behaviour on `bench migrate`

The patch entry (`patches/reconcile_outstanding_payments.py`) calls `runner.run_all(dry_run=1)` and prints:

```
Reconciliation Patch — DRY RUN COMPLETE
  Audit file: <path>
  To commit: bench --site <site> execute \
    kenz_trading.events.reconciliation.runner.run_all --kwargs "{'dry_run': 0}"
```

This guarantees a one-shot `bench migrate` cannot accidentally reconcile production data. Live commit requires an explicit, separate command.

The patch is registered in `patches.txt` under `[post_model_sync]` after `kenz_trading.patches.backfill_cash_payment_entries`.

---

## 9. Data Model — `AllocationProposal`

The contract between the proposal builders and the executor:

```python
@dataclass
class AllocationProposal:
    phase: str                          # e.g. "reconcile_receive_pes"
    party_type: str                     # "Customer" | "Supplier"
    party: str
    source_doctype: str                 # "Payment Entry" | "Sales Invoice" | "Purchase Invoice"
    source_name: str
    source_remaining: float             # before this allocation
    target_doctype: str                 # "Sales Invoice" | "Purchase Invoice"
    target_name: str
    target_outstanding: float           # before this allocation
    allocated_amount: float             # min(source_remaining, target_outstanding) capped
    currency: str
    company: str
    source_posting_date: date
    target_posting_date: date
    mode_of_payment: str | None
    notes: str = ""                     # populated by safeguards on skip
```

---

## 10. Operational Plan

1. Deploy patch to faris site via `bench migrate`. Patch runs in dry-run, audit Excel is written.
2. Admin reviews the audit Excel in the site's `private/files`.
3. If acceptable, admin runs `bench --site faris.kenzcloudx.com execute kenz_trading.events.reconciliation.runner.run_all --kwargs "{'dry_run': 0}"`.
4. Live audit Excel is generated and reviewed.
5. If individual customers need rework, use `run_for_party` to retry just those.

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Wrong PE allocated to wrong invoice (FIFO mistake) | Dry-run by default + per-party retry endpoint + audit Excel before commit |
| Cancelled/amended invoice cited in `return_against` | Phase 1/2 falls back to phase 5/6 (FIFO netting) |
| ERPNext `PaymentReconciliation` raises on edge cases (currency, dimensions) | Per-row savepoint isolates failure; row goes to Failed sheet, run continues |
| Patch re-run double-allocates | Idempotent: re-queries live `unallocated_amount`/`outstanding_amount` each run |
| Long run time on production site | Whitelisted `run_phase` and `run_for_party` allow incremental execution |
| Multi-currency PE silently corrupts books | Hard-skipped by `currency_mismatch` safeguard |

---

## 12. Out of Scope (Explicit)

- Foreign-currency PEs.
- Cross-company allocations.
- Reversal/un-reconciliation of prior reconciliations.
- Reconciliation against Journal Entries (DR/CR notes posted as JV).
- UI dashboard, scheduled re-runs, notifications.

These can be addressed in follow-up work if needed.
