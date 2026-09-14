frappe.pages['itil-practice-dashboard'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('ITIL Practice Dashboard'),
		single_column: true
	});

	page.main.addClass('itil-pd-wrapper');
	// Set false untuk matikan sidebar tanpa restore file
	var ENABLE_PRACTICE_SIDEBAR = false;
	var current_practice_slug = null;

	// Helper to resolve route practice parameter
	function get_selected_practice() {
		var params = frappe.utils.get_query_params();
		if (params && params.practice) {
			return params.practice;
		}
		var route = frappe.get_route();
		if (route.length > 1 && route[0] === 'itil-practice-dashboard') {
			return route[1];
		}
		return frappe.route_options ? frappe.route_options.practice : null;
	}

	function load_practice_dashboard() {
		var practice_param = get_selected_practice();
		if (!practice_param) {
			frappe.set_route("itil-master-dashboard");
			return;
		}

		current_practice_slug = practice_param;

		frappe.call({
			method: 'itil_master_control.practice_registry.get_practice_definition',
			args: { practice: practice_param },
			callback: function (r) {
				if (r.message && !r.message.error) {
					if (ENABLE_PRACTICE_SIDEBAR) {
						load_registry_then_render(r.message.practice, r.message.recent_records);
					} else {
						render_dashboard(r.message.practice, r.message.recent_records);
					}
				} else {
					render_error(r.message ? r.message.error : "Failed to load practice definition.");
				}
			}
		});
	}

	function load_registry_then_render(practice, recent_records) {
		frappe.call({
			method: 'itil_master_control.practice_registry.get_practice_registry',
			callback: function (r) {
				var registry = r.message || {};
				render_dashboard_with_sidebar(practice, recent_records, registry);
			},
			error: function () {
				// Fallback: tampilan lama tanpa sidebar
				render_dashboard(practice, recent_records);
			}
		});
	}

	function render_error(msg) {
		var html = `
			<div class="itil-pd-container">
				<div class="itil-pd-header-nav">
					<button class="btn btn-default btn-xs" id="btn-back-master">
						← Back to ITIL Master Dashboard
					</button>
				</div>
				<div class="itil-pd-error-card">
					<h3>Practice Context Unavailable</h3>
					<p>${frappe.utils.escape_html(msg)}</p>
					<button class="btn btn-primary btn-sm" id="btn-go-master">Go to ITIL Master Dashboard</button>
				</div>
			</div>
		`;
		page.main.html(html);
		bind_nav_events();
	}
	function build_sidebar_html(registry, active_slug) {
		var groups = [
			"General Management Practices",
			"Service Management Practices",
			"Technical Management Practices"
		];
		var short_labels = {
			"General Management Practices": "General",
			"Service Management Practices": "Service",
			"Technical Management Practices": "Technical"
		};

		var html = `
			<aside class="itil-pd-sidebar">
				<div class="itil-pd-sidebar-header">
					<div class="itil-pd-sidebar-title">ITIL Practices</div>
					<button type="button" class="btn btn-default btn-xs itil-pd-sidebar-home" id="btn-sidebar-master">
						← Master Dashboard
					</button>
				</div>
				<div class="itil-pd-sidebar-body">
		`;

		groups.forEach(function (group_name) {
			var items = registry[group_name] || [];
			if (!items.length) return;

			// Buka grup jika berisi practice yang sedang aktif
			var group_has_active = items.some(function (item) {
				var slug = item.practice_slug || frappe.scrub(item.practice_name || '').replace(/_/g, '-');
				return (slug === active_slug) || (item.practice_name === active_slug);
			});

			html += `
				<div class="itil-pd-sidebar-group ${group_has_active ? 'is-open' : ''}">
					<button type="button" class="itil-pd-sidebar-group-toggle">
						<span class="itil-pd-sidebar-group-label">${frappe.utils.escape_html(short_labels[group_name] || group_name)}</span>
						<span class="itil-pd-sidebar-group-count">${items.length}</span>
						<span class="itil-pd-sidebar-chevron">▾</span>
					</button>
					<ul class="itil-pd-sidebar-list">
			`;

			items.forEach(function (item) {
				var slug = item.practice_slug || frappe.scrub(item.practice_name || '').replace(/_/g, '-');
				var is_active = (slug === active_slug) || (item.practice_name === active_slug);
				html += `
					<li>
						<a href="#" class="itil-pd-sidebar-link ${is_active ? 'active' : ''}"
						   data-slug="${frappe.utils.escape_html(slug)}">
							<span class="itil-pd-sidebar-link-text">${frappe.utils.escape_html(item.practice_name || '')}</span>
							<span class="itil-pd-sidebar-badge">${item.open_items_count || 0}</span>
						</a>
					</li>
				`;
			});

			html += `</ul></div>`;
		});

		html += `</div></aside>`;
		return html;
	}

	function render_dashboard_with_sidebar(p, recent_records, registry) {
		render_dashboard(p, recent_records);

		var $old = page.main.children().detach();
		var practice_slug = p.practice_slug || frappe.scrub(p.practice_name).replace(/_/g, '-');
		var sidebar = build_sidebar_html(registry, practice_slug);

		page.main.html(`
			<div class="itil-pd-layout">
				${sidebar}
				<div class="itil-pd-main"></div>
			</div>
		`);
		page.main.find('.itil-pd-main').append($old);

		// Sembunyikan tombol back ganda di konten kanan (sudah ada di sidebar)
		page.main.find('.itil-pd-main .itil-pd-header-nav').hide();

		// Navigasi sidebar → Master Dashboard
		page.main.find('#btn-sidebar-master').on('click', function () {
			frappe.set_route('itil-master-dashboard');
		});

		// Klik practice
		page.main.find('.itil-pd-sidebar-link').on('click', function (e) {
			e.preventDefault();
			var slug = $(this).attr('data-slug');
			if (slug) {
				frappe.set_route('itil-practice-dashboard', { practice: slug });
			}
		});

		// Toggle collapse/expand grup
		page.main.find('.itil-pd-sidebar-group-toggle').on('click', function () {
			$(this).closest('.itil-pd-sidebar-group').toggleClass('is-open');
		});
	}
	function render_dashboard(p, recent_records) {
		page.set_title(__(p.practice_name));

		var doctype_ref = p.doctype_reference || '';
		var has_doctype = doctype_ref && doctype_ref !== 'null';
		var practice_slug = p.practice_slug || frappe.scrub(p.practice_name).replace(/_/g, '-');

		var html = `
			<div class="itil-pd-container">
				<div class="itil-pd-header-nav">
					<button class="btn btn-default btn-xs" id="btn-back-master">
						← Back to ITIL Master Dashboard
					</button>
				</div>

				<div class="itil-pd-header-card">
					<div class="itil-pd-header-main">
						<div class="itil-pd-icon-box">
							<i class="${frappe.utils.escape_html(p.icon || 'octicon octicon-checklist')}"></i>
						</div>
						<div class="itil-pd-header-text">
							<div class="itil-pd-group-badge">${frappe.utils.escape_html(p.practice_group || 'General Management Practices')}</div>
							<h1>${frappe.utils.escape_html(p.practice_name)}</h1>
							<p>${frappe.utils.escape_html(p.description || 'Standard ITIL 4 Service Management Practice.')}</p>
						</div>
					</div>
					<div class="itil-pd-header-meta">
						<div class="itil-pd-owner">Owner: <span>${frappe.utils.escape_html(p.practice_owner || 'Administrator')}</span></div>
					</div>
				</div>

				<div class="itil-pd-metrics-grid">
					<div class="itil-pd-metric-card">
						<div class="itil-pd-metric-label">Health Score</div>
						<div class="itil-pd-metric-value text-primary">${p.health_score || 100}%</div>
						<div class="itil-pd-metric-sub">Calculated Health Index</div>
					</div>
					<div class="itil-pd-metric-card">
						<div class="itil-pd-metric-label">SLA Compliance</div>
						<div class="itil-pd-metric-value text-success">${p.sla_compliance_pct || 95}%</div>
						<div class="itil-pd-metric-sub">Target SLA Adherence</div>
					</div>
					<div class="itil-pd-metric-card">
						<div class="itil-pd-metric-label">Open Items Backlog</div>
						<div class="itil-pd-metric-value text-warning">${p.open_items_count || 0}</div>
						<div class="itil-pd-metric-sub">Active Operational Items</div>
					</div>
					<div class="itil-pd-metric-card">
						<div class="itil-pd-metric-label">Trend Direction</div>
						<div class="itil-pd-metric-value">${frappe.utils.escape_html(p.trend_direction || 'Stable')}</div>
						<div class="itil-pd-metric-sub">Performance Trend</div>
					</div>
				</div>

				<div class="itil-pd-actions-bar">
					${has_doctype ? `
						<button class="btn btn-primary btn-sm" id="btn-open-list">
							<i class="octicon octicon-list-unordered"></i> View ${frappe.utils.escape_html(doctype_ref)} List
						</button>
						<button class="btn btn-default btn-sm" id="btn-create-record">
							<i class="octicon octicon-plus"></i> Create New ${frappe.utils.escape_html(doctype_ref)}
						</button>
					` : ''}
					<button class="btn btn-default btn-sm" id="btn-open-vsm">
						<i class="octicon octicon-pulse"></i> Service Value Stream Mapper
					</button>
				</div>

				<!-- Gantt Widget Container for Project Management -->
				${practice_slug === 'project-management' ? `
				<div class="itil-pd-card itil-gantt-section-card">
					<div class="itil-gantt-header">
						<div class="itil-gantt-title-group">
							<h3>Project Timeline</h3>
							<p class="text-muted">Portfolio timeline across active and scheduled ITIL projects</p>
						</div>
						<div class="itil-gantt-controls">
							<div class="btn-group itil-gantt-view-modes" role="group">
								<button type="button" class="btn btn-default btn-xs btn-gantt-view" data-mode="Day">Day</button>
								<button type="button" class="btn btn-default btn-xs btn-gantt-view" data-mode="Week">Week</button>
								<button type="button" class="btn btn-default btn-xs btn-gantt-view active btn-info" data-mode="Month">Month</button>
								<button type="button" class="btn btn-default btn-xs btn-gantt-view" data-mode="Year">Year</button>
							</div>
							<button type="button" class="btn btn-default btn-xs" id="btn-refresh-gantt" title="Refresh Timeline">
								<i class="octicon octicon-sync"></i> Refresh
							</button>
						</div>
					</div>
					<div id="itil-project-gantt-container" class="itil-gantt-container">
						<div class="itil-gantt-loading text-center text-muted p-4">
							<i class="octicon octicon-sync spin"></i> Loading project timeline...
						</div>
					</div>
				</div>
				` : ''}

				<div class="itil-pd-body-section">
					<div class="itil-pd-card">
						<h3>Recent Operational Activity</h3>
						${has_doctype ? render_recent_table(doctype_ref, recent_records) : render_phase2_placeholder(p.practice_name)}
					</div>
				</div>

				<div id="practice-widget-container" class="itil-pd-widget-container"></div>
			</div>
		`;

		page.main.html(html);

		bind_nav_events();

		if (has_doctype) {
			$('#btn-open-list').on('click', function () {
				frappe.set_route('List', doctype_ref);
			});
			$('#btn-create-record').on('click', function () {
				frappe.new_doc(doctype_ref);
			});
		}

		// Initialize Gantt if Project Management
		if (practice_slug === 'project-management') {
			init_project_gantt();
		}
	}

	function init_project_gantt() {
		var $container = $('#itil-project-gantt-container');
		if (!$container.length) return;

		// Load Frappe Gantt assets safely
		frappe.require([
			'assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.css',
			'assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.min.js'
		], function () {
			load_gantt_data();
		});

		$('#btn-refresh-gantt').on('click', function () {
			load_gantt_data();
		});
	}

	var active_gantt_instance = null;
	var current_view_mode = 'Month';

	function load_gantt_data() {
		var $container = $('#itil-project-gantt-container');
		$container.html(`
			<div class="itil-gantt-loading text-center text-muted p-4">
				<i class="octicon octicon-sync spin"></i> Loading live project records...
			</div>
		`);

		frappe.call({
			method: 'itil_master_control.project_management.api.get_project_gantt_data',
			callback: function (r) {
				if (r.message && r.message.projects) {
					render_gantt_chart(r.message.projects);
				} else if (r.exc) {
					$container.html(`
						<div class="itil-gantt-error alert alert-danger m-3">
							Failed to load project timeline data.
						</div>
					`);
				} else {
					$container.html(`
						<div class="itil-gantt-empty text-center text-muted p-4">
							No ITIL Projects available.
						</div>
					`);
				}
			},
			error: function () {
				$container.html(`
					<div class="itil-gantt-error alert alert-danger m-3">
						Failed to load project timeline data from server.
					</div>
				`);
			}
		});
	}

	function render_gantt_chart(projects) {
		var $container = $('#itil-project-gantt-container');
		$container.empty();

		if (!projects || projects.length === 0) {
			$container.html(`
				<div class="itil-gantt-empty text-center text-muted p-4">
					No ITIL Projects available.
				</div>
			`);
			return;
		}

		var tasks = projects.map(function (p) {
			return {
				id: p.id,
				name: p.project_name || p.name,
				start: p.start,
				end: p.end,
				progress: p.progress || 0,
				dependencies: '',
				custom_class: p.custom_class || 'bar-planning',
				_meta: p
			};
		});

		var gantt_target = $('<div class="itil-gantt-svg-wrapper"></div>').appendTo($container)[0];

		try {
			var GanttConstructor = window.Gantt;
			if (!GanttConstructor && typeof Gantt !== 'undefined') {
				GanttConstructor = Gantt;
			}

			if (!GanttConstructor) {
				$container.html(`
					<div class="itil-gantt-error alert alert-warning m-3">
						Frappe Gantt component could not be initialized.
					</div>
				`);
				return;
			}

			active_gantt_instance = new GanttConstructor(gantt_target, tasks, {
				header_height: 45,
				column_width: 30,
				step: 24,
				view_modes: ['Day', 'Week', 'Month', 'Year'],
				bar_height: 28,
				bar_corner_radius: 4,
				arrow_curve: 5,
				padding: 18,
				view_mode: current_view_mode,
				date_format: 'YYYY-MM-DD',
				popup_trigger: 'click',
				on_click: function (task) {
					frappe.set_route('Form', 'ITIL Project', task.id);
				},
				custom_popup_html: function (task) {
					var p = task._meta || {};
					var status_badge = frappe.utils.escape_html(p.status || 'Planning');
					var manager = p.project_manager ? `<div class="gantt-pop-row"><strong>Manager:</strong> ${frappe.utils.escape_html(p.project_manager)}</div>` : '';
					var cr = p.linked_change_request ? `<div class="gantt-pop-row"><strong>Change Req:</strong> ${frappe.utils.escape_html(p.linked_change_request)}</div>` : '';
					var desc = p.description ? `<div class="gantt-pop-desc">${frappe.utils.escape_html(p.description)}</div>` : '';

					return `
						<div class="itil-gantt-popup-card">
							<div class="gantt-pop-title">${frappe.utils.escape_html(task.name)} (${frappe.utils.escape_html(task.id)})</div>
							<div class="gantt-pop-status"><span class="badge badge-status-${frappe.scrub(p.status || 'planning')}">${status_badge}</span></div>
							<div class="gantt-pop-row"><strong>Schedule:</strong> ${moment(task._start).format('MMM D, YYYY')} – ${moment(task._end).format('MMM D, YYYY')}</div>
							<div class="gantt-pop-row"><strong>Progress:</strong> ${task.progress}%</div>
							${manager}
							${cr}
							${desc}
							<div class="gantt-pop-action text-muted"><small>Click bar to open ITIL Project form</small></div>
						</div>
					`;
				}
			});

			// Bind view mode switch buttons
			$('.btn-gantt-view').off('click').on('click', function () {
				var mode = $(this).attr('data-mode');
				$('.btn-gantt-view').removeClass('active btn-info').addClass('btn-default');
				$(this).addClass('active btn-info').removeClass('btn-default');
				current_view_mode = mode;
				if (active_gantt_instance) {
					active_gantt_instance.change_view_mode(mode);
				}
			});

		} catch (err) {
			console.error("Error rendering Gantt chart:", err);
			$container.html(`
				<div class="itil-gantt-error alert alert-danger m-3">
					Error rendering timeline: ${frappe.utils.escape_html(err.message)}
				</div>
			`);
		}
	}

	function render_recent_table(doctype_ref, records) {
		if (!records || records.length === 0) {
			return `<div class="itil-pd-empty-state">No recent ${frappe.utils.escape_html(doctype_ref)} records found.</div>`;
		}
		var rows = records.map(function (r) {
			return `
				<tr>
					<td><a class="itil-pd-link" data-doctype="${frappe.utils.escape_html(doctype_ref)}" data-name="${frappe.utils.escape_html(r.name)}">${frappe.utils.escape_html(r.name)}</a></td>
					<td>${frappe.datetime.global_date_format(r.modified)}</td>
					<td>${frappe.utils.escape_html(r.owner || 'System')}</td>
				</tr>
			`;
		}).join('');

		return `
			<table class="table table-bordered table-dark-custom">
				<thead>
					<tr>
						<th>Name / ID</th>
						<th>Last Modified</th>
						<th>Owner</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		`;
	}

	function render_phase2_placeholder(practice_name) {
		return `
			<div class="itil-pd-phase2-card">
				<div class="itil-pd-phase2-icon"><i class="octicon octicon-tools"></i></div>
				<h4>Phase 2 Operational Model Candidate</h4>
				<p>The operational DocType for <strong>${frappe.utils.escape_html(practice_name)}</strong> is scheduled for full workflow implementation in Phase 2.</p>
				<p>Practice governance, central registry metadata, and health indicators are fully active.</p>
			</div>
		`;
	}

	function bind_nav_events() {
		$('#btn-back-master, #btn-go-master').on('click', function () {
			frappe.set_route('itil-master-dashboard');
		});
		$('#btn-open-vsm').on('click', function () {
			frappe.set_route('service-value-stream-mapper');
		});
		page.main.find('.itil-pd-link').on('click', function () {
			var dt = $(this).attr('data-doctype');
			var name = $(this).attr('data-name');
			frappe.set_route('Form', dt, name);
		});
	}

	// Trigger load on page show
	$(wrapper).on('show', function () {
		load_practice_dashboard();
	});

	load_practice_dashboard();
};
