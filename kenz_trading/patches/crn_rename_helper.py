import frappe


def rename_cr_no_to_crn_no(doctype):
    """Rename <doctype>.custom_cr_no to custom_crn_no, keeping the data.

    This runs in pre_model_sync, i.e. before the fixtures create custom_crn_no, so it can't
    use frappe's rename_field (that needs the new field to already be in the doctype meta and
    silently does nothing otherwise). It renames the Custom Field row and the DB column
    directly; the fixture sync afterwards just updates the already-renamed field.
    """
    old_name, new_name = f"{doctype}-custom_cr_no", f"{doctype}-custom_crn_no"
    table = f"tab{doctype}"

    if not frappe.db.exists("Custom Field", old_name):
        return

    if frappe.db.exists("Custom Field", new_name):
        # Both fields exist (new one was synced from fixtures first): copy the data across
        # where it's empty, then drop the old field.
        if frappe.db.has_column(doctype, "custom_cr_no") and frappe.db.has_column(doctype, "custom_crn_no"):
            frappe.db.sql(
                f"""update `{table}` set custom_crn_no = custom_cr_no
                where ifnull(custom_crn_no, '') = '' and ifnull(custom_cr_no, '') != ''"""
            )
        frappe.delete_doc("Custom Field", old_name, ignore_permissions=True, force=True)
    else:
        if frappe.db.has_column(doctype, "custom_cr_no") and not frappe.db.has_column(doctype, "custom_crn_no"):
            frappe.db.sql_ddl(f"alter table `{table}` change `custom_cr_no` `custom_crn_no` varchar(140)")
        frappe.db.sql(
            """update `tabCustom Field` set name=%s, fieldname='custom_crn_no', label='CRN No'
            where name=%s""",
            (new_name, old_name),
        )

    # property setters (quick entry flag, field order) that point at the old fieldname
    frappe.db.sql(
        """update `tabProperty Setter` set field_name='custom_crn_no',
        name=replace(name, 'custom_cr_no', 'custom_crn_no')
        where doc_type=%s and field_name='custom_cr_no'""",
        doctype,
    )
    frappe.db.sql(
        """update `tabProperty Setter` set value=replace(value, '"custom_cr_no"', '"custom_crn_no"')
        where doc_type=%s and property='field_order'""",
        doctype,
    )
    frappe.clear_cache(doctype=doctype)
