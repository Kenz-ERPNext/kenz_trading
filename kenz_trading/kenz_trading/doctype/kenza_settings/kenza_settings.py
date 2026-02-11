# Copyright (c) 2025, TBO and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class KenzaSettings(Document):
	# pass 

 
	@frappe.whitelist()
	def create_tc(self):
		"""Create Tax Category"""
		# Check if already exists
		existing = frappe.db.exists("Tax Category", {"title": "VAT 15%"})
		if existing:
			self.tax_category = existing
			self.save()
			return existing

		tc = frappe.new_doc("Tax Category")
		tc.title = "VAT 15%"
		tc.custom_zatca_category = "Standard rate"
		tc.insert()
		frappe.db.commit()

		self.tax_category = tc.name
		self.save()
		return tc.name

	@frappe.whitelist()
	def create_ah(self):
		"""Create Account Head"""
		# Check if already exists
		existing = frappe.db.exists("Account", {"account_name": "VAT 15%"})
		if existing:
			self.account = existing
			self.save()
			return existing

		ah = frappe.new_doc("Account")
		ah.account_name = "VAT 15%"
		ah.parent_account = self.parent_account
		ah.account_type = "Tax"
		ah.tax_rate = 15.0
		ah.insert()
		frappe.db.commit()

		self.account = ah.name
		self.save()
		return ah.name

	@frappe.whitelist()
	def create_tt(self):
		"""Create Sales Taxes and Charges Template"""
		# Check if already exists
		existing = frappe.db.exists("Sales Taxes and Charges Template", {"title": "VAT 15%"})
		if existing:
			self.sales_taxes_and_charges_template = existing
			self.save()
			return existing

		tt = frappe.new_doc("Sales Taxes and Charges Template")
		tt.title = "VAT 15%"
		tt.tax_category = self.tax_category

		# Append tax details
		tt.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": self.account,
			"description": "VAT 15%",
			"rate": 15.0
		})

		tt.insert()
		frappe.db.commit()

		self.sales_taxes_and_charges_template = tt.name
		self.save()
		return tt.name




