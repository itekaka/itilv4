import frappe
from itil_master_control.practice_registry import ensure_practice_registry_synced

def execute():
	"""
	Post-model-sync patch: Runs AFTER schema sync has applied unique index.
	Executes ensure_practice_registry_synced() to update metadata for the 24 practices
	while preserving existing operational metrics.
	"""
	ensure_practice_registry_synced()
