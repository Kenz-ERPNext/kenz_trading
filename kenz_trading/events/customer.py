import frappe
@frappe.whitelist()
def customer_auto_name(doc,method):
    last_code=frappe.db.sql("select custom_custome_code from `tabCustomer` ORDER BY custom_custome_code DESC Limit 1 ")
    if last_code and last_code[0][0]:
        new=int(last_code[0][0])+1
    else:
        new=1
    doc.custom_custome_code="{:02}".format(new)