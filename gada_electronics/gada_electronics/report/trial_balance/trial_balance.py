# Copyright (c) 2025, Agatha and contributors
# For license information, please see license.txt

import frappe

# def execute(filters=None):
# 	columns, data = [], []
# 	return columns, data

# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, cstr

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
    
    # Get report summary
    report_summary = get_report_summary(data)
    
    return columns, data, None, None, report_summary

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
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 300
        },
        {
            "label": _("Opening (Dr)"),
            "fieldname": "opening_debit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Opening (Cr)"),
            "fieldname": "opening_credit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Closing (Dr)"),
            "fieldname": "closing_debit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Closing (Cr)"),
            "fieldname": "closing_credit",
            "fieldtype": "Currency",
            "width": 120
        }
    ]
    
    return columns

def get_data(filters):
    """Get the main data for the trial balance"""
    # Get all accounts
    accounts = get_accounts(filters)
    
    # Get opening balances
    opening_balances = get_opening_balances(filters)
    
    # Get period balances
    period_balances = get_period_balances(filters)
    
    # Process and build trial balance data
    data = build_trial_balance(accounts, opening_balances, period_balances, filters)
    
    return data

def get_accounts(filters):
    """Get all accounts for the trial balance"""
    conditions = ""
    if filters.get("account"):
        conditions = "WHERE name = %(account)s"
    
    query = """
        SELECT 
            name,
            account_name,
            account_type,
            is_group,
            parent_account,
            lft,
            rgt
        FROM `tabAccount`
        {conditions}
        ORDER BY lft
    """.format(conditions=conditions)
    
    accounts = frappe.db.sql(query, filters, as_dict=1)
    return accounts

def get_opening_balances(filters):
    """Get opening balances for all accounts"""
    # Get opening balances from Account doctype
    account_opening = frappe.db.sql("""
        SELECT name as account, opening_balance
        FROM `tabAccount`
        WHERE opening_balance != 0
    """, as_dict=1)
    
    opening_balances = {}
    for row in account_opening:
        opening_balances[row.account] = flt(row.opening_balance)
    
    # Get opening balances from GL entries before from_date
    gl_opening = frappe.db.sql("""
        SELECT 
            account,
            SUM(debit_amount) - SUM(credit_amount) as balance
        FROM `tabGL Entry`
        WHERE docstatus = 1 
        AND posting_date < %(from_date)s
        GROUP BY account
    """, filters, as_dict=1)
    
    # Add GL opening balances
    for row in gl_opening:
        opening_balances[row.account] = flt(opening_balances.get(row.account, 0)) + flt(row.balance)
    
    return opening_balances

def get_period_balances(filters):
    """Get period balances for all accounts"""
    period_balances = frappe.db.sql("""
        SELECT 
            account,
            SUM(debit_amount) as debit,
            SUM(credit_amount) as credit
        FROM `tabGL Entry`
        WHERE docstatus = 1 
        AND posting_date >= %(from_date)s
        AND posting_date <= %(to_date)s
        GROUP BY account
    """, filters, as_dict=1)
    
    balances = {}
    for row in period_balances:
        balances[row.account] = {
            'debit': flt(row.debit),
            'credit': flt(row.credit)
        }
    
    return balances

def build_trial_balance(accounts, opening_balances, period_balances, filters):
    """Build the trial balance data with hierarchy"""
    data = []
    
    # Create account hierarchy
    account_hierarchy = build_account_hierarchy(accounts)
    
    # Process each account
    for account in accounts:
        account_name = account.name
        
        # Get opening balance
        opening_balance = flt(opening_balances.get(account_name, 0))
        
        # Get period movements
        period_data = period_balances.get(account_name, {})
        period_debit = flt(period_data.get('debit', 0))
        period_credit = flt(period_data.get('credit', 0))
        
        # Calculate closing balance
        closing_balance = opening_balance + period_debit - period_credit
        
        # Skip accounts with no movement if specified
        if filters.get("show_zero_values") == 0:
            if opening_balance == 0 and period_debit == 0 and period_credit == 0:
                continue
        
        # Prepare row data
        row_data = {
            "account": account_name,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "is_group": account.is_group,
            "parent_account": account.parent_account,
            "indent": get_account_indent(account_name, account_hierarchy),
            "opening_debit": opening_balance if opening_balance > 0 else 0,
            "opening_credit": abs(opening_balance) if opening_balance < 0 else 0,
            "debit": period_debit,
            "credit": period_credit,
            "closing_debit": closing_balance if closing_balance > 0 else 0,
            "closing_credit": abs(closing_balance) if closing_balance < 0 else 0
        }
        
        data.append(row_data)
    
    # Add group totals
    data = add_group_totals(data, accounts)
    
    # Add grand totals
    data = add_grand_totals(data)
    
    return data

