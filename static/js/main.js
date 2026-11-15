/**
 * ResumeMatch AI — Main Interactive UI Logic
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Sidebar Toggle
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("collapsed");
            localStorage.setItem("sidebarCollapsed", sidebar.classList.contains("collapsed"));
        });

        // Restore saved preference
        if (localStorage.getItem("sidebarCollapsed") === "true") {
            sidebar.classList.add("collapsed");
        }
    }

    // 2. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 6000);
    });

    // 3. Print Results Button helper
    const printBtn = document.getElementById("printResultsBtn");
    if (printBtn) {
        printBtn.addEventListener("click", function () {
            window.print();
        });
    }

    // 4. Copy Analysis ID helper
    const copyIdBtn = document.getElementById("copyAnalysisIdBtn");
    if (copyIdBtn) {
        copyIdBtn.addEventListener("click", function () {
            const analysisId = this.getAttribute("data-id");
            if (analysisId) {
                navigator.clipboard.writeText(analysisId).then(function () {
                    const originalText = copyIdBtn.innerHTML;
                    copyIdBtn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
                    setTimeout(() => { copyIdBtn.innerHTML = originalText; }, 2000);
                });
            }
        });
    }
});
