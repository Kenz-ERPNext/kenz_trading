"""
Override for Sales Invoice Additional Fields to fix ZATCA validation errors.

Uses Frappe's override_doctype_class to reliably patch the ZATCA e-invoice
generation at exactly the right time.

Fixes:
- BR-CO-14: Invoice total VAT amount (BT-110) must equal sum of VAT category tax amounts (BT-117)
- BR-CO-15: Invoice total amount with VAT (BT-112) must equal net total (BT-109) + VAT (BT-110)
- BR-KSA-F-04: All document amounts and quantities must be positive (zero AllowanceCharge)
"""

import re

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

        # Fix BR-CO-14: Use item-level tax sum as total_taxes_and_charges
        # so BT-110 exactly equals sum of BT-117
        tax_total = invoice.get('tax_total', {})
        if tax_total and 'tax_amount' in tax_total:
            invoice['total_taxes_and_charges'] = tax_total['tax_amount']
            # Fix BR-CO-15: Recalculate grand_total = net_total + total_taxes_and_charges
            invoice['grand_total'] = (
                invoice.get('net_total', 0) + invoice['total_taxes_and_charges']
            )
            rounding_adjustment = invoice.get('rounding_adjustment', 0)
            invoice['payable_amount'] = invoice['grand_total'] + rounding_adjustment

        # Fix BR-KSA-F-04: Remove zero-amount AllowanceCharge entries
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
