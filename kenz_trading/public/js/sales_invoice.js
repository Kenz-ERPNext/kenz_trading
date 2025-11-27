let item_uoms = {};

frappe.ui.form.on("Sales Invoice", {
    custom_payment_mode: function (frm) {
        set_pos_value(frm);
        // Always show project field regardless of POS mode
        frm.set_df_property('project', 'hidden', 0);
    },
    is_pos: function(frm) {
        // Always show project field regardless of POS mode
        frm.set_df_property('project', 'hidden', 0);
    },
    refresh: function(frm) {
        
        // Always show project field regardless of POS mode
        frm.set_df_property('project', 'hidden', 0);
    },
    customer: function (frm) {
        frm.set_value("custom_session_user", frappe.session.user);
        default_branch(frm);
    },
    setup: function (frm) {
        frm.fields_dict["items"].grid.get_field("uom").get_query = function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.item_code && item_uoms[row.item_code]) {
                return {
                    filters: [["UOM", "name", "in", item_uoms[row.item_code]]]
                };
            } else {
                return {};
            }
        };
    },
    onload: function(frm) {
        // Always show project field regardless of POS mode
        frm.set_df_property('project', 'hidden', 0);
        // Set default warehouse on form load if update_stock is enabled
        set_default_warehouse(frm);
    },
    update_stock: function(frm) {
        // Set or clear warehouse when update_stock is toggled
        set_default_warehouse(frm);
    },


    refresh(frm) {

        frappe.db.get_single_value('Kenza Settings', 'sale_search_window').then(value => {

            // Only show button if enabled
            if (value) {
                cur_frm.add_custom_button(__('Sales Details'), () => {
                    show_last_sales_dialog(frm);
                });
            }

            // Keyboard shortcut
            $(document).off('keydown.item_qty'); // prevent duplicate events
            $(document).on('keydown.item_qty', function (e) {

                // Shift + S
                if (e.shiftKey && e.key.toLowerCase() === "s") {
                    e.preventDefault();   // prevent default browser behavior

                    if (value && cur_frm && cur_frm.doctype === "Sales Invoice") {
                        show_last_sales_dialog(cur_frm);
                    }
                }
            });

        });






        frappe.db.get_single_value('Kenza Settings', 'purchase_search_window').then(value => {

            // Only show button if enabled
            if (value) {
                cur_frm.add_custom_button(__('Purchase Details'), () => {
                    show_last_purchase_dialog(cur_frm);
                });
            }

            // Keyboard shortcut
            $(document).off('keydown.item_qty_purchase'); // prevent duplicates
            $(document).on('keydown.item_qty_purchase', function (e) {

                // Shift + P
                if (e.shiftKey && e.key.toLowerCase() === "p") {

                    e.preventDefault();   // prevent default browser behavior

                    if (value && cur_frm && cur_frm.doctype === "Sales Invoice") {
                        show_last_purchase_dialog(cur_frm);
                    }
                }
            });

        });






        frappe.db.get_single_value('Kenza Settings', 'item_qty_search_window').then(value => {

            // Only show button if enabled
            if (value) {
                cur_frm.add_custom_button(__('Item Qty'), () => {
                    show_item_qty_dialog(cur_frm);
                });
            }

            // Keyboard shortcut
            $(document).off('keydown.item_qty_window'); // prevent duplicate events
            $(document).on('keydown.item_qty_window', function (e) {

                // Shift + I
                if (e.shiftKey && e.key.toLowerCase() === "i") {

                    e.preventDefault();   // prevent default browser behavior

                    if (value && cur_frm && cur_frm.doctype === "Sales Invoice") {
                        show_item_qty_dialog(cur_frm);
                    }
                }
            });

        });
        





        apply_items_table_height(frm);
        setTimeout(() => {
            unhide_field('project');
            frm.refresh_field('project');
        }, 500);


        

      

    },
    is_pos(frm) {
      setTimeout(() => {
          unhide_field('project');
          frm.refresh_field('project');
      }, 500);
    },

    onload_post_render(frm) {
        apply_items_table_height(frm);
    },
    items_add(frm, cdt, cdn) {
        apply_items_table_height(frm);
    },
    items_remove(frm, cdt, cdn) {
        apply_items_table_height(frm);
    },
});

