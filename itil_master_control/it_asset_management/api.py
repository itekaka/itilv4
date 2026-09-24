# Copyright (c) 2026, ITIL Master Team and contributors
# Endpoint Management — Agent API (Phase 1)

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import now_datetime


# Default intervals (seconds) — sesuai Implementation Spec
DEFAULT_HEARTBEAT_INTERVAL = 300
DEFAULT_INVENTORY_INTERVAL = 21600


def _hash_secret(secret: str) -> str:
	"""Hash agent secret (SHA-256). Never store plain secret."""
	if not secret:
		return ""
	return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _get_agent_headers():
	"""Read Phase 1 auth headers."""
	agent_id = frappe.get_request_header("X-Agent-ID") or ""
	agent_secret = frappe.get_request_header("X-Agent-Secret") or ""
	return agent_id.strip(), agent_secret.strip()


def _write_agent_event(device_name, event_type, payload=None):
	"""Insert Endpoint Agent Event (audit)."""
	try:
		doc = frappe.get_doc({
			"doctype": "Endpoint Agent Event",
			"device": device_name,
			"event_type": event_type,
			"created_at": now_datetime(),
			"payload": json.dumps(payload, default=str) if payload is not None else None,
		})
		doc.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title=f"Endpoint Agent Event failed: {event_type}",
			message=frappe.get_traceback(),
		)


def _verify_agent_auth(agent_id: str, secret: str, require_existing: bool = True):
	"""
	Validate agent credentials.
	Returns (device_doc or None, error_message or None).
	"""
	if not agent_id or not secret:
		return None, "Missing X-Agent-ID or X-Agent-Secret"

	device_name = frappe.db.get_value("Endpoint Device", {"device_uuid": agent_id}, "name")
	if not device_name:
		if require_existing:
			return None, "Unknown agent"
		return None, None

	cred_name = frappe.db.get_value(
		"Endpoint Agent Credential",
		{"device": device_name, "is_active": 1},
		"name",
	)
	if not cred_name:
		return None, "No active credential"

	# Password field: use get_password if stored via set_password;
	# we store SHA-256 hex in Password field via db set for simplicity.
	stored = frappe.db.get_value("Endpoint Agent Credential", cred_name, "secret_hash")
	# For Password fieldtype, value may need get_password
	try:
		from frappe.utils.password import get_decrypted_password
		decrypted = get_decrypted_password(
			"Endpoint Agent Credential", cred_name, "secret_hash", raise_exception=False
		)
		if decrypted:
			stored = decrypted
	except Exception:
		pass

	if not stored or stored != _hash_secret(secret):
		_write_agent_event(device_name, "AUTH_FAILURE", {"agent_id": agent_id})
		return None, "Invalid credential"

	return frappe.get_doc("Endpoint Device", device_name), None


@frappe.whitelist(allow_guest=True)
def agent_register(agent_id=None, hostname=None, agent_version=None, os=None, secret=None):
	"""
	Register a new agent or refresh registration.

	Body JSON (or form):
	  agent_id, hostname, agent_version, os, secret

	Headers (optional on first register, required later):
	  X-Agent-ID, X-Agent-Secret
	"""
	# Prefer JSON body
	data = frappe.request.get_json(silent=True) or {}
	agent_id = (agent_id or data.get("agent_id") or "").strip()
	hostname = (hostname or data.get("hostname") or "").strip() or None
	agent_version = (agent_version or data.get("agent_version") or "").strip() or None
	os_name = (os or data.get("os") or "").strip() or None
	secret = (secret or data.get("secret") or "").strip()

	# Fallback headers
	hdr_id, hdr_secret = _get_agent_headers()
	if not agent_id and hdr_id:
		agent_id = hdr_id
	if not secret and hdr_secret:
		secret = hdr_secret

	if not agent_id:
		frappe.local.response["http_status_code"] = 400
		return {"success": False, "message": "agent_id is required"}

	if not secret:
		frappe.local.response["http_status_code"] = 400
		return {"success": False, "message": "secret is required"}

	existing_name = frappe.db.get_value("Endpoint Device", {"device_uuid": agent_id}, "name")
	is_new = not existing_name

	if is_new:
		# Create device
		device = frappe.get_doc({
			"doctype": "Endpoint Device",
			"device_uuid": agent_id,
			"hostname": hostname,
			"os_name": os_name,
			"agent_version": agent_version,
			"status": "OFFLINE",
		})
		device.insert(ignore_permissions=True)

		# Store hashed secret
		cred = frappe.get_doc({
			"doctype": "Endpoint Agent Credential",
			"device": device.name,
			"secret_hash": _hash_secret(secret),
			"is_active": 1,
		})
		cred.insert(ignore_permissions=True)

		_write_agent_event(
			device.name,
			"AGENT_REGISTERED",
			{"hostname": hostname, "agent_version": agent_version, "os": os_name},
		)
		frappe.db.commit()

		frappe.local.response["http_status_code"] = 201
		return {
			"success": True,
			"device_id": device.name,
			"heartbeat_interval": DEFAULT_HEARTBEAT_INTERVAL,
			"inventory_interval": DEFAULT_INVENTORY_INTERVAL,
			"message": "registered",
		}

	# Existing device — must prove secret
	device, err = _verify_agent_auth(agent_id, secret, require_existing=True)
	if err:
		frappe.local.response["http_status_code"] = 401
		return {"success": False, "message": err}

	# Refresh registration fields
	if hostname:
		device.hostname = hostname
	if agent_version:
		device.agent_version = agent_version
	if os_name:
		device.os_name = os_name
	device.save(ignore_permissions=True)

	_write_agent_event(
		device.name,
		"AGENT_REGISTERED",
		{"hostname": hostname, "agent_version": agent_version, "os": os_name, "refresh": True},
	)
	frappe.db.commit()

	return {
		"success": True,
		"device_id": device.name,
		"heartbeat_interval": DEFAULT_HEARTBEAT_INTERVAL,
		"inventory_interval": DEFAULT_INVENTORY_INTERVAL,
		"message": "registered",
	}
