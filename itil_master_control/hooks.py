app_name = "itil_master_control"
app_title = "ITIL 4 Master Control Panel"
app_publisher = "ITIL Master Team"
app_description = "Enterprise ITIL 4 ITSM Control Plane with Service Value Stream Mapper"
app_email = "dev@itilmaster.local"
app_license = "mit"


# Default application landing page
home_page = "itil-master-dashboard"

# Includes in Desk
app_include_css = "itil_master.bundle.css"
app_include_js = "itil_master.bundle.js"

# Desktop / Workspace Notifications
doctype_js = {
	"ITIL Incident": "public/js/itil_incident.js",
	"ITIL Problem": "public/js/itil_problem.js",
	"ITIL Change Request": "public/js/itil_change_request.js"
}

# Scheduled Tasks for Practice Health Score Recalculation
scheduler_events = {
	"cron": {
		"*/15 * * * *": [
			"itil_master_control.api.recalculate_all_practice_health"
		]
	},
	"daily": [
		"itil_master_control.api.generate_daily_health_snapshots"
	]
}

# DocType Event Hooks — Hybrid realtime sync untuk semua practice
_OPERATIONAL_EVENTS = {
	"after_insert": "itil_master_control.api.on_operational_doc_change",
	"on_update": "itil_master_control.api.on_operational_doc_change",
	"after_delete": "itil_master_control.api.on_operational_doc_change",
}

doc_events = {
	# --- Special handlers (ada logic tambahan auto-link) ---
	"ITIL Incident": {
		"after_insert": "itil_master_control.api.on_incident_update",
		"on_update": "itil_master_control.api.on_incident_update",
		"after_delete": "itil_master_control.api.on_operational_doc_change",
	},
	"ITIL Problem": {
		"after_insert": "itil_master_control.api.on_problem_update",
		"on_update": "itil_master_control.api.on_problem_update",
		"after_delete": "itil_master_control.api.on_operational_doc_change",
	},
	"ITIL Change Request": {
		"after_insert": "itil_master_control.api.on_change_update",
		"on_update": "itil_master_control.api.on_change_update",
		"after_delete": "itil_master_control.api.on_operational_doc_change",
	},
	"ITIL Deployment Log": {
		"on_submit": "itil_master_control.api.on_deployment_submit",
		"on_update": "itil_master_control.api.on_deployment_submit",
		"after_delete": "itil_master_control.api.on_operational_doc_change",
	},

	# --- Generic realtime untuk practice lainnya ---
	"ITIL Project": _OPERATIONAL_EVENTS,
	"ITIL Measurement Report": _OPERATIONAL_EVENTS,
	"ITIL Risk Register": _OPERATIONAL_EVENTS,
	"ITIL Service Financial Record": _OPERATIONAL_EVENTS,
	"ITIL Information Security Management": _OPERATIONAL_EVENTS,
	"ITIL Architecture Management": _OPERATIONAL_EVENTS,
	"ITIL Knowledge Article": _OPERATIONAL_EVENTS,
	"ITIL Organizational Change": _OPERATIONAL_EVENTS,
	"ITIL Supplier Record": _OPERATIONAL_EVENTS,
	"ITIL Asset": _OPERATIONAL_EVENTS,
	"ITIL Monitoring Event Management": _OPERATIONAL_EVENTS,
	"ITIL Service Validation Testing": _OPERATIONAL_EVENTS,
	"ITIL Service Continuity": _OPERATIONAL_EVENTS,
	"ITIL Service Catalogue": _OPERATIONAL_EVENTS,
	"ITIL Service Design": _OPERATIONAL_EVENTS,
	"ITIL Service Desk": _OPERATIONAL_EVENTS,
	"ITIL Service Level Agreement": _OPERATIONAL_EVENTS,
	"ITIL Service Request": _OPERATIONAL_EVENTS,
	"ITIL Software Development": _OPERATIONAL_EVENTS,
	"ITIL Infrastructure Platform": _OPERATIONAL_EVENTS,
}
# Fixtures / Workspace exports
fixtures = [
	"Workspace",
	"ITIL Practice"
]


# Redirect after login hook
on_login = "itil_master_control.api.set_redirect_after_login"
