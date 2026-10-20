// Copyright (c) 2026, ITIL Master Team
// ITIL Asset client script

frappe.ui.form.on("ITIL Asset", {
	refresh(frm) {
		if (frm.doc.endpoint_device) {
			frm.add_custom_button(__("Open Endpoint Device"), () => {
				frappe.set_route("Form", "Endpoint Device", frm.doc.endpoint_device);
			});
		}
		if (!frm.is_new() && !frm.doc.endpoint_device) {
			frm.add_custom_button(__("Link Discovered Device"), () => {
				frappe.prompt(
					{
						label: "Endpoint Device",
						fieldname: "endpoint_device",
						fieldtype: "Link",
						options: "Endpoint Device",
						reqd: 1,
					},
					(values) => {
						frm.set_value("endpoint_device", values.endpoint_device);
						frm.save();
					},
					__("Link Endpoint Device")
				);
			});
		}
	},

	endpoint_device(frm) {
		if (!frm.doc.endpoint_device) return;
		frappe.db.get_doc("Endpoint Device", frm.doc.endpoint_device).then((device) => {
			const fields = ["serial_number", "manufacturer", "model", "hostname", "os_name", "os_version"];
			fields.forEach((f) => {
				if (!frm.doc[f] && device[f]) {
					frm.set_value(f, device[f]);
				}
			});
		});
	},
});
