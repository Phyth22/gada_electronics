import frappe
from frappe.model.document import Document
from frappe.utils import flt
from gada_electronics.gada_electronics.utils.gl_utils import make_gl_entries, make_reverse_gl_entries, validate_gl_entries


class SalesInvoice(Document):
    def validate(self):
        """Validate the sales invoice before saving"""
        self.validate_customer()
        self.validate_items()
        self.validate_accounts()
        self.calculate_totals()
    
    def validate_customer(self):
        """Validate that the selected party is a customer"""
        if self.customer:
            party_type = frappe.db.get_value('Party', self.customer, 'party_type')
            if party_type != 'Customer':
                frappe.throw(f"Selected party {self.customer} is not a Customer")
    
    def validate_items(self):
        """Validate items and calculate amounts"""
        if not self.items:
            frappe.throw("Items table cannot be empty")
        
        for item in self.items:
            if not item.item:
                frappe.throw("Item is mandatory in Items table")
            if flt(item.qty) <= 0:
                frappe.throw(f"Quantity must be greater than 0 for item {item.item}")
            if flt(item.rate) <= 0:
                frappe.throw(f"Rate must be greater than 0 for item {item.item}")
            
            # Calculate amount
            item.amount = flt(item.qty) * flt(item.rate)
    
    def validate_accounts(self):
        """Validate selected accounts"""
        if self.debit_to:
            account_type = frappe.db.get_value('Account', self.debit_to, 'account_type')
            if account_type != 'Asset':
                frappe.throw("Debit To account must be an Asset account")
        
        if self.income_account:
            account_type = frappe.db.get_value('Account', self.income_account, 'account_type')
            if account_type != 'Income':
                frappe.throw("Income Account must be an Income account")
    
    def calculate_totals(self):
        """Calculate total quantity and amount"""
        self.total_qty = sum(flt(item.qty) for item in self.items)
        self.total_amount = sum(flt(item.amount) for item in self.items)
    
    def on_submit(self):
        """Create GL entries when sales invoice is submitted"""
        self.make_gl_entries()
    
    def on_cancel(self):
        """Create reverse GL entries when sales invoice is cancelled"""
        make_reverse_gl_entries('Sales Invoice', self.name)
    
    def make_gl_entries(self):
        """Create GL entries for sales invoice"""
        gl_map = []
        
        # Debit: Accounts Receivable (Asset increases)
        gl_map.append({
            'account': self.debit_to,
            'party': self.customer,
            'debit': self.total_amount,
            'credit': 0
        })
        
        # Credit: Income Account (Revenue increases)
        gl_map.append({
            'account': self.income_account,
            'party': self.customer,
            'debit': 0,
            'credit': self.total_amount
        })
        
        # Validate and create GL entries
        validate_gl_entries(gl_map)
        make_gl_entries(gl_map, 'Sales Invoice', self.name, self.posting_date, self.customer)
        
        frappe.msgprint(f"GL Entries created for Sales Invoice {self.name}")