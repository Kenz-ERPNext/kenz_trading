from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from kenz_trading.events.sales_invoice import fix_inclusive_tax_rounding


class CustomPurchaseInvoice(PurchaseInvoice):
    def calculate_taxes_and_totals(self):
        """Override to fix inclusive tax rounding immediately after every
        ERPNext tax calculation."""
        super().calculate_taxes_and_totals()
        fix_inclusive_tax_rounding(self)

    def db_update(self):
        """Apply fix right before every DB write of the parent document."""
        fix_inclusive_tax_rounding(self)
        super().db_update()
