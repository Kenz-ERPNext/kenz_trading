import frappe
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from kenz_trading.events.sales_invoice import fix_inclusive_tax_rounding

import traceback


class CustomSalesInvoice(SalesInvoice):
    def calculate_taxes_and_totals(self):
        """Override to fix inclusive tax rounding immediately after every
        ERPNext tax calculation.  This ensures no downstream code ever
        sees the unfixed values, regardless of how many times
        calculate_taxes_and_totals() is called during the save/submit
        lifecycle."""
        super().calculate_taxes_and_totals()

        old_net = self.net_total
        old_gt = self.grand_total
        fix_inclusive_tax_rounding(self)

        if self.net_total != old_net or self.grand_total != old_gt:
            caller = "".join(traceback.format_stack()[-3:-1])
            frappe.log_error(
                title="Tax Rounding Fix - calculate_taxes_and_totals",
                message=(
                    f"Fix applied in calculate_taxes_and_totals:\n"
                    f"Net: {old_net} → {self.net_total}\n"
                    f"Grand: {old_gt} → {self.grand_total}\n"
                    f"Caller:\n{caller}"
                ),
            )

    def validate(self):
        super().validate()
        frappe.log_error(
            title="Tax Rounding Debug - after validate",
            message=(
                f"After validate():\n"
                f"Net Total = {self.net_total}\n"
                f"Grand Total = {self.grand_total}\n"
                f"Total Taxes = {self.total_taxes_and_charges}\n"
                f"Class = {type(self).__name__}\n"
                f"MRO = {[c.__name__ for c in type(self).__mro__[:5]]}"
            ),
        )

    def on_submit(self):
        """Safety net: if values are still wrong by on_submit (e.g. an
        external hook recalculated without going through our override),
        fix them and force-write to the database before GL entries are
        created."""
        old_gt = self.grand_total
        old_net = self.net_total

        fix_inclusive_tax_rounding(self)

        changed = self.grand_total != old_gt or self.net_total != old_net

        frappe.log_error(
            title="Tax Rounding Debug - on_submit",
            message=(
                f"on_submit safety net:\n"
                f"Net: {old_net} → {self.net_total} (changed={self.net_total != old_net})\n"
                f"Grand: {old_gt} → {self.grand_total} (changed={self.grand_total != old_gt})\n"
                f"Will db_update: {changed}"
            ),
        )

        if changed:
            self.db_update()
            for row in self.items:
                row.db_update()
            for tax in self.taxes:
                tax.db_update()

        super().on_submit()