function set_pos_value(frm) {
    if (frm.doc.custom_payment_mode === "Credit") {
        frm.set_value("is_pos", 0);
    } else {
        frm.set_value("is_pos", 1);
    }
}

function default_branch(frm) {
    frappe.call({
        method: "kenz_trading.events.sales_invoice.get_default_branch",
        args: {
            user: frappe.session.user,
        },
        callback: function (r) {
            if (r.message) {
                frm.set_value("branch", r.message);
            }
        },
    });
}

function set_default_warehouse(frm) {
    if (frm.doc.update_stock && frm.doc.company) {
        frappe.call({
            method: "kenz_trading.events.warehouse.get_default_warehouse",
            args: {
                company: frm.doc.company
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('set_warehouse', r.message);
                    frm.refresh_field('set_warehouse');
                } else {
                    // Clear warehouse if no default found
                    if (!frm.doc.set_warehouse) {
                        frappe.show_alert({
                            message: __('No default warehouse found. Please set a warehouse with "Is Default" checked.'),
                            indicator: 'orange'
                        }, 5);
                    }
                }
            }
        });
    } else if (!frm.doc.update_stock) {
        // Clear warehouse when update_stock is disabled
        frm.set_value('set_warehouse', '');
        frm.refresh_field('set_warehouse');
    }
}

frappe.ui.form.on("Sales Invoice Item", {
    item_code: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        // Fetch Item details for UOM handling only
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Item", name: row.item_code },
            callback: function(r) {
                if (r.message) {
                    let allowed_uoms = (r.message.uoms || []).map(u => u.uom);
                    item_uoms[row.item_code] = allowed_uoms;

                    let grid_row = frm.fields_dict["items"].grid.grid_rows_by_docname[cdn];
                    if (grid_row) {
                        grid_row.get_field("uom").get_query = () => ({
                            filters: [["UOM", "name", "in", allowed_uoms]]
                        });
                    }

                    // Reset UOM if invalid
                    if (row.uom && !allowed_uoms.includes(row.uom)) {
                        frappe.model.set_value(cdt, cdn, "uom", "");
                    }
                }
            }
        });



        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Kenza Settings",
                fieldname: "show_item_variant_table",
                filters: {}
            },
            callback: function (res) {
                // Only continue if checkbox is checked
                if (!res.message || !res.message.show_item_variant_table) {
                    return;
                }

                // YOUR EXISTING FUNCTION — runs only if checkbox is enabled
                frappe.call({
                    method: "kenz_trading.events.sales_invoice.get_last_variant_transactions",
                    args: {
                        customer: frm.doc.customer,
                        item_code: row.item_code
                    },
                    callback: function (r) {

                        if (!r.message || r.message.length === 0) {
                            frm.set_df_property("last_variant_transaction", "options", "");
                            return;
                        }

                        let html = `
                            <div style="max-height:300px; overflow:auto;">
                            <table class="table table-bordered table-sm" style="margin:0;">
                                <thead style="background:#f5f5f5;">
                                    <tr>
                                        <th>Date</th>
                                        <th>Invoice No</th>
                                        <th>Variant</th>
                                        <th>Rate</th>
                                    </tr>
                                </thead>
                                <tbody>`;

                        r.message.forEach(d => {
                            html += `
                                <tr>
                                    <td>${d.submitted_date || ""}</td>
                                    <td>${d.s_invoice_no || ""}</td>
                                    <td>${d.variant_name || ""}</td>
                                    <td>${d.rate || ""}</td>
                                </tr>`;
                        });

                        html += `</tbody></table></div>`;

                        // Set to HTML field
                        frm.set_df_property("last_variant_transaction", "options", html);

                        // Show popup
                        frappe.msgprint({
                            title: __("Last Variant Transactions"),
                            message: html,
                            wide: true
                        });

                    }
                });
            }
        });

        load_item_transaction_details(row.item_code,frm)




        // Build and display stock details
        build_stock_table(frm, row).then(html => {
            frm.doc.custom_stock_details = html;
            frm.refresh_field("custom_stock_details");
        });
    }
});



// ITEM stock above table//////////////


