frappe.ui.form.on('Item', {
  refresh(frm) {
    // frappe.msgprint("hii")
  },



  async onload(frm) {
    set_branch_filter(frm); 
    if (frm.is_new()) {

      // --- 1️⃣ Default Branch ---
      if (!frm.doc.custom_branches?.length) {
        const branchRes = await frappe.db.get_value('Branch', { custom_is_default: 1 }, 'name');
        if (branchRes.message && branchRes.message.name) {
          let row = frm.add_child('custom_branches');
          row.branch = branchRes.message.name;
          frm.refresh_field('custom_branches');
        }
      }

      // --- 2️⃣ Default Tax Template & Category ---
      if (!frm.doc.taxes?.length) {
        const [taxTemplateRes, taxCategoryRes] = await Promise.all([
          frappe.db.get_value('Item Tax Template', { custom_is_default: 1 }, 'name'),
          frappe.db.get_value('Tax Category', { custom_is_default: 1 }, 'name')
        ]);

        const tax_template = taxTemplateRes?.message?.name;
        const tax_category = taxCategoryRes?.message?.name;

        if (tax_template || tax_category) {
          let row = frm.add_child('taxes');
          if (tax_template) row.item_tax_template = tax_template;
          if (tax_category) row.tax_category = tax_category;
          frm.refresh_field('taxes');
        }
      }

      // --- 3️⃣ Auto Item Code from Kenza Settings ---
      const kenza_settings = await frappe.db.get_doc('Kenza Settings');

      if (kenza_settings?.default_item_code && kenza_settings?.item_code_series) {
        const prefix = kenza_settings.item_code_series;

        // Fetch last created item with same prefix
        const last_item = await frappe.db.get_list('Item', {
          fields: ['item_code'],
          filters: [['item_code', 'like', `${prefix}%`]],
          order_by: 'creation desc',
          limit: 1
        });

        let next_number = 1;
        if (last_item?.length && last_item[0].item_code) {
          const last_code = last_item[0].item_code;
          const match = last_code.match(/\d+$/);
          if (match) {
            next_number = parseInt(match[0]) + 1;
          }
        }

        const next_code = `${prefix}${String(next_number).padStart(3, '0')}`;

        // Set item_code only
        frm.set_value('item_code', next_code);

        // Force item_name to stay blank
        frappe.after_ajax(() => {
          frm.set_value('item_name', '');
        });
      }
    }
  },

  // --- 4️⃣ Stop auto copy behavior entirely ---
  item_code: function(frm) {
    if (frm.is_new()) {
      // Prevent Frappe’s default linking of item_code → item_name
      if (frm.doc.item_name === frm.doc.item_code) {
        frm.set_value('item_name', '');
      }
    }
  },
});
 


