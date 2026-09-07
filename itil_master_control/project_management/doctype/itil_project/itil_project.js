// Copyright (c) 2026, ITIL Master Team and contributors
// For license information, please see license.txt

frappe.provide('itil_master_control');

frappe.ui.form.on('ITIL Project', {
	refresh: function(frm) {
		render_task_gantt_section(frm);
	},

	validate: function(frm) {
		// Validate all child task date ranges
		if (frm.doc.tasks && frm.doc.tasks.length > 0) {
			frm.doc.tasks.forEach(function(row) {
				if (row.start_date && row.end_date && row.start_date > row.end_date) {
					frappe.msgprint({
						title: __('Invalid Task Schedule'),
						indicator: 'red',
						message: __('Task "#{0}: {1}" Start Date ({2}) cannot be after End Date ({3}).', [
							row.idx,
							row.task_name || __('Unnamed'),
							row.start_date,
							row.end_date
						])
					});
					frappe.validated = false;
				}

				if (row.progress < 0 || row.progress > 100) {
					frappe.msgprint({
						title: __('Invalid Task Progress'),
						indicator: 'red',
						message: __('Task "#{0}: {1}" Progress must be between 0 and 100%.', [
							row.idx,
							row.task_name || __('Unnamed')
						])
					});
					frappe.validated = false;
				}
			});
		}
	}
});

// Reactivity on child grid modifications
frappe.ui.form.on('ITIL Project Task', {
	tasks_add: function(frm, cdt, cdn) {
		redraw_task_gantt(frm);
	},
	tasks_remove: function(frm, cdt, cdn) {
		redraw_task_gantt(frm);
	},
	task_name: function(frm, cdt, cdn) {
		redraw_task_gantt(frm);
	},
	start_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.start_date && row.end_date && row.start_date > row.end_date) {
			frappe.show_alert({
				message: __('Start Date cannot be after End Date'),
				indicator: 'orange'
			});
		}
		redraw_task_gantt(frm);
	},
	end_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.start_date && row.end_date && row.start_date > row.end_date) {
			frappe.show_alert({
				message: __('Start Date cannot be after End Date'),
				indicator: 'orange'
			});
		}
		redraw_task_gantt(frm);
	},
	status: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.status === 'Completed' && flt(row.progress) !== 100) {
			frappe.model.set_value(cdt, cdn, 'progress', 100);
		}
		redraw_task_gantt(frm);
	},
	progress: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (flt(row.progress) === 100 && row.status !== 'Completed') {
			frappe.model.set_value(cdt, cdn, 'status', 'Completed');
		} else if (flt(row.progress) < 100 && row.status === 'Completed') {
			frappe.model.set_value(cdt, cdn, 'status', 'In Progress');
		}
		redraw_task_gantt(frm);
	}
});

var current_task_view_mode = 'Month';
var active_task_gantt = null;

function render_task_gantt_section(frm) {
	var field = frm.get_field('task_gantt_html');
	if (!field || !field.$wrapper) return;

	var html = `
		<div class="itil-project-task-gantt">
			<div class="itil-task-gantt-toolbar">
				<div class="itil-task-gantt-left">
					<button type="button" class="btn btn-primary btn-xs btn-add-project-task">
						<i class="octicon octicon-plus"></i> ${__('Add Task')}
					</button>
				</div>
				<div class="itil-task-gantt-right">
					<div class="btn-group itil-task-gantt-views" role="group">
						<button type="button" class="btn btn-default btn-xs btn-task-view ${current_task_view_mode === 'Day' ? 'active btn-info' : ''}" data-mode="Day">${__('Day')}</button>
						<button type="button" class="btn btn-default btn-xs btn-task-view ${current_task_view_mode === 'Week' ? 'active btn-info' : ''}" data-mode="Week">${__('Week')}</button>
						<button type="button" class="btn btn-default btn-xs btn-task-view ${current_task_view_mode === 'Month' ? 'active btn-info' : ''}" data-mode="Month">${__('Month')}</button>
						<button type="button" class="btn btn-default btn-xs btn-task-view ${current_task_view_mode === 'Year' ? 'active btn-info' : ''}" data-mode="Year">${__('Year')}</button>
					</div>
				</div>
			</div>
			<div class="itil-task-gantt-chart-container">
				<div class="itil-project-task-gantt-chart"></div>
			</div>
		</div>
	`;

	field.$wrapper.html(html);

	// Bind toolbar buttons
	field.$wrapper.find('.btn-add-project-task').on('click', function() {
		open_add_task_dialog(frm);
	});

	field.$wrapper.find('.btn-task-view').on('click', function() {
		var mode = $(this).attr('data-mode');
		field.$wrapper.find('.btn-task-view').removeClass('active btn-info').addClass('btn-default');
		$(this).addClass('active btn-info').removeClass('btn-default');
		current_task_view_mode = mode;
		if (active_task_gantt) {
			active_task_gantt.change_view_mode(mode);
		}
	});

	// Load Gantt assets on demand
	frappe.require([
		'assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.css',
		'assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.min.js'
	], function() {
		redraw_task_gantt(frm);
	});
}

