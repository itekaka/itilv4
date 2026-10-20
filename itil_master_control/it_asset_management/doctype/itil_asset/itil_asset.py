# Copyright (c) 2026, ITIL Master Team and contributors
# License: MIT

import frappe
from frappe.model.document import Document


class ITILAsset(Document):
	def validate(self):
		self._sync_from_endpoint_device()
		self._validate_lifecycle()

	def _sync_from_endpoint_device(self):
		"""Copy key fields from linked Endpoint Device if empty."""
		if not self.endpoint_device:
			return
		device = frappe.get_doc("Endpoint Device", self.endpoint_device)
		mapping = {
			"serial_number": "serial_number",
			"manufacturer": "manufacturer",
			"model": "model",
			"hostname": "hostname",
			"os_name": "os_name",
			"os_version": "os_version",
		}
		for src, dst in mapping.items():
			if not self.get(dst) and device.get(src):
				self.set(dst, device.get(src))

	def _validate_lifecycle(self):
		"""Basic lifecycle rules."""
		if self.lifecycle_status == "Disposed" and self.endpoint_device:
			# Optional: mark endpoint offline when disposed
			pass

	def on_update(self):
		self._write_activity_log()

	def _write_activity_log(self):
		"""Simple activity trail via comment / optional custom log."""
		if self.has_value_changed("lifecycle_status"):
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "ITIL Asset",
				"reference_name": self.name,
				"content": f"Lifecycle status changed to <b>{self.lifecycle_status}</b>",
			}).insert(ignore_permissions=True)
