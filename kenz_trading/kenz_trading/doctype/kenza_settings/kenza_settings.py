# Copyright (c) 2025, TBO and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class KenzaSettings(Document):

	@frappe.whitelist()
	def delete_all_projects_and_tasks(self):
		# Delete Tasks first
		tasks = frappe.get_all("Task", pluck="name")
		for t in tasks:
			try:
				frappe.delete_doc("Task", t, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error deleting Task {t}: {e}")

		# Delete Projects
		projects = frappe.get_all("Project", pluck="name")
		for p in projects:
			try:
				frappe.delete_doc("Project", p, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error deleting Project {p}: {e}")

		frappe.db.commit()

		return f"Deleted {len(tasks)} Tasks and {len(projects)} Projects"
