frappe.provide("frappe.ui.form");

// NOTE: this assigns frappe.ui.form.ItemQuickEntryForm - the one global slot Frappe itself checks
// for a custom Item Quick Entry dialog. If kenz_erp is ever installed on the SAME site as
// kenz_trading, whichever app's JS happens to load last silently wins and the other app's version
// of this file never takes effect. Only one of the two should be active on any given site.

// Assigning a plain array of plain objects straight to a doc's child table field (e.g.
// `doc.barcodes = [...]`) works for the initial insert, but those rows never get registered in
// Frappe's `locals` the way frappe.model.add_child() registers them - so if that insert then
// fails server-side (e.g. a barcode checksum error) and the dialog falls back to showing the item
// as a full form, that table's grid can no longer be edited: no rows are "found" to attach clicks
// to. Clearing and rebuilding the table through add_child() keeps every row properly tracked
// either way.
function set_child_table(doc, fieldname, rows) {
	const child_doctype = frappe.get_meta(doc.doctype).fields.find(
		(f) => f.fieldname === fieldname
	).options;
	frappe.model.clear_table(doc, fieldname);
	rows.forEach((row) => {
		const child = frappe.model.add_child(doc, child_doctype, fieldname);
		Object.assign(child, row);
	});
}

// Item quick entry: 3 column layout with item tax template, opening stock, a Price List
// (frappe.kenz_trading.ItemPriceEditor) and a separate Barcode list (frappe.kenz_trading.ItemBarcodeEditor)
// - a barcode doesn't need a price and a price doesn't need a barcode, so they're independent.
// Price list rows become Item Prices in kenz_trading.events.item.sync_price_list_rates, everything
// else is saved on the Item directly.
frappe.ui.form.ItemQuickEntryForm = class ItemQuickEntryForm extends (
	frappe.ui.form.QuickEntryForm
) {
	render_dialog() {
		const df = {};
		this.meta.fields.forEach((f) => (df[f.fieldname] = { ...f }));

		const section = (label, collapsible = 0) => ({
			fieldtype: "Section Break",
			label: label && __(label),
			collapsible,
		});
		const column = () => ({ fieldtype: "Column Break" });
		// kenz_trading's own Item Arabic name field
		const arabic_name_field = df["custom_item_name_arabic"] ? "custom_item_name_arabic" : null;
		// ksa_vat's own "Tax Template" is a bundle of one or more Item Tax Template rows (its
		// on_update hook expands it into the "taxes" table itself, see insert() below) - a strict
		// superset of what the ad-hoc field further down does (pick exactly one Item Tax Template,
		// added as a single row). Showing both would mean filling in tax info twice for the same
		// purpose, so when ksa_vat is installed its field replaces the ad-hoc one instead of
		// sitting alongside it.
		this.uses_ksa_vat_tax_template = !!df["custom_item_tax_template"];
		const layout = [
			section(),
			"item_code",
			"item_name",
			arabic_name_field,
			this.uses_ksa_vat_tax_template
				? "custom_item_tax_template"
				: {
						label: __("Item Tax Template"),
						fieldname: "quick_entry_item_tax_template",
						fieldtype: "Link",
						options: "Item Tax Template",
						reqd: 1,
					},
			column(),
			"item_group",
			"stock_uom",
			column(),
			"is_stock_item",
			"is_fixed_asset",
			"asset_category",
			"opening_stock",
			"valuation_rate",

			section("Units of Measure"),
			{
				// a Table field's grid only shows inline columns when it can look them up via
				// a form (this.frm) - a bare Dialog has none, so they have to be given directly
				...df["uoms"],
				fields: frappe.get_meta("UOM Conversion Detail").fields,
			},

			section("Price List"),
			{
				fieldname: "quick_entry_prices_html",
				fieldtype: "HTML",
			},

			section("Barcode"),
			{
				fieldname: "quick_entry_barcodes_html",
				fieldtype: "HTML",
			},
		];
		// dedupe by fieldname only - a genuinely different field from another app's customization
		// (a different fieldname) still has to show even if its label happens to collide with one
		// already placed above, so it doesn't end up mandatory-but-invisible. e.g. ksa_vat adds its
		// own "custom_item_tax_template" - a Link to ITS OWN "Tax Template" doctype, unrelated to
		// the ad-hoc field below (which maps to the ERPNext "Item Tax Template" child table) - that
		// just happens to carry the exact same label "Item Tax Template". Relabel the collision for
		// disambiguation instead of dropping it.
		const used = new Set(
			layout
				.filter(Boolean)
				.map((f) => (typeof f === "string" ? f : f.fieldname))
				.filter(Boolean)
		);
		const used_labels = new Set(
			layout
				.filter(Boolean)
				.map((f) => (typeof f === "string" ? df[f]?.label : f.label))
				.filter(Boolean)
		);

		// other mandatory / quick entry fields (e.g. from customizations) go at the end of the first section
		const relabeled = {};
		const others = this.mandatory
			.filter((f) => f.fieldname && !used.has(f.fieldname))
			.map((f) => {
				if (!f.label || !used_labels.has(f.label)) return f;
				const label = `${f.label} (${f.module || f.fieldname})`;
				relabeled[f.fieldname] = label;
				return { ...f, label };
			});
		const first_section_end = layout.indexOf("valuation_rate") + 1;
		layout.splice(first_section_end, 0, ...others);

		this.mandatory = layout.map((f) => (typeof f === "string" ? df[f] : f)).filter(Boolean);
		super.render_dialog();

		// a relabel above only takes effect for an ad-hoc field like the ones already in layout -
		// for a real docfield (like ksa_vat's custom_item_tax_template), the Dialog builds its
		// control from Frappe's own canonical field definition rather than the copy handed to it,
		// so the override never took effect on the rendered control; fix it up directly instead.
		Object.entries(relabeled).forEach(([fieldname, label]) => {
			const field = this.dialog.fields_dict[fieldname];
			if (field) {
				field.df.label = label;
				field.refresh();
			}
		});

		// a new Item always ends up with its stock UOM as a Units of Measure row (ERPNext adds it
		// on save if it's missing) - show that row from the start instead of an empty grid. A
		// Table field in a bare Dialog (no frm) keeps its rows on the field itself (df.data), not
		// on doc.uoms - that's only synced from df.data when the dialog's values are read on
		// save - so the row has to be added the same way the grid's own "Add Row" button does it.
		const uom_grid = this.dialog.fields_dict.uoms.grid;
		let default_uom_row = null;
		if (this.doc.__islocal && !uom_grid.get_data().length) {
			const stock_uom = this.dialog.get_value("stock_uom");
			if (stock_uom) {
				uom_grid.add_new_row(null, null, false);
				default_uom_row = uom_grid.get_data().slice(-1)[0];
				Object.assign(default_uom_row, { uom: stock_uom, conversion_factor: 1 });
				uom_grid.refresh();
			}
		}

		// that row only reflects whatever "Default Unit of Measure" was set to at the moment the
		// dialog opened - if the user changes it afterwards, the row doesn't follow along on its
		// own. Keep it in sync: whichever row still has the 1:1 conversion factor (the "this row
		// IS the stock uom" row, whether auto-added above or already there when editing) follows
		// stock_uom as it changes, unless the user has since retyped that row's own UOM by hand.
		const stock_uom_field = this.dialog.fields_dict.stock_uom;
		if (stock_uom_field) {
			let last_stock_uom = this.dialog.get_value("stock_uom");
			stock_uom_field.df.onchange = () => {
				const new_uom = this.dialog.get_value("stock_uom");
				if (!new_uom || new_uom === last_stock_uom) return;
				const row =
					default_uom_row && default_uom_row.uom === last_stock_uom
						? default_uom_row
						: uom_grid.get_data().find((r) => r.uom === last_stock_uom && flt(r.conversion_factor) === 1);
				if (row) {
					row.uom = new_uom;
					default_uom_row = row;
					uom_grid.refresh();
				}
				last_stock_uom = new_uom;
			};
		}

		// looks up the conversion factor for a UOM already added to the Units of Measure grid above
		// - reads the grid's own rows (uom_grid.get_data()), not this.dialog.doc.uoms, since a
		// Table field in a bare Dialog only syncs doc.uoms from the grid when the dialog's values
		// are read on save (see the default-row comment above); before that, doc.uoms is stale, so
		// reading from it here would reject a UOM the user can plainly see in the grid.
		const get_conversion_factor = (uom) => {
			const row = uom_grid.get_data().find((u) => u.uom === uom);
			return row && row.conversion_factor;
		};
		const get_uom_options = () => uom_grid.get_data().map((u) => u.uom).filter(Boolean);

		this.price_editor = new frappe.kenz_trading.ItemPriceEditor({
			get_stock_uom: () => this.dialog.get_value("stock_uom"),
			get_conversion_factor,
			get_uom_options,
		});
		this.price_editor.make(this.dialog.fields_dict.quick_entry_prices_html.wrapper);

		this.barcode_editor = new frappe.kenz_trading.ItemBarcodeEditor({
			get_stock_uom: () => this.dialog.get_value("stock_uom"),
			get_conversion_factor,
			get_uom_options,
		});
		this.barcode_editor.make(this.dialog.fields_dict.quick_entry_barcodes_html.wrapper);

		// Editing an existing Item (e.g. via the list view's edit icon): load its current
		// UOM / Item Price / Barcode rows into the same lists used when adding.
		if (!this.doc.__islocal) {
			this.price_editor.load_from_item(this.doc);
			this.barcode_editor.load_from_item(this.doc);
		}
	}

	// update_doc() copies the dialog's values onto the doc, and for the Units of Measure grid that
	// means plain row objects (no doctype / name, never registered in `locals`). That's harmless for
	// the insert, but "Edit Full Form" opens the doc with those rows as-is, and the full form's grid
	// then throws on "Add Row" (GridRow.refresh reads locals[doctype][name] of a row that was never
	// registered). Rebuild the rows through add_child() so the full form can edit them.
	update_doc() {
		const doc = super.update_doc();
		const rows = doc.uoms || [];
		if (rows.some((row) => !row.name || !locals[row.doctype || ""]?.[row.name])) {
			set_child_table(doc, "uoms", rows.map(({ uom, conversion_factor }) => ({ uom, conversion_factor })));
		}
		return doc;
	}

	insert() {
		if (this.uses_ksa_vat_tax_template) {
			// custom_item_tax_template is a real field, saved as part of the doc as-is; ksa_vat's
			// own on_update hook populates "taxes" from it server-side after insert.
		} else {
			// Item Tax Template is a child table on Item, add the selected template as its row
			const template = this.dialog.get_value("quick_entry_item_tax_template");
			delete this.dialog.doc.quick_entry_item_tax_template;
			set_child_table(this.dialog.doc, "taxes", template ? [{ item_tax_template: template }] : []);
		}

		// wait for the existing Price List / Barcode rows to finish loading (edit mode) before
		// reading them - saving while that fetch is still in flight would read empty lists and
		// wipe out the item's existing rows instead of keeping them
		return Promise.all([this.price_editor.ready, this.barcode_editor.ready]).then(() => {
			const price_fields = this.price_editor.get_item_doc_fields();
			const barcode_fields = this.barcode_editor.get_item_doc_fields();
			// UOM conversions can come from the "Units of Measure" grid itself, from a Price
			// List row, or from a Barcode row - merge all three, the grid's own rows winning
			// on conflict since the user put them there directly.
			const uoms = {};
			[...price_fields.uoms, ...barcode_fields.uoms].forEach(
				(u) => (uoms[u.uom] = u.conversion_factor)
			);
			(this.dialog.doc.uoms || []).forEach((u) => (uoms[u.uom] = u.conversion_factor));

			set_child_table(
				this.dialog.doc,
				"uoms",
				Object.entries(uoms).map(([uom, conversion_factor]) => ({ uom, conversion_factor }))
			);
			set_child_table(this.dialog.doc, "barcodes", barcode_fields.barcodes);
			this.dialog.doc.quick_entry_prices = price_fields.quick_entry_prices;
			return super.insert();
		});
	}
};
