frappe.ui.form.on("Endpoint Device", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button((_("View Agent Events")), function() {
                frappe.set_route("List", "Endpoint Agent Event", {device: frm.doc.name});
            }, _("Endpoint"));
        }
    }
});
