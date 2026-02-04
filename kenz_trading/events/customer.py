# import frappe
# @frappe.whitelist()


# def customer_auto_name(doc,method):
#     last_code=frappe.db.sql("select custom_custome_code from `tabCustomer` ORDER BY custom_custome_code DESC Limit 1 ")
#     if last_code and last_code[0][0]:
#         new=int(last_code[0][0])+1
#     else:
#         new=1
#     doc.custom_custome_code="{:02}".format(new)






# ISSUE FIX CODE BELOW ///////////

# import frappe
# import re

# def customer_auto_name(doc, method):
#     last_code = frappe.db.sql(
#         """
#         SELECT custom_custome_code
#         FROM `tabCustomer`
#         WHERE custom_custome_code IS NOT NULL
#         ORDER BY creation DESC
#         LIMIT 1
#         """,
#         as_list=True
#     )

#     if last_code and last_code[0][0]:
#         # Extract numbers from the code (e.g. S31 → 31)
#         match = re.search(r"\d+", last_code[0][0])
#         last_number = int(match.group()) if match else 0
#         new_number = last_number + 1
#     else:
#         new_number = 1

#     doc.custom_custome_code = f"S{new_number:02d}"
