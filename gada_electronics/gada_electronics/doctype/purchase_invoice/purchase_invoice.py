import frappe
from frappe.model.document import Document
from frappe.utils import flt
from your_app.utils.gl_entry_utils import make_gl_entries, make_reverse_gl_entries, validate_gl_entries

class PurchaseInvoice(Document):
    def validate(self):
        """Validate the purchase invoice before saving"""
        self.validate_supplier()
        self.validate_items()
        self.validate_accounts()
        self.calculate_totals()
    
    def validate_supplier(self):
        """Validate that the selected party is a supplier"""
        if self.supplier:
            party_type = frappe.db.get_value('Party', self.supplier, 'party_type')
            if party_type != 'Supplier':
                frappe.throw(f"Selected party {self.supplier} is not a Supplier")
    
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
        if self.credit_to:
            account_type = frappe.db.get_value('Account', self.credit_to, 'account_type')
            if account_type != 'Liability':
                frappe.throw("Credit To account must be a Liability account")
        
        if self.expense_account:
            account_type = frappe.db.get_value('Account', self.expense_account, 'account_type')
            if account_type != 'Expense':
                frappe.throw("Expense Account must be an Expense account")
    
    def calculate_totals(self):
        """Calculate total quantity and amount"""
        self.total_qty = sum(flt(item.qty) for item in self.items)
        self.total_amount = sum(flt(item.amount) for item in self.items)
    
    def on_submit(self):
        """Create GL entries when purchase invoice is submitted"""
        self.make_gl_entries()
    
    def on_cancel(self):
        """Create reverse GL entries when purchase invoice is cancelled"""
        make_reverse_gl_entries('Purchase Invoice', self.name)
    
    def make_gl_entries(self):
        """Create GL entries for purchase invoice"""
        gl_map = []
        
        # Debit: Expense Account (Expense increases)
        gl_map.append({
            'account': self.expense_account,
            'party': self.supplier,
            'debit': self.total_amount,
            'credit': 0
        })
        
        # Credit: Accounts Payable (Liability increases)
        gl_map.append({
            'account': self.credit_to,
            'party': self.supplier,
            'debit': 0,
            'credit': self.total_amount
        })
        
        # Validate and create GL entries
        validate_gl_entries(gl_map)
        make_gl_entries(gl_map, 'Purchase Invoice', self.name, self.posting_date, self.supplier)
        
        frappe.msgprint(f"GL Entries created for Purchase Invoice {self.name}")