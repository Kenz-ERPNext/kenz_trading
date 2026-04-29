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
