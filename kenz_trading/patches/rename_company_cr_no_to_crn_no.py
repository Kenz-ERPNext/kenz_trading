from kenz_trading.patches.crn_rename_helper import rename_cr_no_to_crn_no


def execute():
    """Company.custom_cr_no was renamed to custom_crn_no (same name as Customer)."""
    rename_cr_no_to_crn_no("Company")
