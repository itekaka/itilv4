frappe.listview_settings["Endpoint Device"] = {
    add_fields: ["status", "hostname", "device_uuid", "os_name", "last_seen", "manufacturer", "model"],
    get_indicator: function(doc) {
        if (doc.status === "ONLINE") return [__("Online"), "green", "status,=,ONLINE"];
        if (doc.status === "WARNING") return [__("Warning"), "orange", "status,=,WARNING"];
        if (doc.status === "OFFLINE") return [__("Offline"), "red", "status,=,OFFLINE"];
        return [__(doc.status), "grey", "status,=," + doc.status];
    }
};