@frappe.whitelist(allow_guest=True)
def agent_heartbeat(agent_id=None, timestamp=None, agent_version=None):
	"""
	Update last_seen and set status ONLINE.

	Body JSON:
	  agent_id, timestamp (optional), agent_version (optional)

	Headers (required):
	  X-Agent-ID, X-Agent-Secret
	"""
	data = frappe.request.get_json(silent=True) or {}
	agent_id = (agent_id or data.get("agent_id") or "").strip()
	timestamp = data.get("timestamp") or timestamp
	agent_version = (agent_version or data.get("agent_version") or "").strip() or None

	hdr_id, hdr_secret = _get_agent_headers()
	if not agent_id and hdr_id:
		agent_id = hdr_id
	secret = hdr_secret or (data.get("secret") or "").strip()

	if not agent_id or not secret:
		frappe.local.response["http_status_code"] = 400
		return {"success": False, "message": "agent_id and secret are required"}

	device, err = _verify_agent_auth(agent_id, secret, require_existing=True)
	if err:
		frappe.local.response["http_status_code"] = 401
		return {"success": False, "message": err}

	device.status = "ONLINE"
	device.last_seen = now_datetime()
	if agent_version:
		device.agent_version = agent_version
	device.save(ignore_permissions=True)

	_write_agent_event(
		device.name,
		"AGENT_HEARTBEAT",
		{"timestamp": timestamp, "agent_version": agent_version},
	)
	frappe.db.commit()

	server_time = now_datetime()
	return {
		"success": True,
		"server_time": server_time.isoformat() if hasattr(server_time, "isoformat") else str(server_time),
		"status": "ONLINE",
	}
