"""
Override for Sales Invoice Additional Fields to fix ZATCA validation errors.

Uses Frappe's override_doctype_class to reliably patch the ZATCA e-invoice
generation at exactly the right time.

Fixes:
- BR-CO-11:  Sum of allowances on document level (BT-107) = Σ Document level allowance amount (BT-92)
- BR-S-08:   VAT category taxable amount (BT-116) must equal Σ BT-131 - Σ BT-92 + Σ BT-99
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

    # Patch 1: Fix Einvoice.get_e_invoice_details to correct tax totals and allowances
    from ksa_compliance.output_models.e_invoice_output_model import Einvoice

    _original_get_details = Einvoice.get_e_invoice_details

    def patched_get_e_invoice_details(self, invoice_type):
        _original_get_details(self, invoice_type)

        invoice = self.result.get('invoice', {})
        item_lines = invoice.get('item_lines', [])
        tax_total = invoice.get('tax_total', {})
        tax_subtotals = tax_total.get('tax_subtotal', []) if tax_total else []
        allowance_charges = invoice.get('allowance_charge', [])

        # === Fix BR-KSA-F-04 ===
        # Remove zero-amount AllowanceCharge entries
        if allowance_charges:
            invoice['allowance_charge'] = [
                ac for ac in allowance_charges
                if ac.get('amount') and float(ac.get('amount', 0)) > 0
            ]
            allowance_charges = invoice['allowance_charge']

        # === Fix BR-CO-11 ===
        # AllowanceTotalAmount (BT-107) must equal Σ AllowanceCharge amounts (BT-92).
        # ksa_compliance's compute_invoice_discount_amount() calculates BT-107 from
        # the grand total discount, while BT-92 comes from per-item (amount - net_amount).
        # Rounding differences between the two approaches cause BR-CO-11 to fail.
        # Fix: set BT-107 = Σ BT-92 so they always match.
        total_allowance = flt(sum(
            flt(ac.get('amount', 0)) for ac in allowance_charges
        ), 2)
        invoice['allowance_total_amount'] = total_allowance

        # === Fix BR-S-08 ===
        # BT-116 = Σ BT-131 (line amounts) - Σ BT-92 (allowances) + Σ BT-99 (charges)
        # per tax category. The original code set taxable_amount from ERPNext's
        # item.net_amount which doesn't account for BT-131 rounding.
        # Fix: recompute from line amounts minus allowances per tax rate.
        if item_lines and tax_subtotals:
            amounts_by_rate = {}
            for item in item_lines:
                rate = round(flt(item.get('tax_percent', 0)), 2)
                amounts_by_rate[rate] = flt(
                    amounts_by_rate.get(rate, 0) + flt(item.get('amount', 0)), 2
                )

            allowances_by_rate = {}
            for ac in allowance_charges:
                tax_cat = ac.get('tax_category', {})
                rate = round(flt(tax_cat.get('percent', 0)), 2)
                allowances_by_rate[rate] = flt(
                    allowances_by_rate.get(rate, 0) + flt(ac.get('amount', 0)), 2
                )

            for subtotal in tax_subtotals:
                tax_cat = subtotal.get('tax_category', {})
                rate = round(flt(tax_cat.get('percent', 0)), 2)
                line_amount = amounts_by_rate.get(rate, 0)
                allowance_amount = allowances_by_rate.get(rate, 0)
                subtotal['taxable_amount'] = flt(line_amount - allowance_amount, 2)
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
        # total_taxes_and_charges (BT-110) must equal sum of subtotal tax amounts (BT-117).
        if tax_total and 'tax_amount' in tax_total:
            invoice['total_taxes_and_charges'] = tax_total['tax_amount']

        # === Fix BR-CO-15 / BR-CO-13 ===
        # net_total (BT-109) = line_extension_amount - allowances + charges
        # grand_total (BT-112) = net_total + taxes
        line_ext = flt(invoice.get('line_extension_amount', 0), 2)
        invoice['net_total'] = flt(line_ext - total_allowance, 2)
        invoice['grand_total'] = flt(
            invoice['net_total'] + flt(invoice.get('total_taxes_and_charges', 0)), 2
        )
        rounding_adjustment = invoice.get('rounding_adjustment', 0)
        invoice['payable_amount'] = flt(
            invoice['grand_total'] + rounding_adjustment, 2
        )

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
