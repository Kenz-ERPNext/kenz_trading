import frappe
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from kenz_trading.events.sales_invoice import fix_inclusive_tax_rounding


class CustomSalesInvoice(SalesInvoice):
    def validate(self):
        super().validate()
        fix_inclusive_tax_rounding(self)

    def before_submit(self):
        super().before_submit()
        fix_inclusive_tax_rounding(self)

    def on_submit(self):
        # Snapshot before fix
        old_gt = self.grand_total
        old_net = self.net_total

        # Apply fix BEFORE parent on_submit (which makes GL entries)
        fix_inclusive_tax_rounding(self)

        # If values changed, force-write to DB so GL entries use correct amounts
        if self.grand_total != old_gt or self.net_total != old_net:
            self.db_update()
            for row in self.items:
                row.db_update()
            for tax in self.taxes:
                tax.db_update()

            frappe.msgprint(
                f"Tax rounding fix applied: Net {old_net} → {self.net_total}, "
                f"Grand {old_gt} → {self.grand_total}",
                indicator="blue",
            )

        super().on_submit()
