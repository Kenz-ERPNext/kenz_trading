import frappe
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from kenz_trading.events.sales_invoice import fix_inclusive_tax_rounding


class CustomSalesInvoice(SalesInvoice):
    def calculate_taxes_and_totals(self):
        """Override to fix inclusive tax rounding immediately after every
        ERPNext tax calculation.  This ensures no downstream code ever
        sees the unfixed values, regardless of how many times
        calculate_taxes_and_totals() is called during the save/submit
        lifecycle."""
        super().calculate_taxes_and_totals()
        fix_inclusive_tax_rounding(self)

    def on_submit(self):
        """Safety net: if values are still wrong by on_submit (e.g. an
        external hook recalculated without going through our override),
        fix them and force-write to the database before GL entries are
        created."""
        old_gt = self.grand_total
        old_net = self.net_total

        fix_inclusive_tax_rounding(self)

        if self.grand_total != old_gt or self.net_total != old_net:
            self.db_update()
            for row in self.items:
                row.db_update()
            for tax in self.taxes:
                tax.db_update()

        super().on_submit()
