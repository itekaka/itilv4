frappe.listview_settings["Endpoint Agent Event"] = {
    add_fields: ["event_type", "device", "created_at"],
    get_indicator: function(doc) {
        const m = {"AGENT_REGISTERED":"green","AGENT_HEARTBEAT":"blue","INVENTORY_RECEIVED":"purple","INVENTORY_CHANGED":"orange","AUTH_FAILURE":"red","AGENT_REVOKED":"grey"};
        return [__(doc.event_type), m[doc.event_type] || "grey", "event_type,=," + doc.event_type];
    }
};