async function build_stock_table(frm, row) {
    let html = "";

    let uoms_res = await frappe.call({
        method: "kenz_trading.events.sales_invoice.get_uoms",
        args: { item_code: row.item_code }
    });

    let uoms = uoms_res.message || [];

    let stock_res = await frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Bin",
            filters: { item_code: row.item_code },
            fields: ["warehouse", "actual_qty"]
        }
    });

    let stock = stock_res.message || [];

    if (uoms.length > 0 || stock.length > 0) {

        html += `
        <h4>Stock Details</h4>
        <table class="table table-bordered" style="width:100%">
            <thead>
                <tr>
                    <th>UOM</th>
                    <th>Conversion Factor</th>
                    <th>Selling Price (${frm.doc.selling_price_list || "Standard Selling"})</th>
                    <th>Buying Price (${frm.doc.buying_price_list || "Standard Buying"})</th>
                    <th>Warehouse</th>
                    <th>Available Qty</th>
                </tr>
            </thead>
            <tbody>`;

        let maxRows = Math.max(uoms.length, stock.length);

        for (let i = 0; i < maxRows; i++) {
            let uom = uoms[i] || {};
            let stockItem = stock[i] || {};

            let selling_rate = "-";
            let buying_rate = "-";

            if (uom.uom) {

                // ------------------ Selling Price ------------------
                let selling_price_res = await frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Item Price",
                        filters: {
                            item_code: row.item_code,
                            uom: uom.uom,
                            price_list: frm.doc.selling_price_list || "Standard Selling"
                        },
                        fieldname: "price_list_rate"
                    }
                });

                selling_rate = (selling_price_res.message && selling_price_res.message.price_list_rate)
                    ? selling_price_res.message.price_list_rate
                    : "-";

                // ------------------ Buying Price ------------------
                let buying_price_res = await frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Item Price",
                        filters: {
                            item_code: row.item_code,
                            uom: uom.uom,
                            price_list: frm.doc.buying_price_list || "Standard Buying"
                        },
                        fieldname: "price_list_rate"
                    }
                });

                buying_rate = (buying_price_res.message && buying_price_res.message.price_list_rate)
                    ? buying_price_res.message.price_list_rate
                    : "-";
            }

            html += `
            <tr>
                <td>${uom.uom || "-"}</td>
                <td>${uom.conversion_factor || "-"}</td>
                <td>${selling_rate}</td>
                <td>${buying_rate}</td>
                <td>${stockItem.warehouse || "-"}</td>
                <td>${stockItem.actual_qty !== undefined ? stockItem.actual_qty : "-"}</td>
            </tr>`;
        }

        html += `</tbody></table>`;
    }

    return html;
}




// SALES CODE/////


function show_last_sales_dialog(frm) {

    let d = new frappe.ui.Dialog({
        title: "Last Sales Details",
        size: "extra-large",
        fields: [



            {
                label: "From Date",
                fieldname: "from_date",
                fieldtype: "Date"
            },

            { fieldtype: "Column Break" },
            
            {
                label: "To Date",
                fieldname: "to_date",
                fieldtype: "Date"
            },

            { fieldtype: "Column Break" },


            {
                label: "Customer",
                fieldname: "customer",
                fieldtype: "Link",
                options: "Customer",
                default: frm.doc.customer
            },

            { fieldtype: "Column Break" },

            {
                label: "Item",
                fieldname: "item_code",
                fieldtype: "Link",
                options: "Item"
            },

            { fieldtype: "Column Break" },

            {
                label: "Warehouse",
                fieldname: "warehouse",
                fieldtype: "Link",
                options: "Warehouse"
            },

            { fieldtype: "Section Break" },

            {
                fieldname: "get_data",
                fieldtype: "Button",
                label: "Get Data"
            },

            {
                fieldname: "results",
                fieldtype: "HTML"
            }
        ]
    });

    d.fields_dict.get_data.onclick = () => {
        let values = d.get_values();

        if (values.from_date && values.to_date && values.from_date > values.to_date) {
            frappe.throw("From Date cannot be greater than To Date");
        }

        frappe.call({
            method: "kenz_trading.events.sales_invoice.get_last_sales_details",
            args: values,
            callback: function (r) {
                if (r.message) {
                    d.fields_dict.results.$wrapper.html(render_sales_table(r.message));
                }
            }
        });
    };

    d.show();
}

