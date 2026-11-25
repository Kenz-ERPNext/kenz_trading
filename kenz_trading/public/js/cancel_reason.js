// Asks for a reason before cancelling, when Kenza Settings > Require Cancel Reason is on.
// The server (events/cancel_reason.py) enforces it; this only collects the reason.
(() => {
	const DOCTYPES = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Stock Entry"];
	const API = "kenz_trading.events.cancel_reason.";
	const BULK = "frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs";
	const MIN_LENGTH = 5; // spaces not counted; same as events/cancel_reason.py
	const xcall = frappe.xcall;

	const is_valid = (reason) => (reason || "").replace(/\s/g, "").length >= MIN_LENGTH;

	// resolves true when the cancel may go ahead, false when the user closed the dialog
	const ask_reason = async (doctype, docnames) => {
		if (!DOCTYPES.includes(doctype)) return true;
		if (!(await xcall.call(frappe, API + "is_reason_required", { doctype }))) return true;

		return new Promise((resolve) => {
			let done = false;
			const d = new frappe.ui.Dialog({
				title: __("Cancel Reason"),
				fields: [
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Reason for Cancellation"),
					},
				],
				primary_action_label: __("Confirm Cancel"),
				primary_action: ({ reason }) => {
					if (!is_valid(reason)) return;
					xcall
						.call(frappe, API + "set_cancel_reason", { doctype, docnames, reason })
						.then(() => {
							done = true;
							d.hide();
							resolve(true);
						})
						.catch(() => {}); // the server's message is already shown
				},
				secondary_action_label: __("Close"),
				secondary_action: () => d.hide(),
			});
			d.onhide = () => !done && resolve(false);
			d.show();

			// Confirm stays disabled until the reason is long enough
			const $reason = d.fields_dict.reason.$input;
			const toggle = () => d.get_primary_btn().prop("disabled", !is_valid($reason.val()));
			$reason.on("input", toggle);
			toggle();
		});
	};

	// form: Cancel button
	const savecancel = frappe.ui.form.Form.prototype.savecancel;
	frappe.ui.form.Form.prototype.savecancel = async function (btn, callback, on_error) {
		if (await ask_reason(this.doctype, [this.docname])) {
			return savecancel.call(this, btn, callback, on_error);
		}
		$(btn).prop("disabled", false);
	};

	// list: Actions > Cancel
	frappe.xcall = async function (method, args, ...rest) {
		if (method === BULK && args?.action === "cancel") {
			if (!(await ask_reason(args.doctype, args.docnames))) return [];
		}
		return xcall.call(this, method, args, ...rest);
	};
})();
