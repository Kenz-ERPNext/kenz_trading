import frappe
from frappe.tests.utils import FrappeTestCase

from kenz_trading.events.sales_invoice import create_payment_entry_for_cash


def _invoice(**overrides):
	"""Minimal stand-in for a submitted Sales Invoice as seen by the on_submit hook."""
	doc = frappe._dict(
		name="SI-TEST-CASH-HOOK",
		company=None,
		customer=None,
		posting_date=None,
		debit_to=None,
		is_return=0,
		custom_payment_mode="Cash",
		custom_mode_of_payment=None,
		grand_total=100.0,
		rounded_total=100.0,
	)
	doc.update(overrides)
	return doc


class TestCreatePaymentEntryForCash(FrappeTestCase):
	def test_zatca_compliance_check_invoice_is_skipped(self):
		"""ksa_compliance submits throw-away invoices during its compliance check and
		rolls them back afterwards. Frappe defaults the Select field to its first option
		("Cash"), so the hook must not try to build a Payment Entry for them."""
		from ksa_compliance.standard_doctypes.sales_invoice import (
			clear_additional_fields_ignore_list,
			ignore_additional_fields_for_invoice,
		)

		ignore_additional_fields_for_invoice("SI-TEST-CASH-HOOK")
		try:
			# Must return silently: no validation error, no Payment Entry
			create_payment_entry_for_cash(_invoice(), "on_submit")
		finally:
			clear_additional_fields_ignore_list()

	def test_mode_of_payment_link_is_used_instead_of_select_label(self):
		"""custom_payment_mode is a Cash/Credit label; custom_mode_of_payment is the real
		Mode of Payment link. Sites name their Mode of Payment freely (e.g. "CASHBOOK
		KENZTECH"), so the hook must resolve the link, not look up a record named "Cash"."""
		mop = "Test Cashbox Hook"
		if not frappe.db.exists("Mode of Payment", mop):
			frappe.get_doc(
				{
					"doctype": "Mode of Payment",
					"mode_of_payment": mop,
					"type": "Cash",
					# mandatory when ksa_compliance is installed
					"custom_zatca_payment_means_code": "10",
				}
			).insert()

		# No Mode of Payment Account rows for this MoP -> the hook gets as far as the
		# account lookup and complains about *this* MoP, proving the link was used.
		with self.assertRaisesRegex(frappe.ValidationError, mop):
			create_payment_entry_for_cash(_invoice(custom_mode_of_payment=mop), "on_submit")