function render_sales_table(data) {

    let html = `
        <table class="table table-bordered table-sm">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Invoice No</th>
                    <th>Customer</th>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.forEach(row => {
        html += `
            <tr>
                <td>${frappe.datetime.str_to_user(row.posting_date)}</td>
                <td>${row.name}</td>
                <td>${row.customer}</td>
                <td>${row.item_code}</td>
                <td>${row.qty}</td>
                <td>${format_currency(row.amount)}</td>
            </tr>
        `;
    });

    if (data.length == 0) {
        html += `<tr><td colspan="6" class="text-center">No data found</td></tr>`;
    }

    html += `</tbody></table>`;

    return html;
}





// PURCHASE CODE 


function show_last_purchase_dialog(frm) {

    let d = new frappe.ui.Dialog({
        title: "Last Purchase Details",
        size: "large",
        fields: [


            {
                label: "From Date",
                fieldname: "from_date",
                fieldtype: "Date"
            },

            { fieldtype: "Column Break" },

            {
                label: "To Date",
                fieldname: "to_date",
                fieldtype: "Date"
            },

            { fieldtype: "Column Break" },

            {
                label: "Supplier",
                fieldname: "supplier",
                fieldtype: "Link",
                options: "Supplier"
            },

            { fieldtype: "Column Break" },

            {
                label: "Item",
                fieldname: "item_code",
                fieldtype: "Link",
                options: "Item"
            },

            { fieldtype: "Column Break" },

            {
                label: "Warehouse",
                fieldname: "warehouse",
                fieldtype: "Link",
                options: "Warehouse"
            },

            { fieldtype: "Section Break" },

            {
                fieldname: "get_data",
                fieldtype: "Button",
                label: "Get Data"
            },

            {
                fieldname: "results",
                fieldtype: "HTML"
            }
        ]
    });

    d.fields_dict.get_data.onclick = () => {
        let values = d.get_values();

        frappe.call({
            method: "kenz_trading.events.sales_invoice.get_last_purchase_details",
            args: values,
            callback: function (r) {
                if (r.message) {
                    d.fields_dict.results.$wrapper.html(render_purchase_table(r.message));
                }
            }
        });
    };

    d.show();
}


function render_purchase_table(data) {

    let html = `
        <table class="table table-bordered table-sm">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Invoice No</th>
                    <th>Supplier</th>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.forEach(row => {
        html += `
            <tr>
                <td>${frappe.datetime.str_to_user(row.posting_date)}</td>
                <td>${row.name}</td>
                <td>${row.supplier}</td>
                <td>${row.item_code}</td>
                <td>${row.qty}</td>
                <td>${format_currency(row.amount)}</td>
            </tr>
        `;
    });

    if (!data.length) {
        html += `<tr><td colspan="6" class="text-center">No data found</td></tr>`;
    }

    html += `</tbody></table>`;

    return html;
}




// ITEM qty

function show_item_qty_dialog(frm) {

    let d = new frappe.ui.Dialog({
        title: "Item Stock Details",
        size: "large",

        fields: [
            {
                label: "Item",
                fieldname: "item_code",
                fieldtype: "Link",
                options: "Item",
                reqd: 1
            },

            {
                fieldtype: "Button",
                label: "Get Stock",
                fieldname: "get_stock"
            },

            {
                fieldtype: "HTML",
                fieldname: "stock_html"
            }
        ]
    });

    // ✅ Button click
    d.fields_dict.get_stock.input.onclick = async function () {

        let item_code = d.get_value("item_code");

        if (!item_code) {
            frappe.msgprint("Please select an Item");
            return;
        }

        let res = await frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Bin",
                fields: [
                    "warehouse",
                    "actual_qty",
                    "valuation_rate"
                ],
                filters: {
                    item_code: item_code,
                    actual_qty: [">", 0]
                },
                limit_page_length: 500
            }
        });

        let data = res.message || [];

        if (!data.length) {
            d.fields_dict.stock_html.$wrapper.html("<p><b>No stock available</b></p>");
            return;
        }

        let html = `
            <div style="max-height:350px; overflow:auto;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Warehouse</th>
                            <th style="text-align:right">Cost Price</th>
                            <th style="text-align:right">Balance Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.forEach(row => {
            html += `
                <tr>
                    <td>${row.warehouse}</td>
                    <td style="text-align:right">${format_currency(row.valuation_rate)}</td>
                    <td style="text-align:right">${row.actual_qty}</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        d.fields_dict.stock_html.$wrapper.html(html);
    };

    d.show();
}