function open_add_task_dialog(frm) {
	var default_start = frm.doc.start_date || frappe.datetime.get_today();
	var default_end = frm.doc.end_date || frappe.datetime.add_days(default_start, 7);

	var d = new frappe.ui.Dialog({
		title: __('Add Project Task'),
		fields: [
			{
				label: __('Task Name'),
				fieldname: 'task_name',
				fieldtype: 'Data',
				reqd: 1
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('Assigned To'),
				fieldname: 'assigned_to',
				fieldtype: 'Link',
				options: 'User'
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: __('Start Date'),
				fieldname: 'start_date',
				fieldtype: 'Date',
				reqd: 1,
				default: default_start
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('End Date'),
				fieldname: 'end_date',
				fieldtype: 'Date',
				reqd: 1,
				default: default_end
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: __('Status'),
				fieldname: 'status',
				fieldtype: 'Select',
				options: ['Planning', 'In Progress', 'Completed', 'On Hold', 'Cancelled'],
				default: 'Planning'
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('Progress (%)'),
				fieldname: 'progress',
				fieldtype: 'Percent',
				default: 0
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: __('Description'),
				fieldname: 'description',
				fieldtype: 'Small Text'
			}
		],
		primary_action_label: __('Add Task'),
		primary_action: function(values) {
			if (!values.task_name) {
				frappe.msgprint(__('Task Name is required'));
				return;
			}
			if (!values.start_date || !values.end_date) {
				frappe.msgprint(__('Start Date and End Date are required'));
				return;
			}
			if (values.start_date > values.end_date) {
				frappe.msgprint({
					title: __('Invalid Date Range'),
					indicator: 'red',
					message: __('Start Date ({0}) cannot be after End Date ({1}).', [values.start_date, values.end_date])
				});
				return;
			}

			if (values.status === 'Completed') {
				values.progress = 100;
			} else if (flt(values.progress) === 100) {
				values.status = 'Completed';
			}

			var row = frm.add_child('tasks', values);
			frm.refresh_field('tasks');
			redraw_task_gantt(frm);
			frm.dirty();
			d.hide();

			frappe.show_alert({
				message: __('Task added to timeline'),
				indicator: 'green'
			});
		}
	});

	d.show();
}

function redraw_task_gantt(frm) {
	var field = frm.get_field('task_gantt_html');
	if (!field || !field.$wrapper) return;

	var $chart_container = field.$wrapper.find('.itil-project-task-gantt-chart');
	if (!$chart_container.length) return;

	$chart_container.empty();

	var tasks_data = frm.doc.tasks || [];

	if (!tasks_data || tasks_data.length === 0) {
		$chart_container.html(`
			<div class="itil-task-gantt-empty text-muted p-4 text-center">
				<p>${__('No tasks scheduled for this project yet.')}</p>
				<button type="button" class="btn btn-default btn-xs btn-empty-add-task">
					<i class="octicon octicon-plus"></i> ${__('Create First Task')}
				</button>
			</div>
		`);
		$chart_container.find('.btn-empty-add-task').on('click', function() {
			open_add_task_dialog(frm);
		});
		return;
	}

	var formatted_tasks = tasks_data.map(function(t, idx) {
		var start = t.start_date || frm.doc.start_date || frappe.datetime.get_today();
		var end = t.end_date || frm.doc.end_date || frappe.datetime.add_days(start, 1);
		if (start > end) {
			end = start;
		}

		var status_class = 'bar-' + frappe.scrub(t.status || 'planning');

		return {
			id: t.name || ('task_' + (idx + 1)),
			name: t.task_name || ('Task ' + (idx + 1)),
			start: start,
			end: end,
			progress: flt(t.progress) || 0,
			dependencies: '',
			custom_class: status_class,
			_meta: t,
			_idx: t.idx || (idx + 1)
		};
	});

	try {
		var GanttConstructor = window.Gantt;
		if (!GanttConstructor && typeof Gantt !== 'undefined') {
			GanttConstructor = Gantt;
		}

		if (!GanttConstructor) {
			$chart_container.html(`
				<div class="alert alert-warning m-2">
					${__('Gantt timeline library is loading...')}
				</div>
			`);
			return;
		}

		var chart_target = $('<div class="itil-task-gantt-svg-wrapper"></div>').appendTo($chart_container)[0];

		active_task_gantt = new GanttConstructor(chart_target, formatted_tasks, {
			header_height: 40,
			column_width: 30,
			step: 24,
			view_modes: ['Day', 'Week', 'Month', 'Year'],
			bar_height: 24,
			bar_corner_radius: 4,
			arrow_curve: 5,
			padding: 16,
			view_mode: current_task_view_mode,
			date_format: 'YYYY-MM-DD',
			popup_trigger: 'click',
			on_click: function(task) {
				// Highlight or focus the task in the child table grid
				frappe.show_alert({
					message: __('Task #{0}: {1} ({2}%)', [task._idx, task.name, task.progress]),
					indicator: 'blue'
				});
			},
			custom_popup_html: function(task) {
				var t = task._meta || {};
				var status_text = frappe.utils.escape_html(t.status || 'Planning');
				var assigned = t.assigned_to ? `<div class="task-pop-row"><strong>${__('Assigned')}:</strong> ${frappe.utils.escape_html(t.assigned_to)}</div>` : '';
				var desc = t.description ? `<div class="task-pop-desc">${frappe.utils.escape_html(t.description)}</div>` : '';

				return `
					<div class="itil-task-gantt-popup">
						<div class="task-pop-title">${frappe.utils.escape_html(task.name)}</div>
						<div class="task-pop-badge"><span class="badge badge-task-${frappe.scrub(t.status || 'planning')}">${status_text}</span></div>
						<div class="task-pop-row"><strong>${__('Schedule')}:</strong> ${moment(task._start).format('MMM D, YYYY')} – ${moment(task._end).format('MMM D, YYYY')}</div>
						<div class="task-pop-row"><strong>${__('Progress')}:</strong> ${task.progress}%</div>
						${assigned}
						${desc}
					</div>
				`;
			}
		});

	} catch (err) {
		console.error("Error rendering task Gantt:", err);
		$chart_container.html(`
			<div class="alert alert-danger m-2">
				${__('Error rendering task timeline')}: ${frappe.utils.escape_html(err.message)}
			</div>
		`);
	}
}
