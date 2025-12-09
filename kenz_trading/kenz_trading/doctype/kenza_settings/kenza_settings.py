# Copyright (c) 2025, TBO and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class KenzaSettings(Document):

	# def delete_task_recursively(task_name):
    # """Delete a task and all its child tasks"""
    # # Find child tasks
    # child_tasks = frappe.get_all("Task", filters={"parent_task": task_name}, pluck="name")
    # for child in child_tasks:
    #     delete_task_recursively(child)  # Recursively delete child tasks

    # # Delete this task
    # try:
    #     frappe.delete_doc("Task", task_name, force=1, ignore_permissions=True)
    # except Exception as e:
    #     frappe.log_error(f"Error deleting Task {task_name}: {e}")


	# @frappe.whitelist()
	# def delete_all_projects_and_tasks():
	# 	# Delete all Tasks (including nested)
	# 	tasks = frappe.get_all("Task", filters={"parent_task": ["is", "set"]}, pluck="name")  # top-level tasks
	# 	for t in tasks:
	# 		delete_task_recursively(t)

	# 	# Delete Projects
	# 	projects = frappe.get_all("Project", pluck="name")
	# 	for p in projects:
	# 		try:
	# 			frappe.delete_doc("Project", p, force=1, ignore_permissions=True)
	# 		except Exception as e:
	# 			frappe.log_error(f"Error deleting Project {p}: {e}")

	# 	frappe.db.commit()
	# 	return "Deleted all Tasks (including child tasks) and all Projects"
