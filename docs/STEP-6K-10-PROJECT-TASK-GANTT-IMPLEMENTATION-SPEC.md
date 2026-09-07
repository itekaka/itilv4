# STEP 6K-10 — ITIL PROJECT TASK GANTT IMPLEMENTATION SPECIFICATION

**Document Version:** 1.0.0 (Pre-Implementation Architectural Specification)  
**Status:** SPECIFICATION ONLY (NOT APPROVED FOR CODING)  
**Bench:** `/home/adminekk/frappe-bench`  
**Active Site:** `development.localhost`  
**Application:** `itil_master_control`  
**Target Practice:** `Project Management`  
**Target Parent DocType:** `ITIL Project`  
**Proposed Child DocType:** `ITIL Project Task`  

---

## 1. BUSINESS INTENT & TWO-TIER GANTT ARCHITECTURE

The ITIL Master Control Panel implements a **Two-Tier Gantt Architecture** to provide both macro-level governance and micro-level project execution visibility:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: PORTFOLIO GANTT (Macro Portfolio Governance)                       │
│ URL: /app/itil-practice-dashboard?practice=project-management               │
│ Scope: All ITIL Projects across the organization                            │
│ Mapping: 1 Bar = 1 ITIL Project                                            │
│ Source: MariaDB tabITIL Project via get_project_gantt_data() API            │
│ Status: ALREADY IMPLEMENTED & ACTIVE (PROTECTED COMPONENT)                 │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                         Click Project Bar / Document Link
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: PROJECT DETAIL TASK GANTT (Micro Task Execution)                  │
│ URL: /app/itil-project/<project-name> (e.g. /app/itil-project/PRJ-00001)    │
│ Scope: Single Project Work Breakdown Structure (WBS)                       │
│ Mapping: 1 Bar = 1 ITIL Project Task                                       │
│ Source: Client-side frm.doc.tasks (In-Memory Reactivity)                   │
│ Status: SPECIFICATION DEFINED (PENDING CODING APPROVAL)                    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PROTECTED COMPONENTS & IMMUTABILITY GUARANTEES

The following components are **STRICTLY PROTECTED** and **MUST NOT BE MODIFIED** during the future implementation:

1. **Portfolio Gantt View:** `/app/itil-practice-dashboard` (JS and CSS handlers).
2. **Portfolio Gantt Backend API:** `itil_master_control.project_management.api.get_project_gantt_data`.
3. **Central Health Engine:** `itil_master_control.api.calculate_practice_live_metrics()`.
4. **Health Metric Configurations:** `PRACTICE_HEALTH_FORMULAS` and `PRACTICE_HEALTH_WEIGHTS`.
5. **Project Management Health Formula:** Status-weighted score calculation for `Project Management`.
6. **Project Management Backlog Formula:** Status-filtered backlog count (`{"In Progress", "On Hold", "Planning"}`).
7. **Cross-Practice Boundaries:** All other 23 ITIL Practices (Incident, Problem, Change, Release, Deployment, SLA, etc.) remain 100% isolated and untouched.

---

## 3. PROJECT HEALTH & BACKLOG ISOLATION PRINCIPLE

**Parent `ITIL Project.status` remains the SOLE AUTHORITATIVE SOURCE** for Project Management Practice metrics.

```
   ┌───────────────────────────────┐
   │      ITIL Project.status      │ ───► calculate_practice_live_metrics("Project Management")
   │ (Completed/In Progress/etc.) │       ├──► Health Score (e.g., 67.5% or 100%)
   └───────────────────────────────┘       └──► Open Backlog (e.g., 2 or 0)

   ┌───────────────────────────────┐
   │     ITIL Project Task[]       │ ───► Project Detail Task Gantt (Level 2 Visual Only)
   │  (Task A, Task B, Task C...)  │   │
   └───────────────────────────────┘   X [STRICTLY ISOLATED]
                                       (Zero effect on Practice Health / Backlog)
```

