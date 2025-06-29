# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate

def execute(filters=None):
    """Main function that returns columns and data for the report"""
    if not filters:
        filters = {}
    
    # Validate filters
    validate_filters(filters)
    
    # Get columns for the report
    columns = get_columns(filters)
    
    # Get data for the report
    data = get_data(filters)
    
    return columns, data

def validate_filters(filters):
    """Validate the filters passed to the report"""
    if not filters.get("from_date"):
        frappe.throw(_("From Date is mandatory"))
    
    if not filters.get("to_date"):
        frappe.throw(_("To Date is mandatory"))
    
    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw(_("From Date cannot be greater than To Date"))

def get_columns(filters):
    """Define the columns for the report"""
    columns = [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 90
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 120
        },
        {
            "label": _("Party Type"),
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Dynamic Link",
            "options": "party_type",
            "width": 150
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Balance"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 100
        }
    ]
    
    return columns

def get_data(filters):
    """Get the main data for the report"""
    # Get GL entries based on filters
    gl_entries = get_gl_entries(filters)
    
    # Get opening balances
    opening_balances = get_opening_balances(filters)
    
    # Process data to include running balances
    data = process_gl_data(gl_entries, opening_balances, filters)
    
    return data

def get_gl_entries(filters):
    """Fetch GL entries based on filters"""
    conditions = get_conditions(filters)
    
    query = """
        SELECT 
            posting_date,
            account,
            voucher_type,
            voucher_no,
            party_type,
            party,
            debit_amount as debit,
            credit_amount as credit
        FROM `tabGL Entry`
        WHERE docstatus = 1 {conditions}
        ORDER BY account, posting_date, creation
    """.format(conditions=conditions)
    
    return frappe.db.sql(query, filters, as_dict=1)

def get_conditions(filters):
    """Build SQL conditions based on filters"""
    conditions = []
    
    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
    
    if filters.get("account"):
        conditions.append("account = %(account)s")
    
    if filters.get("party"):
        conditions.append("party = %(party)s")
    
    if filters.get("party_type"):
        conditions.append("party_type = %(party_type)s")
    
    return " AND " + " AND ".join(conditions) if conditions else ""

def get_opening_balances(filters):
    """Calculate opening balances for accounts"""
    conditions = get_conditions(filters)
    # Remove the from_date condition and add < from_date for opening balance
    conditions = conditions.replace("posting_date >= %(from_date)s", "posting_date < %(from_date)s")
    
    query = """
        SELECT 
            account,
            SUM(debit_amount) - SUM(credit_amount) as opening_balance
        FROM `tabGL Entry`
        WHERE docstatus = 1 {conditions}
        GROUP BY account
    """.format(conditions=conditions)
    
    opening_data = frappe.db.sql(query, filters, as_dict=1)
    
    # Convert to dictionary for easy lookup
    opening_balances = {}
    for row in opening_data:
        opening_balances[row.account] = flt(row.opening_balance)
    
    # Also get opening balance from Account doctype
    account_opening_balances = get_account_opening_balances(filters)
    
    # Merge both opening balances
    for account, balance in account_opening_balances.items():
        opening_balances[account] = flt(opening_balances.get(account, 0)) + flt(balance)
    
    return opening_balances

def get_account_opening_balances(filters):
    """Get opening balances set in Account doctype"""
    conditions = ""
    if filters.get("account"):
        conditions = "WHERE name = %(account)s"
    
    query = """
        SELECT name as account, opening_balance
        FROM `tabAccount`
        {conditions}
    """.format(conditions=conditions)
    
    opening_data = frappe.db.sql(query, filters, as_dict=1)
    
    opening_balances = {}
    for row in opening_data:
        if flt(row.opening_balance):
            opening_balances[row.account] = flt(row.opening_balance)
    
    return opening_balances

def process_gl_data(gl_entries, opening_balances, filters):
    """Process GL entries to add running balances and opening entries"""
    data = []
    account_balances = {}
    
    # Group entries by account
    account_wise_entries = {}
    for entry in gl_entries:
        if entry.account not in account_wise_entries:
            account_wise_entries[entry.account] = []
        account_wise_entries[entry.account].append(entry)
    
    # Process each account
    for account in sorted(account_wise_entries.keys()):
        entries = account_wise_entries[account]
        
        # Get opening balance for this account
        opening_balance = flt(opening_balances.get(account, 0))
        current_balance = opening_balance
        
        # Add opening balance row if there's an opening balance
        if opening_balance != 0:
            data.append({
                "posting_date": filters.get("from_date"),
                "account": account,
                "voucher_type": "",
                "voucher_no": "",
                "party_type": "",
                "party": "",
                "debit": opening_balance if opening_balance > 0 else 0,
                "credit": abs(opening_balance) if opening_balance < 0 else 0,
                "balance": opening_balance,
                "is_opening": True
            })
        
        # Process each entry for this account
        for entry in entries:
            debit = flt(entry.debit)
            credit = flt(entry.credit)
            current_balance += debit - credit
            
            entry_data = {
                "posting_date": entry.posting_date,
                "account": entry.account,
                "voucher_type": entry.voucher_type,
                "voucher_no": entry.voucher_no,
                "party_type": entry.party_type,
                "party": entry.party,
                "debit": debit,
                "credit": credit,
                "balance": current_balance
            }
            
            data.append(entry_data)
        
        # Add account totals
        total_debit = sum(flt(entry.debit) for entry in entries) + (opening_balance if opening_balance > 0 else 0)
        total_credit = sum(flt(entry.credit) for entry in entries) + (abs(opening_balance) if opening_balance < 0 else 0)
        
        data.append({
            "posting_date": "",
            "account": f"<b>Total for {account}</b>",
            "voucher_type": "",
            "voucher_no": "",
            "party_type": "",
            "party": "",
            "debit": total_debit,
            "credit": total_credit,
            "balance": current_balance,
            "is_total": True
        })
        
        # Add empty row for separation
        data.append({})
    
    return data