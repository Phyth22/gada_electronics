# Copyright (c) 2025, Agatha and contributors
# For license information, please see license.txt

# import frappe


# def execute(filters=None):
# 	columns, data = [], []
# 	return columns, data

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    # Use today's date if no date provided
    filters.setdefault("to_date", frappe.utils.nowdate())

    # Get GL Entry totals grouped by account
    results = frappe.db.sql("""
        SELECT
            account,
            SUM(debit_amount) - SUM(credit_amount) as balance
        FROM `tabGL Entry`
        WHERE posting_date <= %(to_date)s AND is_cancelled = 0
        GROUP BY account
    """, filters, as_dict=True)

    # Filter only Asset and Liability accounts
    data = []
    for row in results:
        acc_type = frappe.get_value("Account", row.account, "account_type")
        if acc_type in ["Asset", "Liability"]:
            row["account_type"] = acc_type
            data.append(row)

    columns = [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account"},
        {"label": _("Account Type"), "fieldname": "account_type", "fieldtype": "Data"},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency"},
    ]

    return columns, data
