"""
Monkey-patches for ksa_compliance to fix ZATCA validation errors.

Fixes:
- BR-CO-14: Invoice total VAT amount (BT-110) must equal sum of VAT category tax amounts (BT-117)
- BR-CO-15: Invoice total amount with VAT (BT-112) must equal net total (BT-109) + VAT (BT-110)
- BR-KSA-F-04: All document amounts and quantities must be positive (zero AllowanceCharge)

These patches modify the Einvoice class method and the generate_xml_file function
at runtime so that ksa_compliance source files remain untouched.
"""

import re


_xml_patch_applied = False


def _apply_xml_post_processing():
    """Patch generate_xml_file in sales_invoice_additional_fields module
    to remove zero AllowanceTotalAmount from XML output (BR-KSA-F-04)."""
    global _xml_patch_applied
    if _xml_patch_applied:
        return

    try:
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
        _xml_patch_applied = True
    except (ImportError, AttributeError):
        pass


def apply_zatca_patches():
    """Apply monkey-patches to ksa_compliance Einvoice class for ZATCA validation fixes."""
    try:
        from ksa_compliance.output_models.e_invoice_output_model import Einvoice
    except ImportError:
        return

    if getattr(Einvoice, '_kenz_patched', False):
        return

    _original_get_details = Einvoice.get_e_invoice_details

    def patched_get_e_invoice_details(self, invoice_type):
        # Lazily apply XML post-processing patch.
        # By the time get_e_invoice_details runs, the sales_invoice_additional_fields
        # module is guaranteed to be imported, so patching its generate_xml_file works.
        _apply_xml_post_processing()

        # Call original method to populate self.result
        _original_get_details(self, invoice_type)

        invoice = self.result.get('invoice', {})

        # Fix BR-CO-14: Ensure total_taxes_and_charges (BT-110) equals
        # the sum of tax subtotal amounts (BT-117).
        # The original code uses abs(doc.total_taxes_and_charges) which may differ
        # from the sum of individual item tax amounts due to rounding.
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
    Einvoice._kenz_patched = True
