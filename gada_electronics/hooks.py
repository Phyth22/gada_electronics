app_name = "gada_electronics"
app_title = "Gada Electronics"
app_publisher = "Agatha"
app_description = "Accounting Application"
app_email = "faiththiah2@gmail.com"
app_license = "mit"

# Document Events
doc_events = {
    "Sales Invoice": {
        "on_submit": "gada_electronics.gada_electronics.doctype.sales_invoice.sales_invoice.on_submit",
        "on_cancel": "gada_electronics.gada_electronics.doctype.sales_invoice.sales_invoice.on_cancel"
    },
    "Purchase Invoice": {
        "on_submit": "gada_electronics.gada_electronics.doctype.purchase_invoice.purchase_invoice.on_submit",
        "on_cancel": "gada_electronics.gada_electronics.doctype.purchase_invoice.purchase_invoice.on_cancel"
    },
    "Payment Entry": {
        "on_submit": "gada_electronics.gada_electronics.doctype.payment_entry.payment_entry.on_submit",
        "on_cancel": "gada_electronics.gada_electronics.doctype.payment_entry.payment_entry.on_cancel"
    },
    "Journal Entry": {
        "on_submit": "gada_electronics.gada_electronics.doctype.journal_entry.journal_entry.on_submit",
        "on_cancel": "gada_electronics.gada_electronics.doctype.journal_entry.journal_entry.on_cancel"
    }
}

# Permission Query Conditions
permission_query_conditions = {
    "GL Entry": "gada_electronics.gada_electronics.doctype.gl_entry.gl_entry.get_permission_query_conditions"
}

# Optional Boot Session or Startup hooks (uncomment if you implement them)
# boot_session = "gada_electronics.boot.boot_session"
# startup = "gada_electronics.startup.startup"

fixtures = ["Account"]
