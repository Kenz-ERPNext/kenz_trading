import frappe
from frappe.utils import flt, cint
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from kenz_trading.events.sales_invoice import fix_inclusive_tax_rounding

import traceback


class CustomSalesInvoice(SalesInvoice):
    def calculate_taxes_and_totals(self):
        """Override to fix inclusive tax rounding immediately after every
        ERPNext tax calculation."""
        super().calculate_taxes_and_totals()

        old_net = self.net_total
        old_gt = self.grand_total
        fix_inclusive_tax_rounding(self)

        if self.net_total != old_net or self.grand_total != old_gt:
            caller = "".join(traceback.format_stack()[-3:-1])
            frappe.log_error(
                title="Tax Fix - calc_taxes",
                message=(
                    f"Net: {old_net} → {self.net_total}\n"
                    f"Grand: {old_gt} → {self.grand_total}\n"
                    f"Caller:\n{caller}"
                ),
            )

    def db_update(self):
        """Apply fix right before every DB write of the parent document."""
        old_net = self.net_total
        old_gt = self.grand_total
        fix_inclusive_tax_rounding(self)

        if self.net_total != old_net or self.grand_total != old_gt:
            frappe.log_error(
                title="Tax Fix - db_update",
                message=(
                    f"Fix applied in db_update:\n"
                    f"Net: {old_net} → {self.net_total}\n"
                    f"Grand: {old_gt} → {self.grand_total}"
                ),
            )

        super().db_update()

    def on_submit(self):
        """Safety net: fix values and force-write before GL entries."""
        old_gt = self.grand_total
        old_net = self.net_total

        fix_inclusive_tax_rounding(self)

        changed = self.grand_total != old_gt or self.net_total != old_net

        frappe.log_error(
            title="Tax Debug - on_submit ENTRY",
            message=(
                f"Net: {old_net} → {self.net_total} (changed={self.net_total != old_net})\n"
                f"Grand: {old_gt} → {self.grand_total} (changed={self.grand_total != old_gt})"
            ),
        )

        if changed:
            # Use frappe.db.sql for direct, uncacheable DB write
            frappe.db.sql("""
                UPDATE `tabSales Invoice`
                SET net_total=%s, base_net_total=%s,
                    grand_total=%s, base_grand_total=%s,
                    total_taxes_and_charges=%s, base_total_taxes_and_charges=%s,
                    rounded_total=%s, base_rounded_total=%s,
                    rounding_adjustment=%s, base_rounding_adjustment=%s
                WHERE name=%s
            """, (
                self.net_total, self.base_net_total,
                self.grand_total, self.base_grand_total,
                self.total_taxes_and_charges, self.base_total_taxes_and_charges,
                self.rounded_total, self.base_rounded_total,
                self.rounding_adjustment, self.base_rounding_adjustment,
                self.name,
            ))

            for row in self.items:
                frappe.db.sql("""
                    UPDATE `tabSales Invoice Item`
                    SET net_amount=%s, base_net_amount=%s,
                        net_rate=%s, base_net_rate=%s
                    WHERE name=%s
                """, (
                    row.net_amount, row.base_net_amount,
                    row.net_rate, row.base_net_rate,
                    row.name,
                ))

            for tax in self.taxes:
                frappe.db.sql("""
                    UPDATE `tabSales Taxes and Charges`
                    SET tax_amount=%s, base_tax_amount=%s,
                        tax_amount_after_discount_amount=%s,
                        base_tax_amount_after_discount_amount=%s,
                        total=%s, base_total=%s
                    WHERE name=%s
                """, (
                    tax.tax_amount, tax.base_tax_amount,
                    tax.tax_amount_after_discount_amount,
                    tax.base_tax_amount_after_discount_amount,
                    tax.total, tax.base_total,
                    tax.name,
                ))

        super().on_submit()

        # Log final state AFTER super().on_submit() completes
        frappe.log_error(
            title="Tax Debug - on_submit EXIT",
            message=(
                f"FINAL values after super().on_submit():\n"
                f"Net Total = {self.net_total}\n"
                f"Grand Total = {self.grand_total}\n"
                f"Total Taxes = {self.total_taxes_and_charges}"
            ),
        )

        # Check DB values to see if they match in-memory values
        db_vals = frappe.db.get_value(
            "Sales Invoice", self.name,
            ["net_total", "grand_total", "total_taxes_and_charges"],
            as_dict=True,
        )
        frappe.log_error(
            title="Tax Debug - DB check after submit",
            message=(
                f"DB values after submit:\n"
                f"Net Total = {db_vals.net_total}\n"
                f"Grand Total = {db_vals.grand_total}\n"
                f"Total Taxes = {db_vals.total_taxes_and_charges}\n"
                f"In-memory match: net={db_vals.net_total == self.net_total}, "
                f"grand={db_vals.grand_total == self.grand_total}"
            ),
        )
