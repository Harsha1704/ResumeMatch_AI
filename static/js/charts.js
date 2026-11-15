/**
 * ResumeMatch AI — Client-Side Interactive Visualizations (Chart.js)
 * Clean, lightweight, professional analytics charts.
 */

window.ResumeMatchCharts = {
    /**
     * Renders a doughnut gauge for Skill Coverage Percentage
     */
    renderCoverageDoughnut: function (canvasId, coveragePct) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const covered = Math.min(Math.max(coveragePct, 0), 100);
        const remaining = 100 - covered;

        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Matched", "Missing"],
                datasets: [{
                    data: [covered, remaining],
                    backgroundColor: ["#10b981", "#e2e8f0"],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "78%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return context.label + ": " + context.raw + "%";
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * Renders a horizontal bar chart comparing Matched, Missing Required, and Missing Preferred Skills
     */
    renderSkillGapBar: function (canvasId, matchedCount, missingReqCount, missingPrefCount) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Matched Skills", "Missing Required", "Missing Preferred"],
                datasets: [{
                    label: "Skill Count",
                    data: [matchedCount, missingReqCount, missingPrefCount],
                    backgroundColor: ["#10b981", "#ef4444", "#f59e0b"],
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) { return "Count: " + ctx.raw; }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, precision: 0 },
                        grid: { color: "#f1f5f9" }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { weight: "600" } }
                    }
                }
            }
        });
    },

    /**
     * Renders the interactive multiclass probability breakdown
     */
    renderProbabilitiesChart: function (canvasId, probDict) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !probDict) return;

        const labels = ["No Fit", "Potential Fit", "Good Fit"];
        const data = labels.map(l => (probDict[l] * 100).toFixed(1));

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Model Probability (%)",
                    data: data,
                    backgroundColor: ["#ef4444", "#f59e0b", "#10b981"],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function (val) { return val + "%"; }
                        },
                        grid: { color: "#f1f5f9" }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { weight: "600" } }
                    }
                }
            }
        });
    }
};
