from kenz_trading.patches.crn_rename_helper import rename_cr_no_to_crn_no


def execute():
    """Customer.custom_cr_no was renamed to custom_crn_no so it matches the field name pos_api
    looks for."""
    rename_cr_no_to_crn_no("Customer")
