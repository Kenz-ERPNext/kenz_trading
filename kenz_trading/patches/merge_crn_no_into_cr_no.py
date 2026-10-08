import frappe


def execute():
    """custom_crn_no was renamed back to custom_cr_no. Sites that already ran the old
    cr_no -> crn_no rename now have custom_crn_no (holding the data), and some also got a
    fresh custom_cr_no from the fixtures, so both show up on the form. Keep only custom_cr_no."""
    for doctype in ("Customer", "Company"):
        merge_crn_no_into_cr_no(doctype)


def merge_crn_no_into_cr_no(doctype):
    old_name, new_name = f"{doctype}-custom_crn_no", f"{doctype}-custom_cr_no"
    table = f"tab{doctype}"

    if not frappe.db.exists("Custom Field", old_name):
        return

    if frappe.db.exists("Custom Field", new_name):
        # Both fields exist: copy the data across where it's empty, then drop the old field.
        if frappe.db.has_column(doctype, "custom_crn_no") and frappe.db.has_column(doctype, "custom_cr_no"):
            frappe.db.sql(
                f"""update `{table}` set custom_cr_no = custom_crn_no
                where ifnull(custom_cr_no, '') = '' and ifnull(custom_crn_no, '') != ''"""
            )
        frappe.delete_doc("Custom Field", old_name, ignore_permissions=True, force=True)
    else:
        if frappe.db.has_column(doctype, "custom_crn_no") and not frappe.db.has_column(doctype, "custom_cr_no"):
            frappe.db.sql_ddl(f"alter table `{table}` change `custom_crn_no` `custom_cr_no` varchar(140)")
        frappe.db.sql(
            """update `tabCustom Field` set name=%s, fieldname='custom_cr_no', label='CR No'
            where name=%s""",
            (new_name, old_name),
        )

    # property setters (e.g. the quick entry flag) that point at the old fieldname: rename them,
    # or drop them if the new one already exists (name is the primary key)
    for ps in frappe.get_all(
        "Property Setter", filters={"doc_type": doctype, "field_name": "custom_crn_no"}, pluck="name"
    ):
        new_ps = ps.replace("custom_crn_no", "custom_cr_no")
        if frappe.db.exists("Property Setter", new_ps):
            frappe.db.delete("Property Setter", {"name": ps})
        else:
            frappe.db.sql(
                "update `tabProperty Setter` set name=%s, field_name='custom_cr_no' where name=%s",
                (new_ps, ps),
            )
    frappe.db.sql(
        """update `tabProperty Setter` set value=replace(value, '"custom_crn_no"', '"custom_cr_no"')
        where doc_type=%s and property='field_order'""",
        doctype,
    )
    frappe.clear_cache(doctype=doctype)
