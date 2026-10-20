# Copyright (c) 2026, ITIL Master Team and contributors
# License: MIT

from frappe.model.document import Document


class VLAN(Document):
	def validate(self):
		if self.vlan_id is not None:
			if self.vlan_id < 1 or self.vlan_id > 4094:
				from frappe import _
				frappe.throw(_("VLAN ID must be between 1 and 4094"))
