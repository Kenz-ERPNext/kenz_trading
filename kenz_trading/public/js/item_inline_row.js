frappe.provide("frappe.kenz_trading");

// A row of frappe.ui.form.make_control() inputs rendered directly in a list (no popup dialog).
// Used by ItemUomEditor / ItemPriceEditor / ItemBarcodeEditor so adding or editing a row happens
// in place instead of in a dialog - same fields, same section, just no modal. Saves itself once
// every required field has a value AND focus leaves the row entirely, so filling in the row is
// normally the only step; the check/x buttons stay as a manual fallback (e.g. to save with an
// optional field left blank, or to cancel). It has to watch the whole row rather than each field's
// blur - blurring one required field to reach an optional one (e.g. Barcode to Barcode Type) would
// otherwise count as "leaving" and save the row before that optional field is even reached.
frappe.kenz_trading.InlineRowForm = class InlineRowForm {
	constructor({ fields, values = {}, on_save, on_cancel }) {
		this.fields = fields;
		this.values = values;
		this.on_save = on_save;
		this.on_cancel = on_cancel || (() => {});
		this.controls = {};
	}

	make(wrapper) {
		this.wrapper = $('<div class="border rounded p-2 mb-2 kenz-inline-row"></div>').appendTo(wrapper);
		const fields_row = $('<div class="d-flex flex-wrap" style="gap: 10px;"></div>').appendTo(
			this.wrapper
		);

		this.fields
			.filter((df) => !df.hidden)
			.forEach((df, i) => {
				const col = $('<div style="min-width: 140px; flex: 1;"></div>').appendTo(fields_row);
				const control = frappe.ui.form.make_control({
					df,
					parent: col.get(0),
					render_input: true,
				});
				control.refresh();
				if (this.values[df.fieldname] !== undefined) {
					control.set_value(this.values[df.fieldname]);
				}
				this.controls[df.fieldname] = control;
				if (i === 0) {
					setTimeout(() => control.set_focus && control.set_focus(), 50);
				}
			});

		// fires once when focus moves to anything outside this row - not on every field-to-field
		// blur within it (see the class comment for why that distinction matters here)
		this.wrapper.on("focusout", (e) => {
			setTimeout(() => {
				if (!this.wrapper || this.wrapper.find(":focus").length) return;
				this.maybe_auto_save();
			}, 0);
		});

		const actions = $('<div class="d-flex mt-2" style="gap: 6px;"></div>').appendTo(this.wrapper);
		$(
			`<button class="btn btn-xs btn-primary" title="${__("Save")}">${frappe.utils.icon(
				"check",
				"xs"
			)}</button>`
		)
			.on("click", () => this.save())
			.appendTo(actions);
		$(
			`<button class="btn btn-xs btn-default" title="${__("Cancel")}">${frappe.utils.icon(
				"close",
				"xs"
			)}</button>`
		)
			.on("click", () => this.on_cancel())
			.appendTo(actions);
	}

	maybe_auto_save() {
		if (this.saved) return;
		const complete = this.fields
			.filter((df) => df.reqd && !df.hidden)
			.every((df) => this.controls[df.fieldname] && this.controls[df.fieldname].get_value());
		if (complete) this.save();
	}

	save() {
		if (this.saved) return;
		const values = {};
		for (const df of this.fields) {
			values[df.fieldname] = df.hidden ? df.default : this.controls[df.fieldname].get_value();
			if (df.reqd && !values[df.fieldname]) {
				frappe.show_alert({ message: __("{0} is required", [__(df.label)]), indicator: "red" });
				return;
			}
		}
		// on_save may call frappe.throw() to reject invalid values - that leaves this row open
		// (matching how the old "Add"/"Update" dialog button used to behave), so only latch
		// "saved" once it actually goes through, otherwise the fix-and-retry would be stuck.
		this.saved = true;
		try {
			this.on_save(values);
		} catch (e) {
			this.saved = false;
			throw e;
		}
	}
};