def _get_or_create_software(name, publisher=None, version=None):
	"""Find or create Endpoint Software by name + version."""
	name = (name or "").strip()
	if not name:
		return None
	version = (version or "").strip() or ""
	publisher = (publisher or "").strip() or None

	filters = {"software_name": name}
	if version:
		filters["version"] = version

	existing = frappe.db.get_value("Endpoint Software", filters, "name")
	if existing:
		return existing

	doc = frappe.get_doc({
		"doctype": "Endpoint Software",
		"software_name": name,
		"publisher": publisher,
		"version": version or None,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(allow_guest=True)
def agent_inventory(agent_id=None, inventory_version=None, collected_at=None,
		device=None, hardware=None, disks=None, network_interfaces=None, software=None):
	"""
	Receive full inventory payload and upsert Endpoint Device + children.

	Auth: X-Agent-ID + X-Agent-Secret (or body secret).
	"""
	data = frappe.request.get_json(silent=True) or {}

	agent_id = (agent_id or data.get("agent_id") or "").strip()
	inventory_version = data.get("inventory_version") or inventory_version
	collected_at = data.get("collected_at") or collected_at

	device_data = data.get("device") or device or {}
	hardware_data = data.get("hardware") or hardware or {}
	disks_data = data.get("disks") or disks or []
	network_data = data.get("network_interfaces") or network_interfaces or []
	software_data = data.get("software") or software or []

	hdr_id, hdr_secret = _get_agent_headers()
	if not agent_id and hdr_id:
		agent_id = hdr_id
	secret = hdr_secret or (data.get("secret") or "").strip()

	if not agent_id or not secret:
		frappe.local.response["http_status_code"] = 400
		return {"success": False, "message": "agent_id and secret are required"}

	device_doc, err = _verify_agent_auth(agent_id, secret, require_existing=True)
	if err:
		frappe.local.response["http_status_code"] = 401
		return {"success": False, "message": err}

	# Snapshot sederhana untuk change detection
	before = {
		"hostname": device_doc.hostname,
		"os_name": device_doc.os_name,
		"cpu_model": device_doc.cpu_model,
		"ram_total_bytes": device_doc.ram_total_bytes,
		"disk_count": len(device_doc.disks or []),
		"nic_count": len(device_doc.network_interfaces or []),
		"sw_count": len(device_doc.installed_software or []),
	}

	# --- Device identity ---
	if isinstance(device_data, dict):
		for src, dst in [
			("hostname", "hostname"),
			("serial_number", "serial_number"),
			("manufacturer", "manufacturer"),
			("model", "model"),
			("os_name", "os_name"),
			("os_version", "os_version"),
			("architecture", "architecture"),
			("logged_user", "logged_user"),
		]:
			if device_data.get(src) is not None:
				setattr(device_doc, dst, device_data.get(src))

	# --- Hardware (flat on parent) ---
	if isinstance(hardware_data, dict):
		for src, dst in [
			("cpu_model", "cpu_model"),
			("physical_cores", "physical_cores"),
			("logical_cores", "logical_cores"),
			("ram_total_bytes", "ram_total_bytes"),
			("bios_version", "bios_version"),
			("bios_serial", "bios_serial"),
			("motherboard", "motherboard"),
		]:
			if hardware_data.get(src) is not None:
				val = hardware_data.get(src)
				# Int fields
				if dst in ("physical_cores", "logical_cores") and val is not None:
					try:
						val = int(val)
					except (TypeError, ValueError):
						pass
				# Store large numbers as string for Data field
				if dst == "ram_total_bytes" and val is not None:
					val = str(val)
				setattr(device_doc, dst, val)

	# --- Disks + partitions (replace rows) ---
	device_doc.set("disks", [])
	if isinstance(disks_data, list):
		for d in disks_data:
			if not isinstance(d, dict):
				continue
			disk_row = {
				"disk_index": d.get("disk_index"),
				"model": d.get("model"),
				"serial_number": d.get("serial_number"),
				"capacity_bytes": str(d["capacity_bytes"]) if d.get("capacity_bytes") is not None else None,
				"interface_type": d.get("interface_type"),
				"health_status": d.get("health_status"),
				"partitions": [],
			}
			for p in (d.get("partitions") or []):
				if not isinstance(p, dict):
					continue
				disk_row["partitions"].append({
					"mount_point": p.get("mount_point"),
					"filesystem": p.get("filesystem"),
					"total_bytes": str(p["total_bytes"]) if p.get("total_bytes") is not None else None,
					"used_bytes": str(p["used_bytes"]) if p.get("used_bytes") is not None else None,
					"free_bytes": str(p["free_bytes"]) if p.get("free_bytes") is not None else None,
					"usage_percent": p.get("usage_percent"),
				})
			device_doc.append("disks", disk_row)

	# --- Network interfaces (replace rows) ---
	device_doc.set("network_interfaces", [])
	if isinstance(network_data, list):
		for n in network_data:
			if not isinstance(n, dict):
				continue
			device_doc.append("network_interfaces", {
				"name_nic": n.get("name"),
				"interface_type": n.get("interface_type"),
				"mac_address": n.get("mac_address"),
				"ipv4": n.get("ipv4"),
				"ipv6": n.get("ipv6"),
				"gateway": n.get("gateway"),
				"dns": n.get("dns"),
				"dhcp_enabled": 1 if n.get("dhcp_enabled") else 0,
			})

	# --- Software (catalog + child links) ---
	device_doc.set("installed_software", [])
	if isinstance(software_data, list):
		for s in software_data:
			if not isinstance(s, dict):
				continue
			sw_name = _get_or_create_software(
				s.get("name"),
				publisher=s.get("publisher"),
				version=s.get("version"),
			)
			if not sw_name:
				continue
			device_doc.append("installed_software", {
				"software": sw_name,
				"install_date": s.get("install_date"),
				"architecture": s.get("architecture"),
				"install_location": s.get("install_location"),
			})

	# Touch presence
	device_doc.status = "ONLINE"
	device_doc.last_seen = now_datetime()
	device_doc.save(ignore_permissions=True)

	after = {
		"hostname": device_doc.hostname,
		"os_name": device_doc.os_name,
		"cpu_model": device_doc.cpu_model,
		"ram_total_bytes": device_doc.ram_total_bytes,
		"disk_count": len(device_doc.disks or []),
		"nic_count": len(device_doc.network_interfaces or []),
		"sw_count": len(device_doc.installed_software or []),
	}
	changes_detected = before != after

	_write_agent_event(
		device_doc.name,
		"INVENTORY_CHANGED" if changes_detected else "INVENTORY_RECEIVED",
		{
			"inventory_version": inventory_version,
			"collected_at": collected_at,
			"changes_detected": changes_detected,
		},
	)
	frappe.db.commit()

	return {
		"success": True,
		"message": "inventory received",
		"changes_detected": changes_detected,
	}