- If an `ITIL Project` has `status = "Completed"`, the Practice Health Score for Project Management will reflect `100%` and Backlog `0`, **regardless of the status of individual child tasks**.
- Child task creation, editing, status changes, or deletion **DO NOT** trigger practice health recalculation.

---

## 4. CHILD TABLE SCHEMA SPECIFICATION (`ITIL Project Task`)

A new Child DocType named `ITIL Project Task` will be created with `istable = 1`.

### 4.1 Field Definition
| # | Fieldname | Fieldtype | Label | Options / Configuration | Req'd | Default | Purpose |
|---|---|---|---|---|---|---|---|
| 1 | `task_name` | Data | Task Name | | **1** | | Display title on Gantt bar and task table |
| 2 | `start_date` | Date | Start Date | | **1** | | Task schedule start date |
| 3 | `end_date` | Date | End Date | | **1** | | Task schedule end date |
| 4 | `status` | Select | Status | `Planning`<br>`In Progress`<br>`Completed`<br>`On Hold`<br>`Cancelled` | 0 | `Planning` | Task execution lifecycle state |
| 5 | `progress` | Percent | Progress (%) | 0 to 100 | 0 | `0` | Visual task completion percentage |
| 6 | `assigned_to` | Link | Assigned To | `User` | 0 | | Assigned team member |
| 7 | `description` | Small Text | Description | | 0 | | Detailed task notes / instructions |

### 4.2 DocType JSON Metadata Parameters
- `name`: `"ITIL Project Task"`
- `module`: `"Project Management"`
- `custom`: `0`
- `istable`: `1`
- `editable_grid`: `1`
- `track_changes`: `1`

---

## 5. PARENT DOCTYPE SPECIFICATION (`ITIL Project`)

To accommodate child tasks and the embedded Gantt widget, the parent `ITIL Project` schema will be updated post-approval:

### 5.1 New Fields in `ITIL Project`
| Fieldname | Fieldtype | Label | Options / Insertion Point |
|---|---|---|---|
| `project_tasks_section` | Section Break | Project Tasks | Inserted after `project_schedule_section` |
| `task_gantt_html` | HTML | Task Gantt | Placed above child table for visual timeline |
| `tasks` | Table | Tasks | Options: `ITIL Project Task` |

*Existing parent fields (`project_name`, `status`, `project_manager`, `description`, `start_date`, `end_date`, `linked_change_request`) remain unchanged.*

---

## 6. TASK DEPENDENCY POLICY

- **Phase Scope:** **EXPLICITLY OUT OF SCOPE FOR THIS STEP.**
- No `depends_on_task` field or dependency SVG drawing will be implemented in this phase.
- **Future Enhancement Note:** If intra-project task dependencies are requested in future phases, a predecessor task reference field can be added without altering the core child table architecture.

---

## 7. TASK GANTT DATA SOURCE & IN-MEMORY REACTIVITY

The Level 2 Task Gantt reads directly from `frm.doc.tasks` in browser memory:

```
[User Action: + Add Task / Edit Cell / Delete Row]
                         │
                         ▼
             [Updated in frm.doc.tasks]
                         │
                         ▼
        [Client JS Transformation Function]
   (Maps frm.doc.tasks -> Frappe Gantt Objects)
                         │
                         ▼
    [new Gantt(...) / gantt.refresh(tasks)]
                         │
                         ▼
    [SVG Gantt immediately redraws in Form]
```

### 7.1 Benefits:
1. **Zero Unsaved Data Loss:** Tasks appear on the Gantt timeline immediately upon addition, before the user clicks "Save".
2. **Zero Network Latency:** In-memory transformation provides instantaneous 60fps UI feedback.
3. **Atomic Persistence:** When the user clicks **Save** (`Ctrl+S`), Frappe saves the parent `ITIL Project` and all child `ITIL Project Task` rows in a single ACID MariaDB transaction.

---

## 8. "+ ADD TASK" USER EXPERIENCE SPECIFICATION

