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
