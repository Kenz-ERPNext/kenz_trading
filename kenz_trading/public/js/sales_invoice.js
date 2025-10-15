let item_uoms = {};

frappe.ui.form.on("Sales Invoice", { 
    custom_payment_mode: function (frm) {
        set_pos_value(frm);
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
    }
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

        // Build and display stock details
        build_stock_table(frm, row).then(html => {
            frm.doc.custom_stock_details = html;
            frm.refresh_field("custom_stock_details");
        });
    }
});

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
        
        html += `<h4>Stock Details</h4>
            <table class="table table-bordered" style="width:100%">
                <thead>
                    <tr>
                        <th>UOM</th>
                        <th>Conversion Factor</th>
                        <th>Price (${frm.doc.selling_price_list || "Standard Selling"})</th>
                        <th>Warehouse</th>
                        <th>Available Qty</th>
                    </tr>
                </thead>
                <tbody>`;

        let maxRows = Math.max(uoms.length, stock.length);

        for (let i = 0; i < maxRows; i++) {
            let uom = uoms[i] || {};
            let stockItem = stock[i] || {};
            
            let rate = "-";
            if (uom.uom) {
                let price_res = await frappe.call({
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
                rate = (price_res.message && price_res.message.price_list_rate) ? price_res.message.price_list_rate : "-";
            }

            html += `
                <tr>
                    <td>${uom.uom || "-"}</td>
                    <td>${uom.conversion_factor || "-"}</td>
                    <td>${rate}</td>
                    <td>${stockItem.warehouse || "-"}</td>
                    <td>${stockItem.actual_qty !== undefined ? stockItem.actual_qty : "-"}</td>
                </tr>`;
        }

        html += `</tbody></table>`;
    }

    return html;
}