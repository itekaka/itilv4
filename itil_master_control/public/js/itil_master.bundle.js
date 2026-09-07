/* ITIL 4 Master Control Panel - Desk Initialization Script */

console.log("[ITIL Master Control] Initializing Desk Assets & Control Plane v1.0.0...");

frappe.provide("frappe.itil_master_control");

frappe.itil_master_control = {
	init: function () {
		console.log("[ITIL Master Control] Core Suite Loaded Successfully.");
	},

	open_value_stream_mapper: function () {
		frappe.set_route("service-value-stream-mapper");
	}
};

// Fungsi matikan logo
function killFrappeLogo() {
	const logo = document.querySelector('a.navbar-brand.navbar-home');
	if (logo) {
		logo.removeAttribute('href');
		logo.style.pointerEvents = 'none';
		logo.style.cursor = 'default';
		logo.onclick = function (e) {
			e.preventDefault();
			e.stopImmediatePropagation();
			return false;
		};
	}
}

// Jalankan saat Frappe siap
$(document).on("app_ready", function () {
	frappe.itil_master_control.init();

	// Matikan logo
	killFrappeLogo();
	setTimeout(killFrappeLogo, 500);
	setTimeout(killFrappeLogo, 1500);
	setInterval(killFrappeLogo, 2000);
});