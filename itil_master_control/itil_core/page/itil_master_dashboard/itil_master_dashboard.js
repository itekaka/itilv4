frappe.pages['itil-master-dashboard'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __(''),
        single_column: true
    });
    // Custom breadcrumb → mengarah ke dashboard ini (bukan ke workspace lama)
    frappe.breadcrumbs.clear();
    frappe.breadcrumbs.add({
        type: 'Custom',
        label: __('ITIL 4 Master Control'),
        route: '/app/itil-master-dashboard'
    });

    const $wrapper = $(wrapper);
    $wrapper.find(".page-head").hide();


    function getTrendIcon(trend) {
        if (trend === "Improving" || trend === "up") {
            return `<span class="itil-trend itil-trend-up">↑</span>`;
        }
        return `<span class="itil-trend itil-trend-down">↓</span>`;
    }

    function createPracticeCard(p) {
        var slug = frappe.utils.escape_html(p.practice_slug || frappe.scrub(p.practice_name).replace(/_/g, '-'));
        var title = frappe.utils.escape_html(p.practice_name);
        var score = (p.health_score !== undefined && p.health_score !== null) ? (p.health_score + "%") : "100%";
        var backlog = (p.open_items_count !== undefined && p.open_items_count !== null) ? p.open_items_count : 0;
        var doctype_ref = p.doctype_reference ? frappe.utils.escape_html(p.doctype_reference) : "Operational Model";

        return `
            <div class="itil-practice-card" data-slug="${slug}">
                <div class="itil-practice-card-title">
                    ${title}
                </div>
                <div class="itil-practice-card-metric">
                    ${doctype_ref}
                </div>
                <div class="itil-practice-card-value">
                    Open Backlog: ${backlog}
                </div>
                <div class="itil-practice-card-footer">
                    <span class="itil-health-score">
                        Health Score <strong>${score}</strong>
                    </span>
                    ${getTrendIcon(p.trend_direction)}
                </div>
            </div>
        `;
    }

    function createSection(group_title, number_str, class_name, items) {
        return `
            <section class="itil-practice-section itil-${class_name}-section">
                <div class="itil-section-header">
                    <div class="itil-section-title-group">
                        <span class="itil-section-number">${number_str}</span>
                        <h2>${group_title}</h2>
                    </div>
                    <span class="itil-practice-count">${items.length} Practices</span>
                </div>
                <div class="itil-practice-grid">
                    ${items.map(createPracticeCard).join("")}
                </div>
            </section>
        `;
    }

    function load_dashboard_registry() {
        frappe.call({
            method: 'itil_master_control.practice_registry.get_practice_registry',
            callback: function (r) {
                if (r.message) {
                    render_dashboard(r.message);
                }
            }
        });
    }

    function render_dashboard(registry) {
        const general = registry["General Management Practices"] || [];
        const service = registry["Service Management Practices"] || [];
        const technical = registry["Technical Management Practices"] || [];

        const sections_html = [
            createSection("General Management Practices", "01", "general", general),
            createSection("Service Management Practices", "02", "service", service),
            createSection("Technical Management Practices", "03", "technical", technical)
        ].join("");

        $wrapper.find(".layout-main-section").html(`
            <div class="itil-dashboard">
                <div class="itil-dashboard-header">
                    <div class="itil-dashboard-title-area">
                    
                        
                        <h1>ITIL 4 Master Control Panel</h1>
                        <p>Enterprise ITSM governance overview across all 24 ITIL 4 practices.</p>
                    </div>
                    <div class="itil-system-status">
                        <span class="itil-status-dot"></span>
                        System Operational
                    </div>
                </div>

                <div class="itil-dashboard-content">
                    ${sections_html}
                </div>
            </div>
        `);

        // Attach click navigation using Frappe-native route
        $wrapper.find('.itil-practice-card').css('cursor', 'pointer').on('click', function () {
            const slug = $(this).attr('data-slug');
            if (slug) {
                frappe.set_route('itil-practice-dashboard', { practice: slug });
            }
        });
    }

    load_dashboard_registry();
};
