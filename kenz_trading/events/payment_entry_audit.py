"""
Audit helpers for Payment Entries after the Cash backfill patch.

The backfill patch (kenz_trading.patches.backfill_cash_payment_entries)
created Payment Entries for Sales Invoices that were missing one. In
parallel, users have historically entered Payment Entries manually
without linking them to a Sales Invoice. After the backfill we need to
identify those manual/unlinked PEs so they can be reviewed and
reconciled.
"""

import csv
import os
import frappe
from frappe.utils import flt, get_site_path


def _base_conditions():
    """
    PE is considered 'unlinked to Sales Invoice' when it has NO row in
    tabPayment Entry Reference pointing to a Sales Invoice.
    We intentionally include PEs that reference other doctypes (e.g.
    Journal Entry) because they still aren't tied to an SI.
    """
    return """
        pe.docstatus = 1
        AND pe.party_type = 'Customer'
        AND NOT EXISTS (
            SELECT 1 FROM `tabPayment Entry Reference` per
            WHERE per.parent = pe.name
                AND per.reference_doctype = 'Sales Invoice'
        )
    """


@frappe.whitelist()
def get_unlinked_customer_payment_entries(from_date=None, to_date=None, mode_of_payment=None):
    """
    Return submitted Customer Payment Entries with NO Sales Invoice
    reference. Optionally filter by date range and mode of payment.
    """
    params = {}
    extra = ""
    if from_date:
        extra += " AND pe.posting_date >= %(from_date)s"
        params["from_date"] = from_date
    if to_date:
        extra += " AND pe.posting_date <= %(to_date)s"
        params["to_date"] = to_date
    if mode_of_payment:
        extra += " AND pe.mode_of_payment = %(mop)s"
        params["mop"] = mode_of_payment

    rows = frappe.db.sql(
        f"""
        SELECT
            pe.name,
            pe.posting_date,
            pe.payment_type,
            pe.party,
            pe.party_name,
            pe.mode_of_payment,
            pe.paid_amount,
            pe.received_amount,
            pe.reference_no,
            pe.reference_date,
            pe.paid_from,
            pe.paid_to,
            pe.remarks,
            pe.owner,
            pe.creation,
            pe.modified_by
        FROM `tabPayment Entry` pe
        WHERE {_base_conditions()}
            {extra}
        ORDER BY pe.posting_date DESC, pe.creation DESC
        """,
        params,
        as_dict=True,
    )
    return rows


@frappe.whitelist()
def find_potential_duplicates(tolerance=0.01):
    """
    For each unlinked Customer PE, check if there is another submitted PE
    on the same date, same customer, same amount that IS linked to a
    Sales Invoice. Those are candidates for duplicates against the
    backfill-created entries.
    """
    tolerance = flt(tolerance)
    unlinked = get_unlinked_customer_payment_entries()
    dupes = []

    for pe in unlinked:
        matches = frappe.db.sql(
            """
            SELECT
                pe2.name AS linked_pe,
                per.reference_name AS sales_invoice,
                pe2.paid_amount,
                pe2.posting_date,
                pe2.owner AS linked_owner,
                pe2.creation AS linked_creation
            FROM `tabPayment Entry` pe2
            INNER JOIN `tabPayment Entry Reference` per
                ON per.parent = pe2.name AND per.reference_doctype = 'Sales Invoice'
            WHERE pe2.docstatus = 1
                AND pe2.party_type = 'Customer'
                AND pe2.party = %(party)s
                AND pe2.posting_date = %(posting_date)s
                AND ABS(pe2.paid_amount - %(amount)s) <= %(tol)s
                AND pe2.name != %(name)s
            """,
            {
                "party": pe.party,
                "posting_date": pe.posting_date,
                "amount": pe.paid_amount,
                "tol": tolerance,
                "name": pe.name,
            },
            as_dict=True,
        )
        if matches:
            dupes.append({
                "unlinked_pe": pe.name,
                "posting_date": pe.posting_date,
                "party": pe.party,
                "party_name": pe.party_name,
                "paid_amount": pe.paid_amount,
                "mode_of_payment": pe.mode_of_payment,
                "unlinked_owner": pe.owner,
                "unlinked_creation": pe.creation,
                "matches": matches,
            })
    return dupes


@frappe.whitelist()
def export_unlinked_pe_report(from_date=None, to_date=None, mode_of_payment=None):
    """
    Write a CSV report to sites/<site>/private/files/ and return
    (absolute_path, row_count). Use this to share with the customer.
    """
    rows = get_unlinked_customer_payment_entries(
        from_date=from_date, to_date=to_date, mode_of_payment=mode_of_payment
    )

    site_path = get_site_path("private", "files")
    os.makedirs(site_path, exist_ok=True)
    filename = f"unlinked_customer_payment_entries_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(site_path, filename)

    if not rows:
        with open(filepath, "w", newline="") as f:
            f.write("No unlinked Customer Payment Entries found.\n")
        return {"path": filepath, "count": 0}

    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (v if v is not None else "") for k, v in r.items()})

    total_amount = sum(flt(r.get("paid_amount")) for r in rows)
    summary = {
        "path": filepath,
        "count": len(rows),
        "total_amount": total_amount,
        "download_url": f"/private/files/{filename}",
    }
    return summary
