# Copyright (c) 2025, Agatha and contributors
# For license information, please see license.txt

# import frappe


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
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 150
        }
    ]
    
    # Add comparison columns if previous period is requested
    if filters.get("show_comparison"):
        columns.append({
            "label": _("Previous Period"),
            "fieldname": "previous_amount",
            "fieldtype": "Currency",
            "width": 150
        })
        columns.append({
            "label": _("Variance"),
            "fieldname": "variance",
            "fieldtype": "Currency",
            "width": 120
        })
        columns.append({
            "label": _("Variance %"),
            "fieldname": "variance_percent",
            "fieldtype": "Percent",
            "width": 100
        })
    
    return columns

def get_data(filters):
    """Get the main data for the P&L statement"""
    # Get income and expense accounts
    accounts = get_income_expense_accounts(filters)
    
    # Get current period balances
    current_balances = get_period_balances(filters)
    
    # Get previous period balances if comparison is requested
    previous_balances = {}
    if filters.get("show_comparison"):
        previous_filters = get_previous_period_filters(filters)
        previous_balances = get_period_balances(previous_filters)
    
    # Build P&L statement data
    data = build_profit_loss_statement(accounts, current_balances, previous_balances, filters)
    
    return data

def get_income_expense_accounts(filters):
    """Get all income and expense accounts"""
    conditions = "WHERE account_type IN ('Income', 'Expense')"
    
    if filters.get("account"):
        conditions += " AND name = %(account)s"
    
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
        ORDER BY account_type, lft
    """.format(conditions=conditions)
    
    accounts = frappe.db.sql(query, filters, as_dict=1)
    return accounts

def get_period_balances(filters):
    """Get period balances for income and expense accounts"""
    period_balances = frappe.db.sql("""
        SELECT 
            account,
            SUM(credit_amount) - SUM(debit_amount) as balance
        FROM `tabGL Entry`
        WHERE docstatus = 1 
        AND posting_date >= %(from_date)s
        AND posting_date <= %(to_date)s
        AND account IN (
            SELECT name FROM `tabAccount` 
            WHERE account_type IN ('Income', 'Expense')
        )
        GROUP BY account
    """, filters, as_dict=1)
    
    balances = {}
    for row in period_balances:
        balances[row.account] = flt(row.balance)
    
    return balances

def get_previous_period_filters(filters):
    """Calculate previous period dates for comparison"""
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    
    # Calculate period length
    period_days = (to_date - from_date).days
    
    # Calculate previous period
    previous_to_date = from_date - frappe.utils.datetime.timedelta(days=1)
    previous_from_date = previous_to_date - frappe.utils.datetime.timedelta(days=period_days)
    
    previous_filters = filters.copy()
    previous_filters.update({
        "from_date": previous_from_date,
        "to_date": previous_to_date
    })
    
    return previous_filters

def build_profit_loss_statement(accounts, current_balances, previous_balances, filters):
    """Build the P&L statement with proper structure"""
    data = []
    
    # Separate income and expense accounts
    income_accounts = [acc for acc in accounts if acc.account_type == 'Income']
    expense_accounts = [acc for acc in accounts if acc.account_type == 'Expense']
    
    # Calculate totals
    totals = {
        'income': 0,
        'expense': 0,
        'previous_income': 0,
        'previous_expense': 0
    }
    
    # Add Income Section
    data.append({
        'account': '<b>INCOME</b>',
        'amount': '',
        'is_header': True,
        'indent': 0
    })
    
    # Process income accounts
    income_data = process_accounts_section(income_accounts, current_balances, previous_balances, filters, 'Income')
    data.extend(income_data['accounts'])
    totals['income'] = income_data['total']
    totals['previous_income'] = income_data['previous_total']
    
    # Add total income row
    income_row = {
        'account': '<b>Total Income</b>',
        'amount': totals['income'],
        'is_total': True,
        'indent': 0
    }
    
    if filters.get("show_comparison"):
        income_row.update({
            'previous_amount': totals['previous_income'],
            'variance': totals['income'] - totals['previous_income'],
            'variance_percent': get_variance_percent(totals['income'], totals['previous_income'])
        })
    
    data.append(income_row)
    data.append({})  # Empty row
    
    # Add Expense Section
    data.append({
        'account': '<b>EXPENSES</b>',
        'amount': '',
        'is_header': True,
        'indent': 0
    })
    
    # Process expense accounts
    expense_data = process_accounts_section(expense_accounts, current_balances, previous_balances, filters, 'Expense')
    data.extend(expense_data['accounts'])
    totals['expense'] = expense_data['total']
    totals['previous_expense'] = expense_data['previous_total']
    
    # Add total expense row
    expense_row = {
        'account': '<b>Total Expenses</b>',
        'amount': totals['expense'],
        'is_total': True,
        'indent': 0
    }
    
    if filters.get("show_comparison"):
        expense_row.update({
            'previous_amount': totals['previous_expense'],
            'variance': totals['expense'] - totals['previous_expense'],
            'variance_percent': get_variance_percent(totals['expense'], totals['previous_expense'])
        })
    
    data.append(expense_row)
    data.append({})  # Empty row
    
    # Calculate Net Profit/Loss
    net_profit = totals['income'] - totals['expense']
    previous_net_profit = totals['previous_income'] - totals['previous_expense']
    
    # Add Net Profit/Loss row
    profit_label = '<b>NET PROFIT</b>' if net_profit >= 0 else '<b>NET LOSS</b>'
    profit_row = {
        'account': profit_label,
        'amount': abs(net_profit),
        'is_net_total': True,
        'is_profit': net_profit >= 0,
        'indent': 0
    }
    
    if filters.get("show_comparison"):
        profit_row.update({
            'previous_amount': abs(previous_net_profit),
            'variance': net_profit - previous_net_profit,
            'variance_percent': get_variance_percent(net_profit, previous_net_profit)
        })
    
    data.append(profit_row)
    
    return data

def process_accounts_section(accounts, current_balances, previous_balances, filters, account_type):
    """Process accounts for a specific section (Income/Expense)"""
    section_data = []
    section_total = 0
    previous_section_total = 0
    
    # Build account hierarchy
    account_hierarchy = build_account_hierarchy(accounts)
    
    # Process each account
    for account in accounts:
        account_name = account.name
        
        # Get current period balance
        current_balance = flt(current_balances.get(account_name, 0))
        
        # For expenses, show as positive (debit balance)
        if account_type == 'Expense':
            current_balance = abs(current_balance)
        
        # Get previous period balance
        previous_balance = flt(previous_balances.get(account_name, 0))
        if account_type == 'Expense':
            previous_balance = abs(previous_balance)
        
        # Skip zero balance accounts if requested
        if not filters.get("show_zero_values", True) and current_balance == 0:
            continue
        
        # Calculate variance
        variance = current_balance - previous_balance
        variance_percent = get_variance_percent(current_balance, previous_balance)
        
        # Prepare row data
        row_data = {
            'account': account.account_name or account_name,
            'account_name': account.account_name,
            'account_type': account.account_type,
            'is_group': account.is_group,
            'parent_account': account.parent_account,
            'indent': get_account_indent(account_name, account_hierarchy),
            'amount': current_balance
        }
        
        if filters.get("show_comparison"):
            row_data.update({
                'previous_amount': previous_balance,
                'variance': variance,
                'variance_percent': variance_percent
            })
        
        section_data.append(row_data)
        
        # Add to section total (only for leaf accounts)
        if not account.is_group:
            section_total += current_balance
            previous_section_total += previous_balance
    
    return {
        'accounts': section_data,
        'total': section_total,
        'previous_total': previous_section_total
    }

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
    indent = 1  # Start with 1 for section indentation
    current_account = account_name
    
    while current_account and hierarchy.get(current_account, {}).get('parent'):
        parent = hierarchy[current_account]['parent']
        # Only count parents that are also in the same section
        if parent in hierarchy:
            indent += 1
        current_account = parent
    
    return indent

def get_variance_percent(current, previous):
    """Calculate variance percentage"""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / abs(previous)) * 100

def get_report_summary(data):
    """Get report summary for display"""
    if not data:
        return []
    
    # Find the net profit/loss row
    net_row = None
    income_total = 0
    expense_total = 0
    
    for row in data:
        if row.get('is_net_total'):
            net_row = row
        elif row.get('account') == '<b>Total Income</b>':
            income_total = flt(row.get('amount', 0))
        elif row.get('account') == '<b>Total Expenses</b>':
            expense_total = flt(row.get('amount', 0))
    
    if not net_row:
        return []
    
    net_amount = flt(net_row.get('amount', 0))
    is_profit = net_row.get('is_profit', False)
    
    # Calculate profit margin
    profit_margin = (net_amount / income_total * 100) if income_total > 0 else 0
    
    summary = [
        {
            "value": income_total,
            "label": "Total Income",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": expense_total,
            "label": "Total Expenses",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD"
        },
        {
            "value": net_amount,
            "label": "Net Profit" if is_profit else "Net Loss",
            "datatype": "Currency",
            "currency": frappe.defaults.get_user_default("currency") or "USD",
            "indicator": "Green" if is_profit else "Red"
        },
        {
            "value": profit_margin,
            "label": "Profit Margin %",
            "datatype": "Percent",
            "indicator": "Green" if profit_margin > 0 else "Red"
        }
    ]
    
    return summary