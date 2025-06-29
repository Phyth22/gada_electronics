# Copyright (c) 2025, Agatha and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

class TestSalesInvoice(FrappeTestCase):
    def setUp(self):
        """
        Prepare dummy data for testing:
        - Chart of accounts (Test Receivable and Test Income)
        - Customer (Test Customer)
        - Item (Laptop)
        """
        self.ensure_account("Test Receivable", "Receivable")
        self.ensure_account("Test Income", "Income")
        self.ensure_party("Test Customer", "Customer")
        self.ensure_item("Laptop")

    def ensure_account(self, name, account_type):
        """
        Create a dummy account if it doesn't exist.
        """
        if not frappe.db.exists("Account", name):
            frappe.get_doc({
                "doctype": "Account",
                "account_name": name,
                "account_type": account_type,
                "is_group": 0
            }).insert(ignore_permissions=True, commit=False)  # Prevents implicit commit error

    def ensure_party(self, name, party_type):
        """
        Create a dummy party (Customer or Supplier).
        """
        if not frappe.db.exists("Party", name):
            frappe.get_doc({
                "doctype": "Party",
                "party_name": name,
                "party_type": party_type
            }).insert(ignore_permissions=True, commit=False)

    def ensure_item(self, item_code):
        """
        Create a dummy item (e.g. Laptop).
        """
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "default_unit_of_measurement": "Nos",
                "standard_selling_rate": 1000
            }).insert(ignore_permissions=True, commit=False)

    def test_sales_invoice_submission_and_gl_entry(self):
        """
        Main test:
        - Create and submit a Sales Invoice
        - Check that 2 GL Entries are created (debit and credit)
        """
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "naming_series": "SINV-",
            "customer": "Test Customer",
            "posting_date": frappe.utils.nowdate(),
            "payment_due_date": frappe.utils.nowdate(),
            "debit_to": "Test Receivable",     # Should be a Receivable account
            "income_account": "Test Income",   # Should be an Income account
            "items": [
                {
                    "item": "Laptop",
                    "qty": 2,
                    "rate": 1000
                }
            ]
        })
        invoice.insert(ignore_permissions=True, commit=False)
        invoice.submit()

        # Check that 2 GL Entries were created (1 debit, 1 credit)
        gl_entries = frappe.get_all("GL Entry", filters={
            "voucher_type": "Sales Invoice",
            "voucher_number": invoice.name,
            "is_cancelled": 0
        })

        # The assertion ensures accounting was triggered correctly
        self.assertEqual(len(gl_entries), 2)
