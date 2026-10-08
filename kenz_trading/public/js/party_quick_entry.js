frappe.provide("frappe.ui.form");

// NOTE: this assigns frappe.ui.form.SupplierQuickEntryForm / CustomerQuickEntryForm - the global
// slots Frappe itself checks for a custom Quick Entry dialog. If kenz_erp is ever installed on the
// SAME site as kenz_trading, whichever app's JS happens to load last silently wins and the other
// app's version of this file never takes effect. Only one of the two should be active on any given
// site.

// Supplier / Customer quick entry: extra Contact and Address fields, laid out in 3 columns per
// section, plus kenz_trading's own Arabic name / VAT Registration Number / CR No / Additional IDs
// fields where they exist on the doctype. Contact/Address fieldnames are prefixed (contact_*,
// address_*) so they don't clash with party fields; kenz_trading.events.quick_entry maps them onto
// the Contact and Address that ERPNext creates.
$(() => {
	// party: "supplier" or "customer" (prefix of the <party>_name / <party>_type fields)
	const make_party_quick_entry_form = (party) =>
		class extends frappe.ui.form.ContactAddressQuickEntryForm {
			render_dialog() {
				// Arabic name / VAT registration / CR No - shown only when the field actually
				// exists on this doctype (Customer has all of these; Supplier only has Arabic
				// name today). Some of these are already reqd/allow_in_quick_entry on their own,
				// which puts them in this.mandatory a second time wherever the base class placed
				// them - drop that copy first so they only show up once, at the position chosen
				// below.
				const target_fieldnames = [
					`custom_${party}_name_arabic`,
					"custom_vat_registration_number",
					"custom_cr_no",
				];
				// Supplier has no custom_vat_registration_number to auto-fill it from (see
				// insert() below), so it needs its own Tax ID field instead. Customer already
				// gets tax_id set from the VAT field on save, so showing it there too would just
				// be confusing (it'd silently get overwritten).
				if (party === "supplier") target_fieldnames.push("tax_id");
				this.mandatory = this.mandatory.filter((f) => !target_fieldnames.includes(f.fieldname));

				// Name | Type side by side
				const name_idx = this.mandatory.findIndex((f) => f.fieldname === `${party}_name`);
				if (name_idx !== -1) {
					this.mandatory.splice(name_idx + 1, 0, { fieldtype: "Column Break" });
				}

				const df = {};
				this.meta.fields.forEach((f) => (df[f.fieldname] = f));
				const arabic_name_fieldname = `custom_${party}_name_arabic`;
				const extra_fields = target_fieldnames.map((fieldname) => df[fieldname]).filter(Boolean);

				if (extra_fields.length) {
					const type_idx = this.mandatory.findIndex((f) => f.fieldname === `${party}_type`);
					this.mandatory.splice(type_idx + 1, 0, ...extra_fields);
				}

				super.render_dialog();

				// for a real docfield (like this one), the Dialog builds its control from the
				// doctype's own canonical field definition rather than the copy handed to it
				// above, so the reqd:0 on that copy never took effect - drop it on the actual
				// rendered control and refresh it so the label's "required" star goes away too.
				const arabic_field = this.dialog.fields_dict[arabic_name_fieldname];
				if (arabic_field) {
					arabic_field.df.reqd = 0;
					arabic_field.refresh();
				}
			}

			insert() {
				const additional_ids_df = this.meta.fields.find(
					(f) => f.fieldname === "custom_additional_ids"
				);
				if (additional_ids_df) {
					this.dialog.doc.custom_additional_ids = this.dialog.doc.custom_additional_ids || [];

					// ksa_compliance's own customer.js fills this table with one blank row per ID
					// type the first time it sees it empty on form refresh - but that refresh never
					// fires here (Quick Entry is a bare Dialog, not a real form), so a customer
					// created here would otherwise reach the database with the table still empty.
					// The very next time anyone opens it as a real form, that handler runs for the
					// first time and dirties the page via frm.set_value(), showing "Not Saved" on a
					// record nobody actually changed. Filling the same rows here, up front, avoids
					// that surprise - it's just what the full form would have saved anyway.
					if (!this.dialog.doc.custom_additional_ids.length) {
						[
							["Tax Identification Number", "TIN"],
							["Commercial Registration Number", "CRN"],
							["MOMRAH License", "MOM"],
							["MHRSD License", "MLS"],
							["700 Number", "700"],
							["MISA License", "SAG"],
							["National ID", "NAT"],
							["GCC ID", "GCC"],
							["Iqama", "IQA"],
							["Passport ID", "PAS"],
							["Other ID", "OTH"],
						].forEach(([type_name, type_code]) => {
							const row = frappe.model.add_child(
								this.dialog.doc,
								additional_ids_df.options,
								"custom_additional_ids"
							);
							Object.assign(row, { type_name, type_code });
						});
					}
				}

				// mirror custom_vat_registration_number onto the standard tax_id field, and into
				// the "Additional IDs" TIN row (if that child table is present on this doctype too).
				const vat = this.dialog.get_value("custom_vat_registration_number");
				if (vat) {
					this.dialog.doc.tax_id = vat;

					if (additional_ids_df) {
						let row = this.dialog.doc.custom_additional_ids.find(
							(r) => r.type_code === "TIN"
						);
						if (!row) {
							row = frappe.model.add_child(
								this.dialog.doc,
								additional_ids_df.options,
								"custom_additional_ids"
							);
							row.type_name = "Tax Identification Number";
							row.type_code = "TIN";
						}
						row.value = vat;
					}
				}

				// same sync for the custom_cr_no field: mirror it into the "Additional IDs" CRN
				// row (if that child table is present here too).
				const cr_no = this.dialog.get_value("custom_cr_no");
				if (cr_no && additional_ids_df) {
					let row = this.dialog.doc.custom_additional_ids.find((r) => r.type_code === "CRN");
					if (!row) {
						row = frappe.model.add_child(
							this.dialog.doc,
							additional_ids_df.options,
							"custom_additional_ids"
						);
						row.type_name = "Commercial Registration Number";
						row.type_code = "CRN";
					}
					row.value = cr_no;
				}

				return super.insert();
			}

			get_variant_fields() {
				const erpnext_fields = {};
				super.get_variant_fields().forEach((f) => {
					if (f.fieldname) erpnext_fields[f.fieldname] = f;
				});

				const section = (label, collapsible = 0) => ({
					fieldtype: "Section Break",
					label: __(label),
					collapsible,
				});
				const column = () => ({ fieldtype: "Column Break" });
				const company_only = `eval:doc.${party}_type=='Company'`;

				return [
					section("Primary Address Details"),
					{
						label: __("Address Type"),
						fieldname: "address_type",
						fieldtype: "Select",
						options: [
							"",
							"Billing",
							"Shipping",
							"Office",
							"Personal",
							"Plant",
							"Postal",
							"Shop",
							"Subsidiary",
							"Warehouse",
							"Current",
							"Permanent",
							"Other",
						].join("\n"),
						default: "Billing",
					},
					erpnext_fields.address_line1,
					erpnext_fields.address_line2,
					{
						label: __("Building Number"),
						fieldname: "address_building_number",
						fieldtype: "Data",
					},
					{
						label: __("Area/District"),
						fieldname: "address_area",
						fieldtype: "Data",
					},
					column(),
					erpnext_fields.city,
					{
						label: __("County"),
						fieldname: "address_county",
						fieldtype: "Data",
					},
					erpnext_fields.state,
					erpnext_fields.pincode,
					{ ...(erpnext_fields.country_address || erpnext_fields.country), default: frappe.sys_defaults.country },
					column(),
					{
						label: __("Phone"),
						fieldname: "address_phone",
						fieldtype: "Data",
						options: "Phone",
					},
					{
						label: __("Email Address"),
						fieldname: "address_email",
						fieldtype: "Data",
						options: "Email",
					},
					{
						label: __("Preferred Billing Address"),
						fieldname: "address_is_primary",
						fieldtype: "Check",
						default: 1,
					},
					{
						label: __("Preferred Shipping Address"),
						fieldname: "address_is_shipping",
						fieldtype: "Check",
						default: 1,
					},

					section("Primary Contact Details", 1),
					{
						label: __("Salutation"),
						fieldname: "contact_salutation",
						fieldtype: "Link",
						options: "Salutation",
						depends_on: company_only,
					},
					erpnext_fields.map_to_first_name,
					{
						label: __("Middle Name"),
						fieldname: "contact_middle_name",
						fieldtype: "Data",
						depends_on: company_only,
					},
					erpnext_fields.map_to_last_name,
					column(),
					erpnext_fields.email_address,
					erpnext_fields.mobile_number,
					{
						label: __("Phone"),
						fieldname: "contact_phone",
						fieldtype: "Data",
						options: "Phone",
					},
					column(),
					{
						label: __("Designation"),
						fieldname: "contact_designation",
						fieldtype: "Data",
					},
					{
						label: __("Department"),
						fieldname: "contact_department",
						fieldtype: "Data",
					},
					{
						label: __("Gender"),
						fieldname: "contact_gender",
						fieldtype: "Link",
						options: "Gender",
					},
					// a real Customer field; newer ERPNext no longer lists it in the quick entry variant fields
					erpnext_fields.customer_pos_id ||
						this.meta.fields.find((f) => f.fieldname === "customer_pos_id"),
				].filter(Boolean);
			}
		};

	frappe.ui.form.SupplierQuickEntryForm = make_party_quick_entry_form("supplier");
	frappe.ui.form.CustomerQuickEntryForm = make_party_quick_entry_form("customer");
});
