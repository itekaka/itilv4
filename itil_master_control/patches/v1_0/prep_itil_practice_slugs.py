import frappe
from frappe import _
from frappe import scrub

def execute():
	"""
	Pre-model-sync patch: Runs BEFORE schema sync applies unique index on practice_slug.
	Safely adds column if missing, populates missing slugs for existing records,
	and verifies zero duplicate slugs exist.
	"""
	if not frappe.db.has_column("ITIL Practice", "practice_slug"):
		frappe.db.add_column("ITIL Practice", "practice_slug", "VARCHAR(255)")

	# Load existing ITIL Practice records
	records = frappe.db.get_all("ITIL Practice", fields=["name", "practice_name", "practice_slug"])

	for r in records:
		if not r.get("practice_slug"):
			slug = scrub(r.get("practice_name") or r.get("name")).replace("_", "-")
			frappe.db.sql(
				"UPDATE `tabITIL Practice` SET practice_slug=%s WHERE name=%s",
				(slug, r.name)
			)

	# Verify zero duplicate non-empty slugs exist
	duplicates = frappe.db.sql(
		"""
		SELECT practice_slug, COUNT(*) as cnt
		FROM `tabITIL Practice`
		WHERE practice_slug IS NOT NULL AND practice_slug != ''
		GROUP BY practice_slug
		HAVING cnt > 1
		""",
		as_dict=True
	)

	if duplicates:
		dups_str = ", ".join([d.practice_slug for d in duplicates])
		frappe.throw(
			_("Duplicate practice_slug values found during pre-migration check: {0}. Manual resolution required.").format(dups_str),
			frappe.ValidationError
		)
