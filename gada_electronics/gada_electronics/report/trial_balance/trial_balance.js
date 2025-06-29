// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Trial Balance"] = {
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
                        "is_group": 1
                    }
                }
            }
        },
        {
            "fieldname": "show_zero_values",
            "label": __("Show Zero Values"),
            "fieldtype": "Check",
            "default": 1
        },
        {
            "fieldname": "account_type",
            "label": __("Account Type"),
            "fieldtype": "Select",
            "options": "\nAsset\nLiability\nIncome\nExpense\nEquity"
        },
        {
            "fieldname": "presentation_currency",
            "label": __("Presentation Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "default": frappe.defaults.get_user_default("currency")
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (data && data.is_total_row) {
            // Style total rows
            value = `<span style="font-weight: bold; background-color: #f8f9fa;">${value}</span>`;
        }
        
        if (data && data.is_group) {
            // Style group account rows
            let indent = data.indent || 0;
            let padding = indent * 20;
            
            if (column.fieldname === "account") {
                value = `<span style="font-weight: bold; padding-left: ${padding}px;">${value}</span>`;
            } else {
                value = `<span style="font-weight: bold;">${value}</span>`;
            }
        } else if (data && !data.is_total_row) {
            // Style leaf account rows with proper indentation
            let indent = data.indent || 0;
            let padding = indent * 20;
            
            if (column.fieldname === "account") {
                value = `<span style="padding-left: ${padding}px;">${value}</span>`;
            }
        }
        
        // Highlight debit amounts in red
        if ((column.fieldname === "opening_debit" || column.fieldname === "debit" || column.fieldname === "closing_debit") 
            && data && parseFloat(data[column.fieldname] || 0) > 0) {
            value = `<span style="color: #d73527;">${value}</span>`;
        }
        
        // Highlight credit amounts in green
        if ((column.fieldname === "opening_credit" || column.fieldname === "credit" || column.fieldname === "closing_credit") 
            && data && parseFloat(data[column.fieldname] || 0) > 0) {
            value = `<span style="color: #5cb85c;">${value}</span>`;
        }
        
        return value;
    },

    "tree": true,
    "name_field": "account",
    "parent_field": "parent_account",
    "initial_depth": 3,

    "onload": function(report) {
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

        // Add custom buttons
        report.page.add_inner_button(__("Export to Excel"), function() {
            let data = report.data || [];
            let columns = report.columns || [];
            
            // Prepare data for export
            let export_data = data.map(row => {
                let export_row = {};
                columns.forEach(col => {
                    export_row[col.label] = row[col.fieldname] || "";
                });
                return export_row;
            });
            
            frappe.utils.csv_to_file(export_data, __("Trial Balance"));
        });

        report.page.add_inner_button(__("Balance Sheet"), function() {
            frappe.set_route("query-report", "Balance Sheet", {
                "from_date": report.get_filter_value("from_date"),
                "to_date": report.get_filter_value("to_date")
            });
        });

        report.page.add_inner_button(__("Profit and Loss"), function() {
            frappe.set_route("query-report", "Profit and Loss Statement", {
                "from_date": report.get_filter_value("from_date"),
                "to_date": report.get_filter_value("to_date")
            });
        });
    },

    "after_datatable_render": function(datatable_obj) {
        // Add custom styling after the datatable is rendered
        $(datatable_obj.wrapper).find('.dt-row').each(function() {
            let $row = $(this);
            let rowData = $row.data();
            
            if (rowData && rowData.is_total_row) {
                $row.css({
                    'background-color': '#f8f9fa',
                    'font-weight': 'bold',
                    'border-top': '2px solid #dee2e6'
                });
            }
        });
    },

    "get_datatable_options": function(options) {
        return Object.assign(options, {
            checkboxColumn: false,
            inlineFilters: true,
            treeView: true,
            expandAllOnLoad: false
        });
    }
};
