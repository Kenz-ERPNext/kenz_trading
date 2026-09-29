frappe.pages["barcode-electricals"].on_page_load = function (wrapper) {
	wrapper.barcode_electricals = new kenz_trading.BarcodeElectricals(wrapper);
};

frappe.provide("kenz_trading");

kenz_trading.BarcodeElectricals = class BarcodeElectricals {
	static LABEL_WIDTH_MM = 50;
	static LABEL_HEIGHT_MM = 25;

	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Barcode Printing"),
			single_column: true,
		});
		this.rows = [];
		this.current_barcode = null;

		this.load_jsbarcode();
		this.setup_fields();
		this.setup_actions();
		this.setup_table();
	}

	load_jsbarcode() {
		if (window.JsBarcode) return;
		frappe.require("/assets/kenz_trading/js/lib/JsBarcode.all.min.js");
	}

	setup_fields() {
		this.$fields_wrapper = $('<div class="barcode-electricals-fields"></div>').prependTo(this.page.main);

		this.field_group = new frappe.ui.FieldGroup({
			parent: this.$fields_wrapper,
			fields: [
				{ fieldtype: "Section Break", label: __("Parameters") },
				{
					fieldname: "scan_barcode",
					label: __("Scan Barcode"),
					fieldtype: "Data",
					onchange: () => this.on_barcode_scan(),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "item_code",
					label: __("Product"),
					fieldtype: "Link",
					options: "Item",
					onchange: () => this.on_item_change(),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "item_name",
					label: __("Item Name"),
					fieldtype: "Data",
					read_only: 1,
				},
				{ fieldtype: "Section Break" },
				{
					fieldname: "uom",
					label: __("UOM"),
					fieldtype: "Link",
					options: "UOM",
					onchange: () => this.on_uom_change(),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "count",
					label: __("Count"),
					fieldtype: "Int",
					default: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "rate",
					label: __("Rate (SAR)"),
					fieldtype: "Currency",
				},
				{ fieldtype: "Section Break", hidden: 1 },
				{
					fieldname: "expiry_date",
					label: __("Expiry Date"),
					fieldtype: "Date",
					hidden: 1,
				},
				{ fieldtype: "Column Break", hidden: 1 },
				{
					fieldname: "packing_date",
					label: __("Packing Date"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					hidden: 1,
				},
			],
		});
		this.field_group.make();

		this.barcode_field = this.field_group.get_field("scan_barcode");
		this.item_field = this.field_group.get_field("item_code");
		this.item_name_field = this.field_group.get_field("item_name");
		this.uom_field = this.field_group.get_field("uom");
		this.count_field = this.field_group.get_field("count");
		this.rate_field = this.field_group.get_field("rate");
		this.expiry_field = this.field_group.get_field("expiry_date");
		this.packing_field = this.field_group.get_field("packing_date");
	}

	setup_actions() {
		this.page.set_primary_action(__("Print Labels"), () => this.print_labels(), "printer");
		this.page.set_secondary_action(__("Add to List"), () => this.add_to_list(), "add");
		this.page.add_menu_item(__("Clear List"), () => this.clear_list());
	}

	setup_table() {
		this.$table_wrapper = $(`<div class="barcode-electricals-table" style="margin-top: 20px;"></div>`).appendTo(
			this.page.main
		);
		this.render_table();
	}

	async on_barcode_scan() {
		const search_value = this.barcode_field.get_value();
		if (!search_value) return;

		try {
			const r = await frappe.call({
				method: "erpnext.stock.utils.scan_barcode",
				args: { search_value },
			});
			if (r.message && r.message.item_code) {
				// item_field's own onchange triggers on_item_change; pending_uom lets it
				// use the barcode's exact UOM instead of falling back to stock_uom.
				this.pending_uom = r.message.uom || null;
				await this.item_field.set_value(r.message.item_code);
				this.count_field.set_focus();
			} else {
				frappe.show_alert({ message: __("No item found for this barcode"), indicator: "orange" });
			}
		} catch (e) {
			frappe.show_alert({ message: __("No item found for this barcode"), indicator: "orange" });
		}
	}

	async on_item_change() {
		const item_code = this.item_field.get_value();
		this.current_barcode = null;
		this.current_barcode_type = null;
		if (!item_code) {
			this.item_name_field.set_value("");
			return;
		}

		this.item_doc = await frappe.db.get_doc("Item", item_code);

		const allowed_uoms = [this.item_doc.stock_uom, ...(this.item_doc.uoms || []).map((u) => u.uom)].filter(
			Boolean
		);
		this.uom_field.get_query = () => ({ filters: { name: ["in", allowed_uoms] } });

		const preferred_uom = this.pending_uom;
		this.pending_uom = null;
		if (preferred_uom) {
			this.uom_field.set_value(preferred_uom);
		}
		this.item_name_field.set_value(this.item_doc.item_name || "");
		this.rate_field.set_value(this.item_doc.standard_rate || 0);
		this.expiry_field.set_value(this.item_doc.end_of_life || "");

		await this.on_uom_change();
	}

	async on_uom_change() {
		const item_code = this.item_field.get_value();
		const uom = this.uom_field.get_value();
		this.current_barcode = null;
		this.current_barcode_type = null;

		const barcodes = (this.item_doc && this.item_doc.barcodes) || [];
		if (barcodes.length) {
			const match = barcodes.find((b) => b.uom === uom) || barcodes.find((b) => !b.uom) || barcodes[0];
			this.current_barcode = match.barcode;
			this.current_barcode_type = match.barcode_type || "";
		}

		if (!item_code) return;
		const r = await frappe.call({
			method: "kenz_trading.kenz_trading.page.barcode_electricals.barcode_electricals.get_item_rate",
			args: { item_code, uom },
		});
		if (r.message !== undefined && r.message !== null) {
			this.rate_field.set_value(r.message);
		}
	}

	add_to_list() {
		const item_code = this.item_field.get_value();
		const uom = this.uom_field.get_value();
		const count = cint(this.count_field.get_value());

		if (!item_code) {
			frappe.show_alert({ message: __("Select a Product"), indicator: "red" });
			return;
		}
		if (!uom) {
			frappe.show_alert({ message: __("Select a UOM"), indicator: "red" });
			return;
		}
		if (!count || count < 1) {
			frappe.show_alert({ message: __("Count must be at least 1"), indicator: "red" });
			return;
		}
		if (!this.current_barcode) {
			frappe.show_alert({
				message: __("No barcode found on {0} for UOM {1}", [item_code, uom]),
				indicator: "orange",
			});
			return;
		}

		this.rows.push({
			item_code,
			item_name: this.item_doc ? this.item_doc.item_name : item_code,
			uom,
			count,
			rate: flt(this.rate_field.get_value()),
			expiry_date: this.expiry_field.get_value(),
			packing_date: this.packing_field.get_value(),
			barcode: this.current_barcode,
			barcode_type: this.current_barcode_type,
		});

		this.render_table();

		this.reset_fields();
	}

	reset_fields() {
		this.current_barcode = null;
		this.current_barcode_type = null;
		this.item_doc = null;
		this.barcode_field.set_value("");
		this.item_field.set_value("");
		this.uom_field.set_value("");
		this.count_field.set_value(1);
		this.rate_field.set_value("");
		this.expiry_field.set_value("");
		this.packing_field.set_value("");
	}

	remove_row(idx) {
		this.rows.splice(idx, 1);
		this.render_table();
	}

	clear_list() {
		this.rows = [];
		this.render_table();
	}

	render_table() {
		if (!this.rows.length) {
			this.$table_wrapper.html(`<p class="text-muted">${__("No items added yet.")}</p>`);
			return;
		}

		let rows_html = this.rows
			.map(
				(row, idx) => `
			<tr>
				<td>${frappe.utils.escape_html(row.item_code)}</td>
				<td>${frappe.utils.escape_html(row.item_name || "")}</td>
				<td>${frappe.utils.escape_html(row.uom)}</td>
				<td><input type="number" class="form-control input-sm row-count" data-idx="${idx}" min="1" value="${row.count}" style="width: 70px;"></td>
				<td>${format_currency(row.rate)}</td>
				<td><input type="date" class="form-control input-sm row-expiry" data-idx="${idx}" value="${row.expiry_date || ""}" style="width: 140px;"></td>
				<td><input type="date" class="form-control input-sm row-packing" data-idx="${idx}" value="${row.packing_date || ""}" style="width: 140px;"></td>
				<td>${frappe.utils.escape_html(row.barcode)}</td>
				<td><a href="#" class="text-danger" data-idx="${idx}">${__("Remove")}</a></td>
			</tr>`
			)
			.join("");

		this.$table_wrapper.html(`
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${__("Product")}</th>
						<th>${__("Item Name")}</th>
						<th>${__("UOM")}</th>
						<th>${__("Count")}</th>
						<th>${__("Rate")}</th>
						<th>${__("Expiry Date")}</th>
						<th>${__("Packing Date")}</th>
						<th>${__("Barcode")}</th>
						<th></th>
					</tr>
				</thead>
				<tbody>${rows_html}</tbody>
			</table>
		`);

		this.$table_wrapper.find("a[data-idx]").on("click", (e) => {
			e.preventDefault();
			this.remove_row(cint($(e.currentTarget).attr("data-idx")));
		});

		this.$table_wrapper.find(".row-count").on("change", (e) => {
			const idx = cint($(e.currentTarget).attr("data-idx"));
			const val = cint($(e.currentTarget).val());
			this.rows[idx].count = val > 0 ? val : 1;
		});

		this.$table_wrapper.find(".row-expiry").on("change", (e) => {
			const idx = cint($(e.currentTarget).attr("data-idx"));
			this.rows[idx].expiry_date = $(e.currentTarget).val();
		});

		this.$table_wrapper.find(".row-packing").on("change", (e) => {
			const idx = cint($(e.currentTarget).attr("data-idx"));
			this.rows[idx].packing_date = $(e.currentTarget).val();
		});
	}

	// Maps ERPNext's Item Barcode "Barcode Type" options to the symbologies
	// JsBarcode actually ships (see JsBarcode.all.min.js). Types with no
	// matching symbology (GS1, GTIN, ISBN variants, ISSN, JAN, PZN) fall back
	// to a close equivalent, and CODE128 is the overall default. "EAN" (and
	// no barcode_type at all) isn't a symbology on its own - it's resolved
	// to EAN8/EAN13 by digit count in render_barcode_svg.
	static BARCODE_TYPE_MAP = {
		"UPC-A": "UPC",
		"UPC": "UPC",
		"CODE-39": "CODE39",
		"EAN-12": "UPC",
		"EAN-8": "EAN8",
		"GS1": "CODE128",
		"GTIN": "EAN13",
		"ISBN": "EAN13",
		"ISBN-10": "EAN13",
		"ISBN-13": "EAN13",
		"ISSN": "EAN13",
		"JAN": "EAN13",
		"PZN": "CODE39",
	};

	render_barcode_svg(value, barcode_type) {
	const svg = document.createElementNS(
		"http://www.w3.org/2000/svg",
		"svg"
	);

	let format = BarcodeElectricals.BARCODE_TYPE_MAP[barcode_type];
	if (!format) {
		const digits = String(value || "").replace(/\D/g, "");
		if (digits.length === 8) format = "EAN8";
		else if (digits.length === 12 || digits.length === 13) format = "EAN13";
		else format = "CODE128";
	}

	const options = {
		displayValue: true,

		// Barcode number/text
		text: value,
		textAlign: "center",
		textPosition: "bottom",
		textMargin: 2,

		// Barcode
		fontSize: 10,
		height: 34,
		marginTop: 0,
		marginRight: 0,
		marginBottom: 4,
		marginLeft: 0,

		// Keep barcode itself centered
		width: 2,
	};

	try {
		JsBarcode(svg, value, { ...options, format });
	} catch (e) {
		// value doesn't fit the strict rules of its symbology (e.g. wrong
		// digit count for EAN13/UPC) - CODE128 encodes any string.
		JsBarcode(svg, value, { ...options, format: "CODE128" });
	}

	return svg.outerHTML;
}

	print_labels() {
		// Selecting an item/barcode and hitting Print directly (without an explicit
		// "Add to List" click) should just print that one item.
		if (!this.rows.length && this.item_field.get_value()) {
			this.add_to_list();
		}

		if (!this.rows.length) {
			frappe.show_alert({ message: __("Select a Product (or scan a barcode) first"), indicator: "red" });
			return;
		}
		if (!window.JsBarcode) {
			frappe.show_alert({ message: __("Barcode library still loading, try again in a moment") });
			this.load_jsbarcode();
			return;
		}

		const width = BarcodeElectricals.LABEL_WIDTH_MM;
		const height = BarcodeElectricals.LABEL_HEIGHT_MM;
		const company = frappe.defaults.get_default("company") || "";

		let labels_html = "";
		this.rows.forEach((row) => {
			const svg = this.render_barcode_svg(row.barcode, row.barcode_type);
			for (let i = 0; i < row.count; i++) {
				labels_html += `
					<div class="label">
						${company ? `<div class="company-name">${frappe.utils.escape_html(company)}</div>` : ""}
						<div class="item-name">${frappe.utils.escape_html(row.item_name || row.item_code)}</div>
						${svg}
						<div class="price">${__("SAR")} ${flt(row.rate).toFixed(2)} / ${frappe.utils.escape_html(row.uom)}</div>
					</div>`;
			}
		});

		const html = `
			<!DOCTYPE html>
			<html>
			<head>
				<title>${__("Barcode Labels")}</title>
				<style>
					@page { size: ${width}mm ${height}mm; margin: 0; }
					* { box-sizing: border-box; }
					body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
					.label {
						width: ${width}mm;
						height: ${height}mm;
						padding: 3mm 2.5mm 2mm 2.5mm;
						display: flex;
						flex-direction: column;
						align-items: center;
						justify-content: center;
						gap: 0.3mm;
						text-align: center;
						page-break-after: always;
						overflow: hidden;
					}
					.label .company-name {
						font-family: Arial, sans-serif;
						font-size: 1.8mm;
						font-weight: bold;
						line-height: 1;
						max-width: 100%;
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
					}
					.label .item-name {
						font-family: Arial, sans-serif;
						font-size: 2.2mm;
						font-weight: bold;
						line-height: 1;
						max-width: 100%;
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
					}
					.label svg {
	display: block;
	width: 88%;
	height: auto;
	max-height: 10mm;
	margin: 0 auto 0.4mm auto;
}
					.label .price {
						font-family: Arial, sans-serif;
						font-size: 2.6mm;
						font-weight: bold;
						line-height: 1;
					}
				</style>
			</head>
			<body>
				${labels_html}
			</body>
			</html>
		`;

		const print_window = window.open("", "_blank");
		print_window.document.write(html);
		print_window.document.close();
		print_window.focus();

		this.reset_fields();

		setTimeout(() => {
			print_window.print();
		}, 300);
	}
};