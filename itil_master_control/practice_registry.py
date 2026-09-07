import os, json
import frappe
from frappe import _
from frappe import scrub

def get_canonical_practices():
	"""
	Reads standard canonical practice definitions from fixtures/itil_practice.json.
	This is used ONLY during patch synchronization.
	"""
	fixture_path = frappe.get_app_path("itil_master_control", "fixtures", "itil_practice.json")
	if not os.path.exists(fixture_path):
		# Fallback path if nested
		fixture_path = os.path.join(
			frappe.get_app_path("itil_master_control"), "..", "fixtures", "itil_practice.json"
		)
	
	with open(fixture_path, "r") as f:
		return json.load(f)


def ensure_practice_registry_synced():
	"""
	Authoritative synchronization function invoked by migration patch.
	Idempotently upserts standard 24 practices in database while preserving existing metrics.
	"""
	canonical_list = get_canonical_practices()
	
	for defn in canonical_list:
		name = defn.get("practice_name") or defn.get("name")
		slug = defn.get("practice_slug") or scrub(name).replace("_", "-")
		
		# 1. Primary lookup by practice_slug
		doc_name = frappe.db.get_value("ITIL Practice", {"practice_slug": slug}, "name")
		
		# 2. Fallback lookup by name = practice_name
		if not doc_name and name:
			doc_name = frappe.db.get_value("ITIL Practice", {"name": name}, "name")
		
		if doc_name:
			# Update existing record metadata only (Preserve health metrics & owner)
			doc = frappe.get_doc("ITIL Practice", doc_name)
			doc.practice_name = name
			doc.practice_slug = slug
			doc.practice_group = defn.get("practice_group") or "General Management Practices"
			doc.display_order = defn.get("display_order", 1)
			doc.icon = defn.get("icon") or "octicon octicon-checklist"
			doc.doctype_reference = defn.get("doctype_reference")
			doc.description = defn.get("description") or doc.description
			doc.is_active = defn.get("is_active", 1)
			doc.save(ignore_permissions=True)
		else:
			# Insert new practice record
			doc = frappe.get_doc({
				"doctype": "ITIL Practice",
				"practice_name": name,
				"practice_slug": slug,
				"practice_group": defn.get("practice_group") or "General Management Practices",
				"display_order": defn.get("display_order", 1),
				"icon": defn.get("icon") or "octicon octicon-checklist",
				"doctype_reference": defn.get("doctype_reference"),
				"description": defn.get("description"),
				"health_score": defn.get("health_score", 100.0),
				"sla_compliance_pct": defn.get("sla_compliance_pct", 95.0),
				"open_items_count": defn.get("open_items_count", 0),
				"trend_direction": defn.get("trend_direction", "Stable"),
				"is_active": defn.get("is_active", 1)
			})
			doc.insert(ignore_permissions=True)
			
	frappe.db.commit()


@frappe.whitelist()
def get_practice_registry():
	"""
	Runtime API returning database records grouped into the 3 official practice categories.
	Queries MariaDB directly; does NOT read JSON fixtures.
	"""
	records = frappe.get_all(
		"ITIL Practice",
		filters={"is_active": 1},
		fields=[
			"name", "practice_name", "practice_slug", "practice_group",
			"display_order", "health_score", "sla_compliance_pct",
			"open_items_count", "trend_direction", "icon",
			"doctype_reference", "description"
		],
		order_by="display_order asc"
	)
	
	grouped = {
		"General Management Practices": [],
		"Service Management Practices": [],
		"Technical Management Practices": []
	}
	
	for r in records:
		group = r.get("practice_group") or "General Management Practices"
		if group not in grouped:
			grouped[group] = []
		grouped[group].append(r)
		
	return grouped


@frappe.whitelist()
def get_practice_definition(practice=None):
	"""
	Runtime API returning complete practice details and recent operational activity.
	Resolves by practice_slug or practice_name.
	"""
	if not practice:
		return {"error": "No practice parameter specified."}
		
	# Try lookup by practice_slug
	doc_name = frappe.db.get_value("ITIL Practice", {"practice_slug": practice}, "name")
	if not doc_name:
		# Fallback to lookup by name
		doc_name = frappe.db.get_value("ITIL Practice", {"name": practice}, "name")
		
	if not doc_name:
		return {"error": f"Practice '{practice}' not found."}
		
	doc = frappe.get_doc("ITIL Practice", doc_name)
	practice_data = doc.as_dict()
	
	# Fetch recent operational records defensively if doctype_reference is set
	recent_records = []
	doctype_ref = doc.doctype_reference
	if doctype_ref and frappe.db.exists("DocType", doctype_ref) and frappe.has_permission(doctype_ref, "read"):
		try:
			# Fetch generic base fields
			recent_records = frappe.get_all(
				doctype_ref,
				fields=["name", "modified", "owner"],
				limit=5,
				order_by="modified desc"
			)
		except Exception:
			recent_records = []
			
	return {
		"practice": practice_data,
		"recent_records": recent_records
	}
