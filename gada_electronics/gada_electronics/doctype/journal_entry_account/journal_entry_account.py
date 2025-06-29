import frappe
from frappe.model.document import Document
from frappe.utils import flt
from gada_electronics.gada_electronics.utils.gl_utils import make_gl_entries, make_reverse_gl_entries, validate_gl_entries



class JournalEntry(Document):
    def validate(self):
        """Validate the journal entry before saving"""
        self.validate_entries()
        self.calculate_totals()
        self.validate_balance()
    
    def validate_entries(self):
        """Validate accounting entries"""
        if not self.accounting_entries:
            frappe.throw("Accounting Entries table cannot be empty")
        
        has_debit = False
        has_credit = False
        
        for entry in self.accounting_entries:
            if not entry.account:
                frappe.throw("Account is mandatory in Accounting Entries")
            
            # Validate that account is not a group account
            is_group = frappe.db.get_value('Account', entry.account, 'is_group')
            if is_group:
                frappe.throw(f"Account {entry.account} is a group account. Please select a ledger account.")
            
            # Check for both debit and credit in same row
            if flt(entry.debit) > 0 and flt(entry.credit) > 0:
                frappe.throw("Cannot have both Debit and Credit amounts in the same row")
            
            # Check for at least one debit or credit
            if flt(entry.debit) <= 0 and flt(entry.credit) <= 0:
                frappe.throw("Either Debit or Credit amount must be greater than 0")
            
            if flt(entry.debit) > 0:
                has_debit = True
            if flt(entry.credit) > 0:
                has_credit = True
        
        if not has_debit or not has_credit:
            frappe.throw("Journal Entry must have at least one Debit and one Credit entry")
    
    def calculate_totals(self):
        """Calculate total debit and credit"""
        self.total_debit = sum(flt(entry.debit) for entry in self.accounting_entries)
        self.total_credit = sum(flt(entry.credit) for entry in self.accounting_entries)
        self.difference = self.total_debit - self.total_credit
    
    def validate_balance(self):
        """Validate that total debit equals total credit"""
        if abs(flt(self.difference)) > 0.01:
            frappe.throw(f"Total Debit ({self.total_debit}) must equal Total Credit ({self.total_credit})")
    
    def on_submit(self):
        """Create GL entries when journal entry is submitted"""
        self.make_gl_entries()
    
    def on_cancel(self):
        """Create reverse GL entries when journal entry is cancelled"""
        make_reverse_gl_entries('Journal Entry', self.name)
    
    def make_gl_entries(self):
        """Create GL entries for journal entry"""
        gl_map = []
        
        for entry in self.accounting_entries:
            gl_map.append({
                'account': entry.account,
                'party': entry.party,
                'debit': flt(entry.debit),
                'credit': flt(entry.credit)
            })
        
        # Validate and create GL entries
        validate_gl_entries(gl_map)
        make_gl_entries(gl_map, 'Journal Entry', self.name, self.posting_date)
        
        frappe.msgprint(f"GL Entries created for Journal Entry {self.name}")