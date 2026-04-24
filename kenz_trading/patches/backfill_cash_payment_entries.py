import frappe
from frappe.utils import flt


def execute():
    """
    Backfill missing Payment Entries for submitted Cash Sales Invoices.

    Earlier versions of create_payment_entry_for_cash skipped return/credit-note
    invoices and also short-circuited when grand_total was non-positive, which
    meant no refund Payment Entry was created. This patch finds those invoices
    (and any other Cash invoices missing a PE) and creates the appropriate
    Payment Entry.
    """
    from kenz_trading.events.sales_invoice import create_payment_entry_for_cash

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "custom_payment_mode": "Cash",
        },
        fields=["name", "is_return", "grand_total", "rounded_total"],
        order_by="posting_date asc",
    )

    if not invoices:
        print("[backfill_cash_payment_entries] No submitted Cash invoices found.")
        return

    created = 0
    skipped = 0
    failed = 0

    for inv in invoices:
        # Skip if a submitted Payment Entry already references this invoice
        has_pe = frappe.db.exists(
            "Payment Entry Reference",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": inv.name,
                "docstatus": 1,
            },
        )
        if has_pe:
            skipped += 1
            continue

        total = flt(inv.rounded_total or inv.grand_total or 0)
        if total == 0:
            skipped += 1
            continue

        try:
            doc = frappe.get_doc("Sales Invoice", inv.name)
            create_payment_entry_for_cash(doc)
            frappe.db.commit()
            created += 1
        except Exception:
            frappe.db.rollback()
            failed += 1
            frappe.log_error(
                title=f"Backfill Cash PE failed: {inv.name}",
                message=frappe.get_traceback(),
            )

    print(
        f"[backfill_cash_payment_entries] "
        f"Processed {len(invoices)} | Created {created} | Skipped {skipped} | Failed {failed}"
    )
