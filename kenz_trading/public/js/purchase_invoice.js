// frappe.ui.form.on('Purchase Invoice', {
//     onload(frm) {
//         if (frm.doc.update_stock) {
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Warehouse",
//                     filters: { "custom_is_default": 1},
//                     fields: ["name"],
//                     limit_page_length: 1
//                 },
//                 callback: function(r) {
//                     if (r.message && r.message.length > 0) {
//                         frm.set_value('set_warehouse', r.message[0].name);
//                         frm.refresh_field('set_warehouse');
//                         frappe.show_alert({
//                             message: 'Warehouse set to: ' + r.message.name,
//                             indicator: 'green'
//                         });
//                     } else {
//                         frappe.msgprint(__('Warehouse "Stores - A" not found.'));
//                     }
//                 }
//             });
//         } else {
//             frm.set_value('set_warehouse', '');
//             frm.refresh_field('set_warehouse');
//         }
//     }
// });




frappe.ui.form.on('Purchase Invoice', {
    onload(frm) {
        if (frm.doc.docstatus !== 0) {
            return;
        }

        if (frm.doc.update_stock) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Warehouse",
                    filters: {
                        custom_is_default: 1
                    },
                    fields: ["name"],
                    limit_page_length: 1
                },
                callback(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value(
                            'set_warehouse',
                            r.message[0].name
                        );
                    } else {
                        frappe.msgprint(
                            __('No default warehouse found.')
                        );
                    }
                }
            });
        } else {
            frm.set_value('set_warehouse', '');
        }

       if (frm.doc.is_paid) {
            frm.set_value(
                'paid_amount',
                frm.doc.rounded_total || 0
            );
        }
    }
});


// Live Tax Rate / Tax Amount / Total Amount on item rows (same logic as the
// server-side regional update_itemised_tax_data + fix_inclusive_tax_rounding)
frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        if (frm.cscript._kenz_item_tax_hooked) {
            return;
        }
        const original = frm.cscript._calculate_taxes_and_totals;
        frm.cscript._calculate_taxes_and_totals = function (...args) {
            const result = original.apply(this, args);
            update_item_tax_fields(frm);
            return result;
        };
        frm.cscript._kenz_item_tax_hooked = true;
    }
});

function update_item_tax_fields(frm) {
    if (!frappe.meta.has_field(frm.doc.doctype + ' Item', 'tax_rate')) {
        return;
    }

    const taxes = frm.doc.taxes || [];
    const skip_inclusive_fix = taxes.some(
        (tax) => tax.add_deduct_tax === 'Deduct' || tax.category === 'Valuation'
    );
    const all_inclusive = taxes.length
        && !skip_inclusive_fix
        && taxes.every((tax) => cint(tax.included_in_print_rate));

    (frm.doc.items || []).forEach((row) => {
        const key = row.item_code || row.item_name;
        let tax_rate = 0.0;
        let tax_amount = 0.0;

        taxes.forEach((tax) => {
            if (tax.category === 'Valuation') {
                return;
            }
            let detail = tax.item_wise_tax_detail || {};
            if (typeof detail === 'string') {
                detail = detail ? JSON.parse(detail) : {};
            }
            if (!detail[key]) {
                return;
            }
            const rate = flt(Array.isArray(detail[key]) ? detail[key][0] : detail[key]);
            tax_amount += flt((row.net_amount * rate) / 100, precision('tax_amount', row));
            tax_rate += rate;
        });

        row.tax_rate = flt(tax_rate, precision('tax_rate', row));
        row.tax_amount = flt(tax_amount, precision('tax_amount', row));
        row.total_amount = flt(row.net_amount + row.tax_amount, precision('total_amount', row));

        if (all_inclusive && row.total_amount !== flt(row.amount, precision('total_amount', row))) {
            row.tax_amount = flt(row.amount - row.net_amount, precision('tax_amount', row));
            row.total_amount = flt(row.net_amount + row.tax_amount, precision('total_amount', row));
        }
    });
}