### 8.1 Dual-Input Interaction Model
1. **Primary Entry (`+ Add Task` Button):**
   - Located on the Task Timeline toolbar.
   - Clicking opens a clean `frappe.ui.Dialog`:
     - `Task Name` (Data, mandatory, autofocus)
     - `Start Date` (Date, mandatory, defaults to parent `start_date` or today)
     - `End Date` (Date, mandatory, defaults to parent `end_date` or `start_date + 7 days`)
     - `Assigned To` (Link: User)
     - `Status` (Select: Planning, In Progress, Completed, On Hold, Cancelled; default: Planning)
     - `Progress` (Percent: 0 to 100; default: 0)
   - On **"Add Task"** click:
     - Validates date range (`start_date <= end_date`).
     - Appends row to `frm.doc.tasks` using `frm.add_child('tasks', values)`.
     - Refreshes child table grid (`frm.refresh_field('tasks')`).
     - Re-renders Task Gantt immediately.
     - Sets form dirty (`frm.dirty()`).
2. **Secondary Entry (Child Table Grid):**
   - Native Frappe grid table below the Gantt allows inline editing, sorting (`idx`), and deletion.

---

## 9. VALIDATION & BUSINESS LOGIC RULES

1. **Mandatory Fields:** `task_name`, `start_date`, and `end_date` are strictly required.
2. **Chronological Validity:** `start_date` must not be later than `end_date` (`start_date <= end_date`).
3. **Progress Boundaries:** `progress` must be an integer/float between `0` and `100`.
4. **Status & Progress Synchronization:**
   - If a task `status` is changed to `Completed`, `progress` is automatically set to `100%`.
   - If a task `progress` is set to `100%`, `status` defaults to `Completed`.
   - For all other statuses (`Planning`, `In Progress`, `On Hold`), progress remains user-adjustable (0-99%).
5. **Zero Parent Metric Mutation:** Task validations and updates must never alter parent `ITIL Project.status` or Practice Health.

---

## 10. PROJECT FORM UI LAYOUT SPECIFICATION

```
================================================================================
ITIL Project Form: PRJ-00001 — Project HRMS
================================================================================

[ Section 1: Project Information ]
Project Name    : [ Project HRMS                  ]  Status : [ In Progress   ▼ ]
Project Manager : [ teguhww007@gmail.com          ]
Start Date      : [ 2026-06-01 ]                     End Date : [ 2026-12-31 ]
Description     : [ Human Resource Management System deployment...          ]

--------------------------------------------------------------------------------
[ Section 2: Project Tasks & Execution Timeline ]

Toolbar:
[ + Add Task ]                         View: [ Day ] [ Week ] [ Month* ] [ Year ]

TASK GANTT SVG CONTAINER:
1. Requirements Analysis   ████████ (100%)
2. Database Design                  ██████████ (100%)
3. Core Backend API                          ██████████████ (50%)
4. Frontend Portal                                    ██████████ (20%)
5. UAT & Deployment                                             ██████ (0%)

TASK TABLE GRID:
#  | Task Name               | Start Date | End Date   | Status      | Progress | Assigned To
1  | Requirements Analysis   | 2026-06-01 | 2026-06-30 | Completed   | 100%     | adminekk
2  | Database Design         | 2026-07-01 | 2026-07-31 | Completed   | 100%     | teguhww007
3  | Core Backend API        | 2026-08-01 | 2026-10-15 | In Progress | 50%      | teguhww007
4  | Frontend Portal         | 2026-09-01 | 2026-11-15 | In Progress | 20%      | adminekk
5  | UAT & Deployment        | 2026-11-15 | 2026-12-31 | Planning    | 0%       | adminekk

--------------------------------------------------------------------------------
[ Section 3: Change Management & Governance ]
Linked Change Request : [ CR-00012               ]
================================================================================
```

---

## 11. FUTURE IMPLEMENTATION FILE IMPACT ANALYSIS

*The following files are identified for modification/creation ONLY AFTER EXPLICIT APPROVAL:*

