frappe.provide("frappe.kenz_trading");

// same Select options as ERPNext's Item Barcode child doctype (barcode_type field)
const KENZ_BARCODE_TYPES = [
	"",
	"EAN",
	"UPC-A",
	"CODE-39",
	"EAN-12",
	"EAN-8",
	"GS1",
	"GTIN",
	"ISBN",
	"ISBN-10",
	"ISBN-13",
	"ISSN",
	"JAN",
	"PZN",
	"UPC",
].join("\n");

// Shared Barcode editor: its own "Add Barcode" list (Barcode / Barcode Type / UOM), independent
// of the Price List (item_price_editor.js) - a barcode doesn't need a price and a price doesn't
// need a barcode. Used by both the Item Quick Entry (item_quick_entry.js) and the inline editor
// on transaction item rows (item_child_table_price_editor.js).
frappe.kenz_trading.ItemBarcodeEditor = class ItemBarcodeEditor {
	constructor({ get_stock_uom, get_conversion_factor, get_uom_options, on_change }) {
		this.get_stock_uom = get_stock_uom;
		// looks up the conversion factor already set for a UOM in the Units of Measure list -
		// there's no Conversion Factor field here, a UOM other than the stock one has to be
		// added there first.
		this.get_conversion_factor = get_conversion_factor;
		// restricts the UOM field below to UOMs already in the Units of Measure list, instead of
		// a free Link search across every UOM in the system - picking one that isn't there yet
		// would just fail on save anyway (see save_row()'s "Add ... first" check).
		this.get_uom_options = get_uom_options;
		this.on_change = on_change || (() => {});
		this.barcodes = [];
	}

	make(wrapper) {
		this.wrapper = $(wrapper).empty();
		this.add_button = $(
			`<button class="btn btn-xs btn-default kenz-add-barcode">${__("Add Barcode")}</button>`
		)
			.on("click", () => {
				this.editing_idx = "new";
				this.render();
			})
			.appendTo(this.wrapper);
		this.list_wrapper = $('<div class="kenz-barcode-list mt-2"></div>').appendTo(this.wrapper);
		this.editing_idx = null; // null = none, "new", or an index into this.barcodes
		this.render();
		// resolves once there is nothing left to load - kept for symmetry with ItemPriceEditor,
		// whose own get_item_doc_fields() must not run before ITS load finishes (see its .ready).
		this.ready = Promise.resolve();
	}

	load_from_item(item_doc) {
		const stock_uom = item_doc.stock_uom;
		const conversion_by_uom = {};
		(item_doc.uoms || []).forEach((u) => (conversion_by_uom[u.uom] = u.conversion_factor));
		this.barcodes = (item_doc.barcodes || []).map((b) => {
			const uom = b.uom || stock_uom;
			return {
				barcode: b.barcode,
				barcode_type: b.barcode_type,
				uom,
				conversion_factor: uom === stock_uom ? 1 : conversion_by_uom[uom],
			};
		});
		this.render();
		return this.ready;
	}

	get_fields() {
		return [
			{ label: __("Barcode"), fieldname: "barcode", fieldtype: "Data", reqd: 1 },
			{
				label: __("Barcode Type"),
				fieldname: "barcode_type",
				fieldtype: "Select",
				options: KENZ_BARCODE_TYPES,
			},
			{ fieldname: "stock_uom", fieldtype: "Data", hidden: 1, default: this.get_stock_uom() },
			{
				label: __("UOM"),
				fieldname: "uom",
				fieldtype: "Select",
				options: ["", ...this.get_uom_options()].join("\n"),
				reqd: 1,
			},
		];
	}

	save_row(values, idx) {
		const stock_uom = this.get_stock_uom();
		const conversion_factor = values.uom === stock_uom ? 1 : this.get_conversion_factor(values.uom);
		if (!conversion_factor) {
			frappe.throw(__("Add {0} to Units of Measure first", [values.uom]));
		}
		const barcode = {
			barcode: values.barcode,
			barcode_type: values.barcode_type,
			uom: values.uom,
			conversion_factor,
		};
		const others = this.barcodes.filter((b, i) => i !== idx);
		if (others.some((b) => b.barcode === barcode.barcode)) {
			frappe.throw(__("Barcode {0} is already added", [barcode.barcode]));
		}
		if (others.some((b) => b.uom === barcode.uom && b.conversion_factor !== barcode.conversion_factor)) {
			frappe.throw(__("UOM {0} is already added with a different conversion factor", [barcode.uom]));
		}

		if (idx === "new") this.barcodes.push(barcode);
		else this.barcodes[idx] = barcode;
		this.editing_idx = null;
		this.render();
		this.on_change(this.barcodes);
	}

	render_inline_form(idx) {
		const row = idx === "new" ? {} : this.barcodes[idx];
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

		this.barcodes.forEach((b, idx) => {
			if (this.editing_idx === idx) {
				this.render_inline_form(idx);
				return;
			}
			$(`<div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center">
				<div>
					<div class="bold">${frappe.utils.escape_html(b.barcode)}</div>
					<div class="text-muted small">
						${frappe.utils.escape_html(b.uom)}${
				b.barcode_type ? " · " + frappe.utils.escape_html(b.barcode_type) : ""
			}
					</div>
				</div>
				<div class="d-flex align-items-center">
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
					this.barcodes.splice(idx, 1);
					this.render();
					this.on_change(this.barcodes);
				})
				.appendTo(this.list_wrapper);
		});
	}

	get_item_doc_fields() {
		const stock_uom = this.get_stock_uom();
		const uoms = {};
		this.barcodes
			.filter((b) => b.uom !== stock_uom)
			.forEach((b) => (uoms[b.uom] = b.conversion_factor));
		return {
			uoms: Object.entries(uoms).map(([uom, conversion_factor]) => ({ uom, conversion_factor })),
			barcodes: this.barcodes.map((b) => ({
				barcode: b.barcode,
				barcode_type: b.barcode_type,
				uom: b.uom,
			})),
		};
	}
};
