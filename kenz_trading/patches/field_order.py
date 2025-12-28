# import frappe
# import json

# def execute():
#     doctype = "Purchase Invoice"
#     property_name = "field_order"
#     module_name = "Kenz Trading"  # ✅ Module must be set
#     value = [
#         "custom_new", "custom_test", "supplier", "supplier_name", "custom_a", "posting_date",
#         "due_date", "custom_b", "is_paid", "is_return", "sec_warehouse", "scan_barcode",
#         "last_scanned_warehouse", "col_break_warehouse", "update_stock", "set_warehouse",
#         "set_from_warehouse", "is_subcontracted", "rejected_warehouse", "supplier_warehouse",
#         "items_section", "items", "totals", "custom_test_totals", "total_qty",
#         "total_taxes_and_charges", "taxes_and_charges", "in_words", "column_break_40",
#         "total", "net_total", "grand_total", "rounding_adjustment", "rounded_total",
#         "total_advance", "outstanding_amount", "section_break_44", "apply_discount_on",
#         "base_discount_amount", "column_break_46", "additional_discount_percentage",
#         "discount_amount", "custom_sub_details", "title", "naming_series", "tax_id",
#         "company", "column_break_6", "posting_time", "set_posting_time", "column_break1",
#         "return_against", "update_outstanding_for_self", "update_billed_amount_in_purchase_order",
#         "update_billed_amount_in_purchase_receipt", "apply_tds", "tax_withholding_category",
#         "amended_from", "accounting_dimensions_section", "color", "cost_center", "dimension_col_break",
#         "branch", "project", "supplier_invoice_details", "bill_no", "column_break_15", "bill_date",
#         "currency_and_price_list", "currency", "conversion_rate", "use_transaction_date_exchange_rate",
#         "column_break2", "buying_price_list", "price_list_currency", "plc_conversion_rate",
#         "ignore_pricing_rule", "section_break_26", "total_net_weight", "base_taxes_and_charges_added",
#         "base_total_taxes_and_charges", "base_taxes_and_charges_deducted", "column_break_50",
#         "base_total", "base_net_total", "column_break_28", "base_tax_withholding_net_total",
#         "tax_withholding_net_total", "taxes_and_charges_added", "taxes_and_charges_deducted",
#         "taxes_section", "tax_category", "column_break_58", "shipping_rule", "column_break_49",
#         "incoterm", "named_place", "section_break_49", "base_grand_total", "base_rounding_adjustment",
#         "base_rounded_total", "base_in_words", "column_break8", "use_company_roundoff_cost_center",
#         "disable_rounded_total", "section_break_51", "taxes", "tax_withheld_vouchers_section",
#         "tax_withheld_vouchers", "sec_tax_breakup", "other_charges_calculation",
#         "pricing_rule_details", "pricing_rules", "raw_materials_supplied", "supplied_items",
#         "payments_tab", "payments_section", "mode_of_payment", "base_paid_amount", "clearance_date",
#         "col_br_payments", "cash_bank_account", "paid_amount", "advances_section",
#         "allocate_advances_automatically", "only_include_allocated_payments", "get_advances",
#         "advances", "advance_tax", "write_off", "write_off_amount", "base_write_off_amount",
#         "column_break_61", "write_off_account", "write_off_cost_center", "address_and_contact_tab",
#         "section_addresses", "supplier_address", "address_display", "col_break_address",
#         "contact_person", "contact_display", "contact_mobile", "contact_email",
#         "company_shipping_address_section", "dispatch_address", "dispatch_address_display",
#         "column_break_126", "shipping_address", "shipping_address_display",
#         "company_billing_address_section", "billing_address", "column_break_130",
#         "billing_address_display", "terms_tab", "payment_schedule_section",
#         "payment_terms_template", "ignore_default_payment_terms_template", "payment_schedule",
#         "terms_section_break", "tc_name", "terms", "more_info_tab", "status_section",
#         "status", "column_break_177", "per_received", "accounting_details_section", "credit_to",
#         "party_account_currency", "is_opening", "against_expense_account", "column_break_63",
#         "unrealized_profit_loss_account", "subscription_section", "subscription", "auto_repeat",
#         "update_auto_repeat_reference", "column_break_114", "from_date", "to_date",
#         "printing_settings", "letter_head", "group_same_items", "column_break_112",
#         "select_print_heading", "language", "sb_14", "on_hold", "release_date", "cb_17",
#         "hold_comment", "additional_info_section", "is_internal_supplier", "represents_company",
#         "supplier_group", "column_break_147", "inter_company_invoice_reference",
#         "is_old_subcontracting_flow", "remarks", "connections_tab"
#     ]

