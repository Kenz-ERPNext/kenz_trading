"""
Override for Sales Invoice Additional Fields to fix ZATCA validation errors.

Uses Frappe's override_doctype_class to reliably patch the ZATCA e-invoice
generation at exactly the right time.

Fixes:
- BR-S-08:   VAT category taxable amount (BT-116) must equal sum of line net amounts (BT-131)
- BR-CO-14:  Invoice total VAT amount (BT-110) must equal sum of VAT category tax amounts (BT-117)
- BR-CO-15:  Invoice total amount with VAT (BT-112) must equal net total (BT-109) + VAT (BT-110)
- BR-KSA-F-04: All document amounts and quantities must be positive (zero AllowanceCharge)
"""

import re

from frappe.utils import flt
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)

_patches_applied = False


def _ensure_patches_applied():
    """Apply monkey-patches to Einvoice class and generate_xml_file.
    Safe to call multiple times - only applies once."""
    global _patches_applied
    if _patches_applied:
        return

    # Patch 1: Fix Einvoice.get_e_invoice_details to correct tax totals and remove zero allowances
    from ksa_compliance.output_models.e_invoice_output_model import Einvoice

    _original_get_details = Einvoice.get_e_invoice_details

    def patched_get_e_invoice_details(self, invoice_type):
        _original_get_details(self, invoice_type)

        invoice = self.result.get('invoice', {})
        item_lines = invoice.get('item_lines', [])
        tax_total = invoice.get('tax_total', {})
        tax_subtotals = tax_total.get('tax_subtotal', []) if tax_total else []

        # === Fix BR-S-08 ===
        # ksa_compliance recalculates each line's pre-tax amount (BT-131) as
        #   flt(item.amount / (1 + tax_percent/100), 2)
        # but computes taxable_amount (BT-116) from ERPNext's item.net_amount.
        # Rounding differences between the two cause BR-S-08 to fail.
        # Fix: recompute each tax subtotal's taxable_amount from the sum of
        # line amounts (BT-131) grouped by tax rate.
        if item_lines and tax_subtotals:
            amounts_by_rate = {}
            for item in item_lines:
                rate = round(flt(item.get('tax_percent', 0)), 2)
                amounts_by_rate[rate] = flt(
                    amounts_by_rate.get(rate, 0) + flt(item.get('amount', 0)), 2
                )

            for subtotal in tax_subtotals:
                tax_cat = subtotal.get('tax_category', {})
                rate = round(flt(tax_cat.get('percent', 0)), 2)
                if rate in amounts_by_rate:
                    subtotal['taxable_amount'] = amounts_by_rate[rate]
                    subtotal['tax_amount'] = flt(
                        subtotal['taxable_amount'] * rate / 100, 2
                    )

            tax_total['tax_amount'] = flt(sum(
                flt(s.get('tax_amount', 0)) for s in tax_subtotals
            ), 2)
            tax_total['taxable_amount'] = flt(sum(
                flt(s.get('taxable_amount', 0)) for s in tax_subtotals
            ), 2)

        # === Fix BR-CO-14 ===
        # total_taxes_and_charges (BT-110) must equal sum of subtotal tax
        # amounts (BT-117). Use the (possibly corrected) tax_total value.
        if tax_total and 'tax_amount' in tax_total:
            invoice['total_taxes_and_charges'] = tax_total['tax_amount']
            # === Fix BR-CO-15 ===
            # grand_total (BT-112) = net_total (BT-109) + taxes (BT-110)
            invoice['grand_total'] = flt(
                invoice.get('net_total', 0) + invoice['total_taxes_and_charges'], 2
            )
            rounding_adjustment = invoice.get('rounding_adjustment', 0)
            invoice['payable_amount'] = flt(
                invoice['grand_total'] + rounding_adjustment, 2
            )

        # === Fix BR-KSA-F-04 ===
        # Remove zero-amount AllowanceCharge entries
        if 'allowance_charge' in invoice:
            invoice['allowance_charge'] = [
                ac for ac in invoice['allowance_charge']
                if ac.get('amount') and float(ac.get('amount', 0)) > 0
            ]

    Einvoice.get_e_invoice_details = patched_get_e_invoice_details

    # Patch 2: Post-process XML to remove zero AllowanceTotalAmount
    import ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields as siaf_module

    _original_generate_xml = siaf_module.generate_xml_file

    def patched_generate_xml_file(data):
        xml_string = _original_generate_xml(data)
        # Remove zero AllowanceTotalAmount element (BR-KSA-F-04)
        xml_string = re.sub(
            r'\s*<cbc:AllowanceTotalAmount[^>]*>0(?:\.0+)?</cbc:AllowanceTotalAmount>',
            '',
            xml_string,
        )
        return xml_string

    siaf_module.generate_xml_file = patched_generate_xml_file

    _patches_applied = True


class CustomSalesInvoiceAdditionalFields(SalesInvoiceAdditionalFields):
    """Override that applies ZATCA fixes before invoice processing."""

    def _prepare_for_zatca(self, settings, invoice_type):
        _ensure_patches_applied()
        return super()._prepare_for_zatca(settings, invoice_type)
