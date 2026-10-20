# Copyright (c) 2026, ITIL Master Team and contributors
# License: MIT

import frappe
from frappe.model.document import Document


class IPAddress(Document):
	def validate(self):
		self._sync_status()

	def _sync_status(self):
		"""If assigned to device/asset → status Assigned; if cleared → Free (unless Reserved/Deprecated)."""
		if self.assigned_to_device or self.assigned_to_asset:
			if self.status in ("Free",):
				self.status = "Assigned"
		elif self.status == "Assigned":
			self.status = "Free"
