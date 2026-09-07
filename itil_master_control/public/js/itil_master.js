frappe.provide("frappe.itil_master_control");

frappe.itil_master_control.render_dashboard = function (wrapper) {
    const container = $(wrapper).find("#itil4-master-control-panel");

    if (!container.length) {
        return;
    }

    container.html(`
        <div class="itil-dashboard">
            <div class="itil-dashboard-loading">
                Loading ITIL 4 Practice Dashboard...
            </div>
        </div>
    `);

    frappe.call({
        method: "itil_master_control.api.get_practice_dashboard_metrics",

        callback: function (r) {
            const groupedMetrics = r.message || {};

            const practiceGroups = [
                "General Management Practices",
                "Service Management Practices",
                "Technical Management Practices"
            ];

            let html = "";

            practiceGroups.forEach(function (groupName) {
                const practices = groupedMetrics[groupName] || [];

                html += `
                    <section class="itil-practice-group">
                        <h2 class="itil-practice-group-title">
                            ${frappe.utils.escape_html(groupName)}
                        </h2>

                        <div class="itil-dashboard-grid">
                `;

                practices.forEach(function (p) {
                    const healthScore = p.health_score || 0;

                    const trendIcon =
                        p.trend_direction === "Improving"
                            ? "▲"
                            : p.trend_direction === "Declining"
                                ? "▼"
                                : "●";

                    const status =
                        healthScore >= 90
                            ? "healthy"
                            : healthScore >= 75
                                ? "warning"
                                : "critical";

                    const groupClass = (p.practice_group || "")
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, "-");

                    html += `
                        <div class="itil-card practice-group-${groupClass} status-${status}">

                            <div class="itil-card-title">
                                ${frappe.utils.escape_html(p.practice_name || p.name)}
                            </div>

                            <div class="itil-card-sparkline">
                                ${frappe.utils.escape_html(p.icon || "●")}
                            </div>

                            <div class="itil-card-footer">
                                <span class="itil-card-score">
                                    Health Score:
                                    <b>${healthScore}</b>
                                </span>

                                <span class="itil-card-trend">
                                    ${trendIcon}
                                </span>
                            </div>

                            <div class="itil-card-subinfo">
                                SLA: ${p.sla_compliance_pct || 0}%
                                |
                                Open Items: ${p.open_items_count || 0}
                            </div>

                        </div>
                    `;
                });

                html += `
                        </div>
                    </section>
                `;
            });

            container.html(html);
        },

        error: function () {
            container.html(`
                <div class="itil-dashboard-error">
                    Failed to load ITIL Practice Dashboard.
                </div>
            `);
        }
    });
};


frappe.router.on("change", function () {
    setTimeout(function () {

        if (
            frappe.get_route_str() !==
            "workspace/ITIL 4 Master Control"
        ) {
            return;
        }

        const workspace = $(".desk-page");

        if (!workspace.length) {
            return;
        }

        if ($("#itil4-master-control-panel").length) {
            return;
        }

        const pageContent = workspace.find(".page-content");

        if (!pageContent.length) {
            return;
        }

        pageContent.empty();

        pageContent.append(`
            <div id="itil4-master-control-panel"></div>
        `);

        frappe.itil_master_control.render_dashboard(pageContent);

    }, 500);
});

// Matikan logo Frappe secara otomatis
function killFrappeLogo() {
    const logo = document.querySelector('a.navbar-brand.navbar-home');
    if (logo) {
        logo.removeAttribute('href');
        logo.style.pointerEvents = 'none';
        logo.style.cursor = 'default';
        logo.onclick = function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            return false;
        };
    }
}

// Jalankan setelah Frappe siap
frappe.ready(function () {
    killFrappeLogo();
    // Jaga-jaga kalau navbar di-render ulang
    setTimeout(killFrappeLogo, 500);
    setTimeout(killFrappeLogo, 1500);
    setInterval(killFrappeLogo, 2000);
});