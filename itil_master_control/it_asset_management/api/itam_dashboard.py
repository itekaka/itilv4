# Copyright (c) 2026, ITIL Master Team and contributors
# IT Asset Management — Dashboard KPIs, Reconciliation, Overview
# Place under: itil_master_control/it_asset_management/api/itam_dashboard.py
# Or merge into existing api.py

import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, add_days


# ---------------------------------------------------------------------------
# D3 — KPI Real Data
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_itam_kpis():
	"""Return 6 KPI values for Practice Dashboard."""
	total_assets = frappe.db.count("ITIL Asset")
	by_type = frappe.db.sql(
		"""
		SELECT asset_type, COUNT(*) as cnt
		FROM `tabITIL Asset`
		GROUP BY asset_type
		""",
		as_dict=True,
	)
	type_map = {r.asset_type: r.cnt for r in by_type}
	hardware = type_map.get("Hardware", 0)
	software = type_map.get("Software", 0)
	network = type_map.get("Network", 0)

	# Discovery Gap: Endpoint Device without linked ITIL Asset
	discovery_gap = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabEndpoint Device` ed
		WHERE NOT EXISTS (
			SELECT 1 FROM `tabITIL Asset` ia
			WHERE ia.endpoint_device = ed.name
		)
		"""
	)[0][0]

	# Open Lifecycle Actions: statuses that need attention
	open_actions = frappe.db.count(
		"ITIL Asset",
		{"lifecycle_status": ["in", ["Planning", "Ordered", "Received", "Maintenance", "Retired"]]},
	)

	# License Compliance
	licenses = frappe.get_all(
		"Software License",
		fields=["compliance_status"],
	)
	total_lic = len(licenses) or 1
	compliant = sum(1 for l in licenses if l.compliance_status == "Compliant")
	license_compliance_pct = round((compliant / total_lic) * 100) if licenses else 100

	# Health Score (simple composite 0-100)
	# completeness: assets with serial or endpoint link
	complete = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabITIL Asset`
		WHERE IFNULL(serial_number,'') != '' OR IFNULL(endpoint_device,'') != ''
		"""
	)[0][0]
	completeness = (complete / total_assets * 100) if total_assets else 100
	freshness = 100  # placeholder — can use last_seen from endpoint later
	health_score = round((completeness * 0.4) + (license_compliance_pct * 0.4) + (freshness * 0.2))

	# Trend (simple): compare open_actions vs previous week — placeholder Improving
	trend = "Improving"
	if open_actions > 50:
		trend = "Declining"
	elif open_actions > 20:
		trend = "Stable"

	return {
		"total_assets": total_assets,
		"hardware": hardware,
		"software": software,
		"network": network,
		"health_score": health_score,
		"license_compliance": license_compliance_pct,
		"open_lifecycle_actions": open_actions,
		"discovery_gap": discovery_gap,
		"trend": trend,
	}


# ---------------------------------------------------------------------------
# D4 — Overview Tab Content
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_recent_activity(limit=10):
	"""Recent operational activity from comments + agent events."""
	limit = int(limit or 10)
	activities = []

	# From ITIL Asset comments (lifecycle changes)
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "ITIL Asset",
			"comment_type": "Info",
		},
		fields=["content", "creation", "reference_name", "owner"],
		order_by="creation desc",
		limit=limit,
	)
	for c in comments:
		activities.append({
			"type": "Lifecycle",
			"title": frappe.utils.strip_html(c.content or "")[:120],
			"ref": c.reference_name,
			"doctype": "ITIL Asset",
			"when": c.creation,
			"by": c.owner,
		})

	# From Endpoint Agent Event (discovery)
	events = frappe.get_all(
		"Endpoint Agent Event",
		fields=["event_type", "device", "created_at", "payload"],
		order_by="created_at desc",
		limit=limit,
	)
	for e in events:
		activities.append({
			"type": "Discovery",
			"title": f"{e.event_type} — {e.device}",
			"ref": e.device,
			"doctype": "Endpoint Device",
			"when": e.created_at,
			"by": "Agent",
		})

	# Sort by when desc
	activities.sort(key=lambda x: x["when"] or "", reverse=True)
	return activities[:limit]


@frappe.whitelist()
def get_lifecycle_breakdown():
	"""Assets by lifecycle_status for donut/bar."""
	rows = frappe.db.sql(
		"""
		SELECT lifecycle_status as status, COUNT(*) as count
		FROM `tabITIL Asset`
		GROUP BY lifecycle_status
		ORDER BY count DESC
		""",
		as_dict=True,
	)
	total = sum(r.count for r in rows) or 1
	for r in rows:
		r.percent = round(r.count / total * 100, 1)
	return {"total": total, "rows": rows}


@frappe.whitelist()
def get_top_license_risks(limit=5):
	"""Over-licensed, under-licensed, expiring soon."""
	limit = int(limit or 5)
	risks = []

	# Over
	overs = frappe.get_all(
		"Software License",
		filters={"compliance_status": "Over"},
		fields=["name", "license_name", "software_name", "seats", "used_count", "expiry_date"],
		limit=limit,
	)
	for o in overs:
		risks.append({
			"name": o.name,
			"title": o.license_name or o.software_name,
			"risk": "Over Licensed",
			"detail": f"{o.used_count}/{o.seats} seats used",
			"severity": "high",
		})

	# Expiring in 30 days
	soon = add_days(getdate(), 30)
	expiring = frappe.get_all(
		"Software License",
		filters={
			"expiry_date": ["between", [getdate(), soon]],
		},
		fields=["name", "license_name", "software_name", "expiry_date"],
		limit=limit,
	)
	for e in expiring:
		risks.append({
			"name": e.name,
			"title": e.license_name or e.software_name,
			"risk": "Expiring Soon",
			"detail": f"Expires {e.expiry_date}",
			"severity": "medium",
		})

	return risks[:limit]


# ---------------------------------------------------------------------------
# D5 — Reconciliation
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_unmatched_devices(limit=50):
	"""Endpoint Devices not yet linked to any ITIL Asset."""
	limit = int(limit or 50)
	rows = frappe.db.sql(
		"""
		SELECT ed.name, ed.device_uuid, ed.hostname, ed.serial_number,
		       ed.manufacturer, ed.model, ed.os_name, ed.status, ed.last_seen
		FROM `tabEndpoint Device` ed
		WHERE NOT EXISTS (
			SELECT 1 FROM `tabITIL Asset` ia
			WHERE ia.endpoint_device = ed.name
		)
		ORDER BY ed.last_seen DESC
		LIMIT %s
		""",
		(limit,),
		as_dict=True,
	)
	return rows


@frappe.whitelist()
def promote_to_itil_asset(endpoint_device, asset_tag=None, lifecycle_status="In Use"):
	"""
	Create ITIL Asset from Endpoint Device and link them.
	Returns the new ITIL Asset name.
	"""
	if not endpoint_device:
		frappe.throw(_("endpoint_device is required"))

	device = frappe.get_doc("Endpoint Device", endpoint_device)

	# Already linked?
	existing = frappe.db.get_value("ITIL Asset", {"endpoint_device": endpoint_device}, "name")
	if existing:
		return {"success": True, "asset": existing, "message": "Already linked"}

	asset_tag = asset_tag or f"AST-{device.hostname or device.device_uuid[:8]}"
	# Ensure unique asset_tag
	if frappe.db.exists("ITIL Asset", {"asset_tag": asset_tag}):
		asset_tag = f"{asset_tag}-{frappe.generate_hash(length=4)}"

	doc = frappe.get_doc({
		"doctype": "ITIL Asset",
		"asset_tag": asset_tag,
		"asset_name": device.hostname or asset_tag,
		"asset_type": "Hardware",
		"lifecycle_status": lifecycle_status or "In Use",
		"endpoint_device": device.name,
		"serial_number": device.serial_number,
		"manufacturer": device.manufacturer,
		"model": device.model,
		"hostname": device.hostname,
		"os_name": device.os_name,
		"os_version": device.os_version,
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"asset": doc.name,
		"asset_tag": doc.asset_tag,
		"message": "Promoted to ITIL Asset",
	}


@frappe.whitelist()
def suggest_match(endpoint_device):
	"""Suggest existing ITIL Asset that might match this device (by serial/hostname)."""
	device = frappe.get_doc("Endpoint Device", endpoint_device)
	suggestions = []

	if device.serial_number:
		found = frappe.get_all(
			"ITIL Asset",
			filters={"serial_number": device.serial_number, "endpoint_device": ["in", ["", None]]},
			fields=["name", "asset_tag", "hostname", "lifecycle_status"],
			limit=5,
		)
		suggestions.extend(found)

	if device.hostname:
		found = frappe.get_all(
			"ITIL Asset",
			filters={"hostname": device.hostname, "endpoint_device": ["in", ["", None]]},
			fields=["name", "asset_tag", "hostname", "lifecycle_status"],
			limit=5,
		)
		for f in found:
			if f.name not in [s.name for s in suggestions]:
				suggestions.append(f)

	return suggestions
