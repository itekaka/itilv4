import frappe
from frappe import _
from frappe.utils import getdate, add_days

STATUS_PROGRESS_MAP = {
    "Completed": 100,
    "In Progress": 50,
    "Planning": 10,
    "On Hold": 25,
    "Cancelled": 0,
}

STATUS_CLASS_MAP = {
    "Completed": "bar-completed",
    "In Progress": "bar-in-progress",
    "Planning": "bar-planning",
    "On Hold": "bar-on-hold",
    "Cancelled": "bar-cancelled",
}


@frappe.whitelist()
def get_project_gantt_data():
    """
    Whitelisted read-only API returning formatted project data for Frappe Gantt.
    Does NOT modify any database records or practice health scores.
    """
    if not frappe.has_permission("ITIL Project", "read"):
        frappe.throw(_("Not permitted to view ITIL Project records"), frappe.PermissionError)

    records = frappe.get_all(
        "ITIL Project",
        fields=[
            "name",
            "project_name",
            "status",
            "project_manager",
            "description",
            "start_date",
            "end_date",
            "linked_change_request",
        ],
        order_by="start_date asc, creation asc",
    )

    projects = []
    for doc in records:
        start_date = doc.get("start_date")
        end_date = doc.get("end_date")

        # Safely normalize dates without crashing
        if not start_date and not end_date:
            today = getdate()
            start_str = str(today)
            end_str = str(add_days(today, 30))
        elif start_date and not end_date:
            start_str = str(start_date)
            end_str = str(add_days(getdate(start_date), 30))
        elif not start_date and end_date:
            end_str = str(end_date)
            start_str = str(add_days(getdate(end_date), -30))
        else:
            # Both dates present
            s_date = getdate(start_date)
            e_date = getdate(end_date)
            if s_date > e_date:
                s_date, e_date = e_date, s_date
            start_str = str(s_date)
            end_str = str(e_date)

        status = doc.get("status") or "Planning"
        progress = STATUS_PROGRESS_MAP.get(status, 0)
        custom_class = STATUS_CLASS_MAP.get(status, "bar-planning")

        projects.append({
            "id": doc.get("name"),
            "name": doc.get("project_name") or doc.get("name"),
            "project_name": doc.get("project_name") or doc.get("name"),
            "start": start_str,
            "end": end_str,
            "status": status,
            "progress": progress,
            "project_manager": doc.get("project_manager") or "",
            "description": doc.get("description") or "",
            "custom_class": custom_class,
            "linked_change_request": doc.get("linked_change_request") or "",
        })

    return {
        "projects": projects
    }