// LAST FIVE TRANSACTION//////////////////////

function load_item_transaction_details(item_code, frm) {

    // First check Kenza Settings
    frappe.db.get_single_value(
        "Kenza Settings",
        "show_last_5_sales_and_purchase_transaction"
    ).then(enabled => {

        // If disabled → clear wrapper and stop
        if (!enabled) {
            if (frm.fields_dict.custom_last_five_transaction_details) {
                frm.fields_dict.custom_last_five_transaction_details.$wrapper.empty();
            }
            return;
        }

        // If enabled → run your existing logic
        frappe.call({
            method: 'kenz_trading.events.sales_invoice.get_last_purchase_and_sales',
            args: { item_code: item_code, customer: frm.doc.customer },
            callback: function (r) {

                let purchases = r.message.purchases || [];
                let sales = r.message.sales || [];

                let html = `
                    <style>
                        .transaction-container {
                            display: flex;
                            gap: 10px;
                            width: 100%;
                        }
                        .transaction-box {
                            flex: 1;
                            border: 1px solid #dcdcdc;
                            border-radius: 6px;
                            background-color: #f9f9f9;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                            overflow-y: auto;
                            max-height: 220px;
                            font-size: 12px;
                        }
                        .transaction-box h4 {
                            background: #e8f5e9;
                            color: #15694f;
                            font-size: 13px;
                            padding: 6px 8px;
                            margin: 0;
                            border-bottom: 1px solid #c5e1a5;
                            text-align: center;
                        }
                        table.transaction-table {
                            width: 100%;
                            border-collapse: collapse;
                        }
                        table.transaction-table th,
                        table.transaction-table td {
                            border: 1px solid #ddd;
                            padding: 4px 6px;
                            text-align: left;
                            white-space: nowrap;
                        }
                        table.transaction-table th {
                            background-color: #f1f8e9;
                            color: #2e7d32;
                            font-weight: 600;
                        }
                        td[data-rate] {
                            color: #f02121ff;
                            cursor: pointer;
                            text-align: right;
                        }
                        td[data-rate]:hover {
                            background: #e3f2fd;
                        }
                    </style>

                    <div class="transaction-container">
                        <div class="transaction-box">
                            <h4>Last 5 Purchases</h4>
                            ${get_table_html(purchases, "purchase")}
                        </div>
                        <div class="transaction-box">
                            <h4>Last 5 Sales</h4>
                            ${get_table_html(sales, "sales")}
                        </div>
                    </div>
                `;

                frm.fields_dict.custom_last_five_transaction_details.$wrapper.html(html);
            }
        });

    });

    // Helper function
    function get_table_html(data, type) {

        if (data.length === 0) {
            return '<p style="padding:8px;text-align:center;color:#888;">No records found.</p>';
        }

        let html = `<table class="transaction-table">
            <thead>
                <tr>
                    <th>No</th>
                    <th>Date</th>
                    <th>${type === "purchase" ? "Supplier" : "Customer"}</th>
                    <th>UOM</th>
                    <th>Qty</th>
                    <th>Rate</th>
                </tr>
            </thead>
            <tbody>`;

        data.forEach(d => {
            html += `
                <tr>
                    <td>${type === "purchase" ? d.purchase_invoice_no : d.sales_invoice_no}</td>
                    <td>${frappe.datetime.str_to_user(d.posting_date)}</td>
                    <td>${type === "purchase" ? d.supplier : d.customer}</td>
                    <td>${d.uom}</td>
                    <td style="text-align:right;">${d.qty}</td>
                    <td data-rate="${d.rate}" data-item-code="${item_code}">${d.rate}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        return html;
    }
}