def build_account_hierarchy(accounts):
    """Build account hierarchy for indentation"""
    hierarchy = {}
    for account in accounts:
        hierarchy[account.name] = {
            'parent': account.parent_account,
            'is_group': account.is_group,
            'lft': account.lft,
            'rgt': account.rgt
        }
    return hierarchy

def get_account_indent(account_name, hierarchy):
    """Calculate indentation level for account"""
    indent = 0
    current_account = account_name
    
    while current_account and hierarchy.get(current_account, {}).get('parent'):
        indent += 1
        current_account = hierarchy[current_account]['parent']
    
    return indent

def add_group_totals(data, accounts):
    """Add totals for group accounts"""
    # Create a map of accounts by parent
    children_map = {}
    for account in accounts:
        if account.parent_account:
            if account.parent_account not in children_map:
                children_map[account.parent_account] = []
            children_map[account.parent_account].append(account.name)
    
    # Calculate group totals
    group_totals = {}
    
    def calculate_group_total(group_account):
        if group_account in group_totals:
            return group_totals[group_account]
        
        total = {
            'opening_debit': 0,
            'opening_credit': 0,
            'debit': 0,
            'credit': 0,
            'closing_debit': 0,
            'closing_credit': 0
        }
        
        # Get children of this group
        children = children_map.get(group_account, [])
        
        for child in children:
            # Find child data
            child_data = None
            for row in data:
                if row['account'] == child:
                    child_data = row
                    break
            
            if child_data:
                # If child is also a group, calculate its total first
                if child_data.get('is_group'):
                    child_total = calculate_group_total(child)
                    for key in total:
                        total[key] += flt(child_total.get(key, 0))
                else:
                    # Add child amounts to total
                    for key in total:
                        total[key] += flt(child_data.get(key, 0))
        
        group_totals[group_account] = total
        return total
    
    # Update group account data with calculated totals
    for i, row in enumerate(data):
        if row.get('is_group'):
            account_name = row['account']
            totals = calculate_group_total(account_name)
            data[i].update(totals)
    
    return data

def add_grand_totals(data):
    """Add grand totals at the end"""
    grand_totals = {
        'opening_debit': 0,
        'opening_credit': 0,
        'debit': 0,
        'credit': 0,
        'closing_debit': 0,
        'closing_credit': 0
    }
    
    # Calculate grand totals (only for root level accounts)
    for row in data:
        if not row.get('parent_account') or row.get('indent', 0) == 0:
            for key in grand_totals:
                grand_totals[key] += flt(row.get(key, 0))
    
    # Add grand total row
    data.append({
        'account': '<b>Total</b>',
        'account_name': '',
        'is_total_row': True,
        'opening_debit': grand_totals['opening_debit'],
        'opening_credit': grand_totals['opening_credit'],
        'debit': grand_totals['debit'],
        'credit': grand_totals['credit'],
        'closing_debit': grand_totals['closing_debit'],
        'closing_credit': grand_totals['closing_credit']
    })
    
    return data

def get_report_summary(data):
    """Get report summary for display"""
    if not data:
        return []
    
    # Get the total row (last row)
    total_row = data[-1] if data and data[-1].get('is_total_row') else {}
    
    opening_debit = flt(total_row.get('opening_debit', 0))
    opening_credit = flt(total_row.get('opening_credit', 0))
    period_debit = flt(total_row.get('debit', 0))
    period_credit = flt(total_row.get('credit', 0))
    closing_debit = flt(total_row.get('closing_debit', 0))
    closing_credit = flt(total_row.get('closing_credit', 0))
    
    # Check if trial balance is balanced
    is_balanced = (closing_debit == closing_credit)
    balance_status = "Balanced" if is_balanced else "Not Balanced"
    difference = closing_debit - closing_credit
    
    summary = [
        {
            "value": opening_debit,
            "label": "Opening Debit",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": opening_credit,
            "label": "Opening Credit", 
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": period_debit,
            "label": "Period Debit",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": period_credit,
            "label": "Period Credit",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": closing_debit,
            "label": "Closing Debit",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": closing_credit,
            "label": "Closing Credit",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": balance_status,
            "label": "Status",
            "indicator": "Green" if is_balanced else "Red"
        }
    ]
    
    if not is_balanced:
        summary.append({
            "value": abs(difference),
            "label": "Difference",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD",
            "indicator": "Red"
        })
    
    return summary