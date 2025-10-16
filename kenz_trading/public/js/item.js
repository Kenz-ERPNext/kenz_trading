frappe.ui.form.on('Item', {
  onload(frm) {
    if (frm.is_new()) {
      if (!frm.doc.custom_branches?.length) {
        const branchRes = await frappe.db.get_value('Branch', { custom_is_default: 1 }, 'name');
        if (branchRes.message && branchRes.message.name) {
          let row = frm.add_child('custom_branches');
          row.branch = branchRes.message.name;
          frm.refresh_field('custom_branches');
        }
      }
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
    }
  }
});
