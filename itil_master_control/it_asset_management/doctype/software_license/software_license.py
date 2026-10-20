# Copyright (c) 2026, ITIL Master Team and contributors
# License: MIT

import frappe
from frappe.model.document import Document


class SoftwareLicense(Document):
	def validate(self):
		self.recalculate_usage()

	def recalculate_usage(self):
		"""Count installations matching software_name from Endpoint Device Software."""
		if not self.software_name:
			self.used_count = 0
			self.available_count = self.seats or 0
			self.compliance_status = "Unknown"
			return

		# Count distinct devices that have this software installed
		used = frappe.db.sql(
			"""
			SELECT COUNT(DISTINCT parent)
			FROM `tabEndpoint Device Software`
			WHERE software_name = %s
			""",
			(self.software_name,),
		)
		self.used_count = used[0][0] if used else 0
		seats = self.seats or 0
		self.available_count = max(seats - self.used_count, 0)

		if seats == 0:
			self.compliance_status = "Unknown"
		elif self.used_count > seats:
			self.compliance_status = "Over"
		elif self.used_count < seats:
			# Under can still be Compliant if intentional; treat exact or under as Compliant for simplicity
			# Over = non-compliant
			self.compliance_status = "Compliant" if self.used_count <= seats else "Over"
		else:
			self.compliance_status = "Compliant"

		# Expiring soon / expired override visual (status stays; UI can flag)
		if self.expiry_date and frappe.utils.getdate(self.expiry_date) < frappe.utils.getdate():
			# Keep compliance_status; callers can check expiry separately
			pass


@frappe.whitelist()
def refresh_all_license_usage():
	"""Background-friendly: recalculate all licenses."""
	licenses = frappe.get_all("Software License", pluck="name")
	for name in licenses:
		doc = frappe.get_doc("Software License", name)
		doc.recalculate_usage()
		doc.save(ignore_permissions=True)
	return {"updated": len(licenses)}