| Action | Target File Path | Purpose |
|---|---|---|
| **NEW** | `itil_master_control/project_management/doctype/itil_project_task/__init__.py` | Module package initializer |
| **NEW** | `itil_master_control/project_management/doctype/itil_project_task/itil_project_task.py` | Controller class `ITILProjectTask(Document)` |
| **NEW** | `itil_master_control/project_management/doctype/itil_project_task/itil_project_task.json` | Child DocType metadata definition (`istable: 1`) |
| **MODIFY** | `itil_master_control/project_management/doctype/itil_project/itil_project.json` | Addition of `project_tasks_section`, `task_gantt_html`, and `tasks` fields |
| **NEW** | `itil_master_control/project_management/doctype/itil_project/itil_project.js` | Form client script: Gantt initialization, "+ Add Task" dialog, in-memory redraws |
| **NEW** | `itil_master_control/public/css/itil_project_gantt.css` (or bundle include) | Scoped Gantt styling within Form views |

---

## 12. REGRESSION TEST PLAN

Upon post-approval implementation, the following 15 verification tests must be executed:

- [ ] **TEST 1:** Existing `ITIL Project` records (`PRJ-00001`, `PRJ-00002`) load successfully without error.
- [ ] **TEST 2:** Existing Portfolio Gantt (`/app/itil-practice-dashboard`) renders all projects properly.
- [ ] **TEST 3:** Clicking a project on the Portfolio Gantt navigates to `/app/itil-project/<name>`.
- [ ] **TEST 4:** Project detail form renders Project Information, Task Gantt, and Task Grid.
- [ ] **TEST 5:** Clicking `[ + Add Task ]` opens the modal dialog.
- [ ] **TEST 6:** Adding a task appends it to the in-memory Gantt immediately before clicking Save.
- [ ] **TEST 7:** Saving the parent form (`Ctrl+S`) commits parent and child tasks to MariaDB.
- [ ] **TEST 8:** Editing task dates/status in child grid immediately updates the Task Gantt.
- [ ] **TEST 9:** Deleting a row in child grid removes the bar from the Task Gantt immediately.
- [ ] **TEST 10:** Validation rejects `start_date > end_date` with an error message.
- [ ] **TEST 11:** Changing child task statuses does NOT modify Project Management Practice Health Score.
- [ ] **TEST 12:** Changing child task statuses does NOT modify Project Management Open Backlog count.
- [ ] **TEST 13:** Changing parent `ITIL Project.status` modifies Practice Health according to existing formula.
- [ ] **TEST 14:** Zero regression or modifications in any of the other 23 ITIL practices.
- [ ] **TEST 15:** System cache clear and asset rebuild complete with zero errors.

---

## 13. POST-APPROVAL DEPLOYMENT PROCEDURE

*(DO NOT EXECUTE NOW — FOR POST-APPROVAL EXECUTION ONLY)*

```bash
# 1. Apply Schema Changes
bench --site development.localhost migrate

# 2. Build Frontend Asset Bundles
bench build --app itil_master_control

# 3. Clear Runtime Cache
bench --site development.localhost clear-cache
```

---

## 14. ROLLBACK PLAN

If any unforeseen error occurs during post-approval implementation:
1. Revert `itil_project.json` to its previous schema (remove `tasks` and `task_gantt_html`).
2. Remove `itil_project_task/` DocType directory.
3. Remove `itil_project.js`.
4. Run `bench --site development.localhost migrate` to restore clean MariaDB schema.
5. All existing `ITIL Project` data (`PRJ-00001`, `PRJ-00002`) will remain intact without data loss.

---

====================================================================================================
STEP 6K-10 COMPLETE
PRE-IMPLEMENTATION SPECIFICATION ONLY

NO SOURCE CODE MODIFIED
NO DOCTYPE MODIFIED
NO DATABASE MODIFIED
NO DATABASE MIGRATION
NO JAVASCRIPT MODIFIED
NO CSS MODIFIED
NO PYTHON MODIFIED
NO HOOKS MODIFIED
NO BUILD PERFORMED
NO CACHE CLEAR PERFORMED

IMPLEMENTATION NOT APPROVED

WAITING FOR EXPLICIT USER APPROVAL
====================================================================================================
