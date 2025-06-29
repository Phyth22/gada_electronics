import frappe
from frappe import _
from frappe.utils import flt, nowdate

def make_gl_entries(gl_map, voucher_type, voucher_no, posting_date=None, party=None):
    """
    Create GL Entries from a list of account entries
    """
    if not posting_date:
        posting_date = nowdate()

    gl_entries = []

    for entry in gl_map:
        if not entry.get("account"):
            continue

        if not (flt(entry.get("debit", 0)) or flt(entry.get("credit", 0))):
            continue

        gl_entry = frappe.get_doc({
            "doctype": "GL Entry",
            "posting_date": posting_date,
            "account": entry.get("account"),
            "party": entry.get("party") or party,
            "debit_amount": flt(entry.get("debit", 0)),
            "credit_amount": flt(entry.get("credit", 0)),
            "voucher_type": voucher_type,
            "voucher_number": voucher_no,
            "is_cancelled": 0
        })

        try:
            gl_entry.insert(ignore_permissions=True)
            gl_entries.append(gl_entry.name)
        except Exception as e:
            frappe.log_error(title="GL Entry Error", message=frappe.get_traceback())
            frappe.throw(_("Error creating GL Entry for account {0}: {1}").format(entry.get("account"), str(e)))

    return gl_entries


def make_reverse_gl_entries(voucher_type, voucher_no):
    """
    Create reverse GL entries for a cancelled transaction
    """
    existing_entries = frappe.get_all("GL Entry",
        filters={
            "voucher_type": voucher_type,
            "voucher_number": voucher_no,
            "is_cancelled": 0
        },
        fields=["name", "account", "party", "debit_amount", "credit_amount", "posting_date"]
    )

    reverse_entries = []

    for entry in existing_entries:
        reverse_entry = frappe.get_doc({
            "doctype": "GL Entry",
            "posting_date": entry.posting_date,
            "account": entry.account,
            "party": entry.party,
            "debit_amount": entry.credit_amount,
            "credit_amount": entry.debit_amount,
            "voucher_type": voucher_type,
            "voucher_number": voucher_no,
            "is_cancelled": 1
        })

        reverse_entry.insert(ignore_permissions=True)
        reverse_entries.append(reverse_entry.name)

        # Mark original as cancelled
        frappe.db.set_value("GL Entry", entry.name, "is_cancelled", 1)

    return reverse_entries


def validate_gl_entries(gl_map):
    """
    Validate that total debits = total credits
    """
    total_debit = sum(flt(entry.get("debit", 0)) for entry in gl_map)
    total_credit = sum(flt(entry.get("credit", 0)) for entry in gl_map)

    if abs(total_debit - total_credit) > 0.001:
        frappe.throw(_("Total Debit ({0}) must equal Total Credit ({1})").format(total_debit, total_credit))

    return True


def get_account_balance(account, party=None, posting_date=None):
    """
    Get the balance of a specific account
    """
    if not posting_date:
        posting_date = nowdate()

    filters = {
        "account": account,
        "posting_date": ["<=", posting_date],
        "is_cancelled": 0
    }

    if party:
        filters["party"] = party

    entries = frappe.get_all("GL Entry",
        filters=filters,
        fields=["debit_amount", "credit_amount"]
    )

    balance = sum(flt(e.debit_amount) - flt(e.credit_amount) for e in entries)
    return balance
