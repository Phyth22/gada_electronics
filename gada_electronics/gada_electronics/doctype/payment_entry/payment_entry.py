import frappe
from frappe.model.document import Document
from frappe.utils import flt
from gada_electronics.gada_electronics.utils.gl_utils import make_gl_entries, make_reverse_gl_entries, validate_gl_entries



class PaymentEntry(Document):
    def validate(self):
        """Validate the payment entry before saving"""
        self.validate_party_type()
        self.validate_payment_type()
        self.validate_accounts()
        self.validate_amount()
    
    def validate_party_type(self):
        """Validate party type matches payment type"""
        if self.payment_type == 'Receive' and self.party_type != 'Customer':
            frappe.throw("For Receive payment, Party Type must be Customer")
        elif self.payment_type == 'Pay' and self.party_type != 'Supplier':
            frappe.throw("For Pay payment, Party Type must be Supplier")
    
    def validate_payment_type(self):
        """Validate payment type logic"""
        if self.party:
            party_type = frappe.db.get_value('Party', self.party, 'party_type')
            if party_type != self.party_type:
                frappe.throw(f"Selected party {self.party} is not a {self.party_type}")
    
    def validate_accounts(self):
        """Validate that accounts are not group accounts"""
        for account_field in ['account_paid_from', 'account_paid_to']:
            account = self.get(account_field)
            if account:
                is_group = frappe.db.get_value('Account', account, 'is_group')
                if is_group:
                    frappe.throw(f"{account} is a group account. Please select a ledger account.")
    
    def validate_amount(self):
        """Validate amount is positive"""
        if flt(self.amount) <= 0:
            frappe.throw("Amount must be greater than 0")
    
    def on_submit(self):
        """Create GL entries when payment entry is submitted"""
        self.make_gl_entries()
    
    def on_cancel(self):
        """Create reverse GL entries when payment entry is cancelled"""
        make_reverse_gl_entries('Payment Entry', self.name)
    
    def make_gl_entries(self):
        """Create GL entries for payment entry"""
        gl_map = []
        
        if self.payment_type == 'Receive':
            # Money received from customer
            # Debit: Cash/Bank Account (Asset increases)
            gl_map.append({
                'account': self.account_paid_to,
                'party': self.party,
                'debit': self.amount,
                'credit': 0
            })
            
            # Credit: Accounts Receivable (Asset decreases)
            gl_map.append({
                'account': self.account_paid_from,
                'party': self.party,
                'debit': 0,
                'credit': self.amount
            })
            
        elif self.payment_type == 'Pay':
            # Money paid to supplier
            # Debit: Accounts Payable (Liability decreases)
            gl_map.append({
                'account': self.account_paid_to,
                'party': self.party,
                'debit': self.amount,
                'credit': 0
            })
            
            # Credit: Cash/Bank Account (Asset decreases)
            gl_map.append({
                'account': self.account_paid_from,
                'party': self.party,
                'debit': 0,
                'credit': self.amount
            })
        
        # Validate and create GL entries
        validate_gl_entries(gl_map)
        make_gl_entries(gl_map, 'Payment Entry', self.name, self.posting_date, self.party)
        
        frappe.msgprint(f"GL Entries created for Payment Entry {self.name}")