#     value_json = json.dumps(value, indent=4)

#     ps = frappe.get_all("Property Setter",
#         filters={
#             "doctype_or_field": "DocType",
#             "doc_type": doctype,
#             "property": property_name
#         },
#         limit=1
#     )

#     if ps:
#         doc = frappe.get_doc("Property Setter", ps[0].name)
#         doc.value = value_json
#         doc.module = module_name  # ✅ Set module in case missing
#         doc.save()
#         frappe.db.commit()
#         print(f"Updated Property Setter: {doc.name}")
#     else:
#         doc = frappe.get_doc({
#             "doctype": "Property Setter",
#             "doctype_or_field": "DocType",
#             "doc_type": doctype,
#             "property": property_name,
#             "property_type": "Data",
#             "value": value_json,
#             "module": module_name,
#             "is_system_generated": 0
#         })
#         doc.insert(ignore_permissions=True)
#         frappe.db.commit()
#         print(f"Created Property Setter: {doc.name}")



import frappe
import json

def execute():
    property_setters = [
        {
            "doctype": "Purchase Invoice",
            "module": "Kenz Trading",
            "value": [
                "custom_new", "custom_test", "supplier", "supplier_name", "custom_a", "posting_date",
                "due_date", "custom_b", "is_paid", "is_return", "sec_warehouse", "scan_barcode",
                "last_scanned_warehouse", "col_break_warehouse", "update_stock", "set_warehouse",
                "set_from_warehouse", "is_subcontracted", "rejected_warehouse", "supplier_warehouse",
                "items_section", "items", "totals", "custom_test_totals", "total_qty",
                "total_taxes_and_charges", "taxes_and_charges", "in_words", "column_break_40",
                "total", "net_total", "grand_total", "rounding_adjustment", "rounded_total",
                "total_advance", "outstanding_amount", "section_break_44", "apply_discount_on",
                "base_discount_amount", "column_break_46", "additional_discount_percentage",
                "discount_amount", "custom_sub_details", "title", "naming_series", "tax_id",
                "company", "column_break_6", "posting_time", "set_posting_time", "column_break1",
                "return_against", "update_outstanding_for_self", "update_billed_amount_in_purchase_order",
                "update_billed_amount_in_purchase_receipt", "apply_tds", "tax_withholding_category",
                "amended_from", "accounting_dimensions_section", "color", "cost_center", "dimension_col_break",
                "branch", "project", "supplier_invoice_details", "bill_no", "column_break_15", "bill_date",
                "currency_and_price_list", "currency", "conversion_rate", "use_transaction_date_exchange_rate",
                "column_break2", "buying_price_list", "price_list_currency", "plc_conversion_rate",
                "ignore_pricing_rule", "section_break_26", "total_net_weight", "base_taxes_and_charges_added",
                "base_total_taxes_and_charges", "base_taxes_and_charges_deducted", "column_break_50",
                "base_total", "base_net_total", "column_break_28", "base_tax_withholding_net_total",
                "tax_withholding_net_total", "taxes_and_charges_added", "taxes_and_charges_deducted",
                "taxes_section", "tax_category", "column_break_58", "shipping_rule", "column_break_49",
                "incoterm", "named_place", "section_break_49", "base_grand_total", "base_rounding_adjustment",
                "base_rounded_total", "base_in_words", "column_break8", "use_company_roundoff_cost_center",
                "disable_rounded_total", "section_break_51", "taxes", "tax_withheld_vouchers_section",
                "tax_withheld_vouchers", "sec_tax_breakup", "other_charges_calculation",
                "pricing_rule_details", "pricing_rules", "raw_materials_supplied", "supplied_items",
                "payments_tab", "payments_section", "mode_of_payment", "base_paid_amount", "clearance_date",
                "col_br_payments", "cash_bank_account", "paid_amount", "advances_section",
                "allocate_advances_automatically", "only_include_allocated_payments", "get_advances",
                "advances", "advance_tax", "write_off", "write_off_amount", "base_write_off_amount",
                "column_break_61", "write_off_account", "write_off_cost_center", "address_and_contact_tab",
                "section_addresses", "supplier_address", "address_display", "col_break_address",
                "contact_person", "contact_display", "contact_mobile", "contact_email",
                "company_shipping_address_section", "dispatch_address", "dispatch_address_display",
                "column_break_126", "shipping_address", "shipping_address_display",
                "company_billing_address_section", "billing_address", "column_break_130",
                "billing_address_display", "terms_tab", "payment_schedule_section",
                "payment_terms_template", "ignore_default_payment_terms_template", "payment_schedule",
                "terms_section_break", "tc_name", "terms", "more_info_tab", "status_section",
                "status", "column_break_177", "per_received", "accounting_details_section", "credit_to",
                "party_account_currency", "is_opening", "against_expense_account", "column_break_63",
                "unrealized_profit_loss_account", "subscription_section", "subscription", "auto_repeat",
                "update_auto_repeat_reference", "column_break_114", "from_date", "to_date",
                "printing_settings", "letter_head", "group_same_items", "column_break_112",
                "select_print_heading", "language", "sb_14", "on_hold", "release_date", "cb_17",
                "hold_comment", "additional_info_section", "is_internal_supplier", "represents_company",
                "supplier_group", "column_break_147", "inter_company_invoice_reference",
                "is_old_subcontracting_flow", "remarks", "connections_tab"
            ]
        },
        {
            "doctype": "Sales Invoice",
            "module": "Kenz Trading",
            "value": [
                "custom_test", "customer", "customer_name", "customer_name_in_arabic", "custom_a",
                "posting_date", "due_date", "custom_b", "custom_po_no", "is_return", "custom_payment_mode",
                "custom_mode_of_payment", "custom_cheque_number", "custom_cheque_date",
                "custom_additional_information", "custom_attention", "custom_bank_details",
                "custom_due_date", "custom_a1", "custom_payment_term", "custom_location",
                "custom_delivery_note_no", "custom_reference_number", "items_section", "scan_barcode",
                "update_stock", "last_scanned_warehouse", "column_break_39", "set_warehouse",
                "set_target_warehouse", "custom_section_break_kzlxf", "custom_stock_details",
                "section_break_42", "items", "custom_five_transaction", "custom_last_five_transaction_details",
                "custom_total", "custom_total_test", "total_qty", "total_advance", "taxes_and_charges",
                "custom_c", "total", "net_total", "total_taxes_and_charges", "grand_total",
                "section_break_49", "apply_discount_on", "base_discount_amount",
                "is_cash_or_non_trade_discount", "additional_discount_account", "column_break_51",
                "additional_discount_percentage", "discount_amount", "custom_zatca_discount_reason",
                "pricing_rule_details", "pricing_rules", "packing_list", "packed_items",
                "product_bundle_help", "section_break_104", "total_billing_hours", "column_break_106",
                "total_billing_amount", "custom_sub_details", "customer_section", "title",
                "naming_series", "tax_id", "company", "company_tax_id", "ksa_einv_qr", "custom_cno",
                "column_break1", "posting_time", "set_posting_time", "custom_session_user",
                "column_break_14", "is_pos", "pos_profile", "is_consolidated", "return_against",
                "custom_return_against_additional_references", "update_outstanding_for_self",
                "update_billed_amount_in_sales_order", "update_billed_amount_in_delivery_note",
                "is_debit_note", "custom_return_reason", "amended_from", "accounting_dimensions_section",
                "color", "cost_center", "dimension_col_break", "branch", "project",
                "currency_and_price_list", "currency", "conversion_rate", "column_break2",
                "selling_price_list", "price_list_currency", "plc_conversion_rate", "ignore_pricing_rule",
                "section_break_43", "base_total_taxes_and_charges", "base_in_words", "column_break_47",
                "rounded_total", "outstanding_amount", "section_break_40", "taxes", "totals",
                "base_grand_total", "base_rounding_adjustment", "base_rounded_total", "column_break5",
                "rounding_adjustment", "use_company_roundoff_cost_center", "in_words",
                "disable_rounded_total", "section_break_30", "total_net_weight", "column_break_32",
                "base_total", "base_net_total", "column_break_52", "taxes_section", "tax_category",
                "column_break_38", "shipping_rule", "column_break_55", "incoterm", "named_place",
                "sec_tax_breakup", "other_charges_calculation", "time_sheet_list", "timesheets",
                "payments_tab", "payments_section", "cash_bank_account", "payments", "section_break_84",
                "base_paid_amount", "column_break_86", "paid_amount", "section_break_88",
                "base_change_amount", "column_break_90", "change_amount", "account_for_change_amount",
                "advances_section", "allocate_advances_automatically", "only_include_allocated_payments",
                "get_advances", "advances", "write_off_section", "write_off_amount", "base_write_off_amount",
                "write_off_outstanding_amount_automatically", "column_break_74", "write_off_account",
                "write_off_cost_center", "loyalty_points_redemption", "redeem_loyalty_points",
                "loyalty_points", "loyalty_amount", "column_break_77", "loyalty_program",
                "loyalty_redemption_account", "loyalty_redemption_cost_center", "contact_and_address_tab",
                "address_and_contact", "customer_address", "address_display", "col_break4",
                "contact_person", "contact_display", "contact_mobile", "contact_email", "territory",
                "shipping_address_section", "shipping_address_name", "shipping_address",
                "shipping_addr_col_break", "dispatch_address_name", "dispatch_address",
                "company_address_section", "company_address", "company_trn", "company_address_display",
                "company_addr_col_break", "company_contact_person", "terms_tab",
                "payment_schedule_section", "ignore_default_payment_terms_template", "payment_terms_template",
                "payment_schedule", "terms_section_break", "tc_name", "terms", "more_info_tab",
                "customer_po_details", "po_no", "column_break_23", "po_date", "more_info", "debit_to",
                "party_account_currency", "is_opening", "column_break8", "unrealized_profit_loss_account",
                "against_income_account", "sales_team_section_break", "sales_partner",
                "amount_eligible_for_commission", "column_break10", "commission_rate", "total_commission",
                "section_break2", "sales_team", "edit_printing_settings", "letter_head",
                "group_same_items", "column_break_84", "select_print_heading", "language",
                "subscription_section", "subscription", "from_date", "auto_repeat", "column_break_140",
                "to_date", "update_auto_repeat_reference", "more_information", "status",
                "inter_company_invoice_reference", "campaign", "represents_company", "source",
                "customer_group", "col_break23", "is_internal_customer", "is_discounted", "remarks",
                "connections_tab"
            ]
        }
    ]

    for ps_def in property_setters:
        doctype = ps_def["doctype"]
        module = ps_def["module"]
        value_json = json.dumps(ps_def["value"], indent=4)

        existing = frappe.get_all("Property Setter",
            filters={
                "doctype_or_field": "DocType",
                "doc_type": doctype,
                "property": "field_order"
            },
            limit=1
        )

        if existing:
            doc = frappe.get_doc("Property Setter", existing[0].name)
            doc.value = value_json
            doc.module = module
            doc.save()
            frappe.db.commit()
            print(f"Updated Property Setter: {doc.name}")
        else:
            doc = frappe.get_doc({
                "doctype": "Property Setter",
                "doctype_or_field": "DocType",
                "doc_type": doctype,
                "property": "field_order",
                "property_type": "Data",
                "value": value_json,
                "module": module,
                "is_system_generated": 0
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Created Property Setter: {doc.name}")
