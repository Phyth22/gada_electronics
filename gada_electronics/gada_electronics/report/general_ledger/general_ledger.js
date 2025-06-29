// Copyright (c) 2025, Agatha and contributors
// For license information, please see license.txt

// frappe.query_reports["General Ledger"] = {
// 	"filters": [

// 	]
// };
// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["General Ledger"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "account",
            "label": __("Account"),
            "fieldtype": "Link",
            "options": "Account",
            "get_query": function() {
                return {
                    "filters": {
                        "is_group": 0
                    }
                }
            }
        },
        {
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Select",
            "options": "\nCustomer\nSupplier"
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "Dynamic Link",
            "options": "party_type"
        },
        {
            "fieldname": "group_by",
            "label": __("Group By"),
            "fieldtype": "Select",
            "options": "Account\nParty\nVoucher Type",
            "default": "Account"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (data && data.is_opening) {
            // Style opening balance rows
            value = `<span style="font-style: italic; color: #666;">${value}</span>`;
        }
        
        if (data && data.is_total) {
            // Style total rows
            value = `<span style="font-weight: bold;">${value}</span>`;
        }
        
        // Highlight debit/credit amounts
        if (column.fieldname === "debit" && data && data.debit > 0) {
            value = `<span style="color: #d73527;">${value}</span>`;
        }
        
        if (column.fieldname === "credit" && data && data.credit > 0) {
            value = `<span style="color: #5cb85c;">${value}</span>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export"), function() {
            frappe.utils.csv_to_file(report.data, __("General Ledger"));
        });
        
        // Set default fiscal year dates
        let fiscal_year = frappe.defaults.get_user_default("fiscal_year");
        if (fiscal_year) {
            frappe.db.get_value("Fiscal Year", fiscal_year, ["start_date", "end_date"])
                .then(r => {
                    if (r.message) {
                        report.set_filter_value("from_date", r.message.start_date);
                        report.set_filter_value("to_date", r.message.end_date);
                    }
                });
        }
    }
};