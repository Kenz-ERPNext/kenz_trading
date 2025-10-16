frappe.ui.form.on('Item', {
  refresh(frm) {
    frappe.db.get_value('Branch', { custom_is_default: 1 }, 'name')
      .then(r => {
        if (r && r.message && r.message.name) {
          frm.clear_table('custom_branches');
          let row = frm.add_child('custom_branches');
          row.branch = r.message.name;
          frm.refresh_field('custom_branches');
        }
      });
    frappe.db.get_value('Item Tax Template', { custom_is_default: 1 }, 'name')
    .then(r => {
      if (r && r.message && r.message.name) {
        frm.clear_table('taxes');
        let row = frm.add_child('taxes');
        row.item_tax_template = r.message.name;
        frm.refresh_field('taxes');
      }
    });
  }
});
