frappe.provide("frappe.kenz_trading");

// Shared Units of Measure editor: its own "Add Row" list (UOM / Conversion Factor), independent
// of Price List and Barcode. This is the inline-row-editor equivalent of the native "uoms" grid
// in the Item Quick Entry (item_quick_entry.js uses the real Table field there since it's inside
// a Dialog with a doctype-loaded meta; the inline row editor has no such Dialog/Layout to host a
// native grid, so it gets the same card-list treatment as the other two lists).
frappe.kenz_trading.ItemUomEditor = class ItemUomEditor {
	constructor({ get_stock_uom, on_change }) {
		this.get_stock_uom = get_stock_uom;
		this.on_change = on_change || (() => {});
		this.uoms = [];
	}

	make(wrapper) {
		this.wrapper = $(wrapper).empty();
		this.add_button = $(`<button class="btn btn-xs btn-default kenz-add-uom">${__("Add Row")}</button>`)
			.on("click", () => {
				this.editing_idx = "new";
				this.render();
			})
			.appendTo(this.wrapper);
		this.list_wrapper = $('<div class="kenz-uom-list mt-2"></div>').appendTo(this.wrapper);
		this.editing_idx = null; // null = none, "new", or an index into this.uoms
		this.render();
		this.ready = Promise.resolve();
	}

	load_from_item(item_doc) {
		this.uoms = (item_doc.uoms || []).map((u) => ({
			uom: u.uom,
			conversion_factor: u.conversion_factor,
		}));
		this.render();
		return this.ready;
	}

	get_fields() {
		const stock_uom = this.get_stock_uom();
		return [
			{ label: __("UOM"), fieldname: "uom", fieldtype: "Link", options: "UOM", reqd: 1 },
			{
				label: __("Conversion Factor"),
				fieldname: "conversion_factor",
				fieldtype: "Float",
				reqd: 1,
				description: __("1 UOM = ? {0}", [stock_uom]),
			},
		];
	}

	save_row(values, idx) {
		const stock_uom = this.get_stock_uom();
		if (values.uom === stock_uom) {
			frappe.throw(__("{0} is already the item's stock UOM", [stock_uom]));
		}
		const uom_row = { uom: values.uom, conversion_factor: values.conversion_factor };
		const others = this.uoms.filter((u, i) => i !== idx);
		if (others.some((u) => u.uom === uom_row.uom)) {
			frappe.throw(__("UOM {0} is already added", [uom_row.uom]));
		}

		if (idx === "new") this.uoms.push(uom_row);
		else this.uoms[idx] = uom_row;
		this.editing_idx = null;
		this.render();
		this.on_change(this.uoms);
	}

	render_inline_form(idx) {
		const row = idx === "new" ? { conversion_factor: 1 } : this.uoms[idx];
		new frappe.kenz_trading.InlineRowForm({
			fields: this.get_fields(),
			values: row,
			on_save: (values) => this.save_row(values, idx),
			on_cancel: () => {
				this.editing_idx = null;
				this.render();
			},
		}).make(this.list_wrapper);
	}

	render() {
		if (!this.list_wrapper) return;
		this.list_wrapper.empty();
		this.add_button.prop("disabled", this.editing_idx !== null);

		if (this.editing_idx === "new") {
			this.render_inline_form("new");
		}

		this.uoms.forEach((u, idx) => {
			if (this.editing_idx === idx) {
				this.render_inline_form(idx);
				return;
			}
			$(`<div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center">
				<div class="bold">${frappe.utils.escape_html(u.uom)}</div>
				<div class="d-flex align-items-center">
					<span class="bold mr-3">${frappe.utils.escape_html(String(u.conversion_factor))}</span>
					<button class="btn btn-xs btn-default mr-1" data-action="edit">${frappe.utils.icon(
						"edit",
						"xs"
					)}</button>
					<button class="btn btn-xs btn-default" data-action="delete">${frappe.utils.icon(
						"delete",
						"xs"
					)}</button>
				</div>
			</div>`)
				.on("click", "[data-action=edit]", () => {
					this.editing_idx = idx;
					this.render();
				})
				.on("click", "[data-action=delete]", () => {
					this.uoms.splice(idx, 1);
					this.render();
					this.on_change(this.uoms);
				})
				.appendTo(this.list_wrapper);
		});
	}

	get_item_doc_fields() {
		return {
			uoms: this.uoms.map((u) => ({ uom: u.uom, conversion_factor: u.conversion_factor })),
		};
	}
};
