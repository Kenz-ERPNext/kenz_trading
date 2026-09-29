frappe.provide("frappe.kenz_trading");

// Shared UOM / Price List editor: the "Add Price" grid used by both the Item Quick Entry
// (item_quick_entry.js) and the inline editor on transaction item rows
// (item_child_table_price_editor.js), so editing an item's prices looks and behaves the same
// everywhere. Barcodes are a separate list - see item_barcode_editor.js.
frappe.kenz_trading.ItemPriceEditor = class ItemPriceEditor {
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
		this.prices = [];
	}

	make(wrapper) {
		this.wrapper = $(wrapper).empty();
		this.add_button = $(`<button class="btn btn-xs btn-default kenz-add-price">${__("Add Price")}</button>`)
			.on("click", () => {
				this.editing_idx = "new";
				this.render();
			})
			.appendTo(this.wrapper);
		this.list_wrapper = $('<div class="kenz-price-list mt-2"></div>').appendTo(this.wrapper);
		this.editing_idx = null; // null = none, "new", or an index into this.prices
		this.render();
		// resolves once there is nothing left to load - get_item_doc_fields() must not run before
		// this, or it would save an empty/partial list and wipe out the item's existing rows
		this.ready = Promise.resolve();
	}

	load_from_item(item_doc) {
		const stock_uom = item_doc.stock_uom;
		const conversion_by_uom = {};
		(item_doc.uoms || []).forEach((u) => (conversion_by_uom[u.uom] = u.conversion_factor));

		this.add_button.prop("disabled", true);
		this.ready = frappe.db
			.get_list("Item Price", {
				filters: { item_code: item_doc.name },
				fields: ["uom", "price_list", "price_list_rate"],
				limit: 0,
			})
			.then((rows) => {
				this.prices = rows.map((row) => {
					const uom = row.uom || stock_uom;
					return {
						uom,
						conversion_factor: uom === stock_uom ? 1 : conversion_by_uom[uom],
						price_list: row.price_list,
						rate: row.price_list_rate,
					};
				});
				this.render();
			})
			.finally(() => this.add_button.prop("disabled", false));
		return this.ready;
	}

	get_fields() {
		return [
			{ fieldname: "stock_uom", fieldtype: "Data", hidden: 1, default: this.get_stock_uom() },
			{
				label: __("UOM"),
				fieldname: "uom",
				fieldtype: "Select",
				options: ["", ...this.get_uom_options()].join("\n"),
				reqd: 1,
			},
			{
				label: __("Price List"),
				fieldname: "price_list",
				fieldtype: "Link",
				options: "Price List",
				reqd: 1,
				get_query: () => ({ filters: { enabled: 1 } }),
			},
			{ label: __("Rate"), fieldname: "rate", fieldtype: "Currency", reqd: 1 },
		];
	}

	save_row(values, idx) {
		const stock_uom = this.get_stock_uom();
		const conversion_factor = values.uom === stock_uom ? 1 : this.get_conversion_factor(values.uom);
		if (!conversion_factor) {
			frappe.throw(__("Add {0} to Units of Measure first", [values.uom]));
		}
		const price = {
			uom: values.uom,
			conversion_factor,
			price_list: values.price_list,
			rate: values.rate,
		};
		const others = this.prices.filter((p, i) => i !== idx);
		if (others.some((p) => p.uom === price.uom && p.price_list === price.price_list)) {
			frappe.throw(__("{0} price for {1} is already added", [price.price_list, price.uom]));
		}
		if (others.some((p) => p.uom === price.uom && p.conversion_factor !== price.conversion_factor)) {
			frappe.throw(__("UOM {0} is already added with a different conversion factor", [price.uom]));
		}

		if (idx === "new") this.prices.push(price);
		else this.prices[idx] = price;
		this.editing_idx = null;
		this.render();
		this.on_change(this.prices);
	}

	render_inline_form(idx) {
		const row = idx === "new" ? {} : this.prices[idx];
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

		this.prices.forEach((p, idx) => {
			if (this.editing_idx === idx) {
				this.render_inline_form(idx);
				return;
			}
			$(`<div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center">
				<div>
					<div class="bold">${frappe.utils.escape_html(p.price_list)}</div>
					<div class="text-muted small">${frappe.utils.escape_html(p.uom)}</div>
				</div>
				<div class="d-flex align-items-center">
					<span class="bold mr-3">${format_currency(p.rate)}</span>
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
					this.prices.splice(idx, 1);
					this.render();
					this.on_change(this.prices);
				})
				.appendTo(this.list_wrapper);
		});
	}

	get_item_doc_fields() {
		const stock_uom = this.get_stock_uom();
		const uoms = {};
		this.prices.filter((p) => p.uom !== stock_uom).forEach((p) => (uoms[p.uom] = p.conversion_factor));
		return {
			uoms: Object.entries(uoms).map(([uom, conversion_factor]) => ({ uom, conversion_factor })),
			quick_entry_prices: JSON.stringify(
				this.prices.map((p) => ({ uom: p.uom, price_list: p.price_list, rate: p.rate }))
			),
		};
	}
};
