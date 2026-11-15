/**
 * Personalized Career Mentor Client-side Interactivity
 */

document.addEventListener("DOMContentLoaded", function () {
    initDisplayNameEditor();
    initTargetRoleEditor();
    initEducationConfirmation();
    initCategoryFilters();
    initAccordionControls();
    initQuickActionScrolls();
    initTaskStatusHandlers();
    initStudyPlanForm();
});

/**
 * Allows user to edit preferred display name dynamically
 */
function initDisplayNameEditor() {
    const editBtn = document.getElementById("editDisplayNameBtn");
    const saveBtn = document.getElementById("saveDisplayNameBtn");
    const cancelBtn = document.getElementById("cancelDisplayNameBtn");
    const nameInputGroup = document.getElementById("nameInputGroup");
    const nameDisplayGroup = document.getElementById("nameDisplayGroup");
    const nameInput = document.getElementById("candidateNameInput");
    const nameDisplayText = document.getElementById("candidateDisplayNameText");
    const mentorTitleText = document.getElementById("mentorTitleText");

    if (!editBtn || !nameInputGroup) return;

    editBtn.addEventListener("click", function () {
        nameDisplayGroup.classList.add("d-none");
        nameInputGroup.classList.remove("d-none");
        nameInput.focus();
    });

    cancelBtn.addEventListener("click", function () {
        nameInputGroup.classList.add("d-none");
        nameDisplayGroup.classList.remove("d-none");
    });

    saveBtn.addEventListener("click", function () {
        const newName = nameInput.value.trim();
        if (!newName) {
            alert("Please enter a valid display name.");
            return;
        }

        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        fetch("/api/mentor/update-name", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ preferred_name: newName })
        })
        .then(res => res.json())
        .then(data => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-lg"></i>';
            if (data.status === "success") {
                if (nameDisplayText) nameDisplayText.textContent = data.preferred_name;
                if (mentorTitleText) mentorTitleText.textContent = data.mentor_title;
                nameInputGroup.classList.add("d-none");
                nameDisplayGroup.classList.remove("d-none");
                // Reload to refresh full greeting text smoothly
                window.location.reload();
            }
        })
        .catch(err => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-lg"></i>';
            console.error("Failed to update name:", err);
        });
    });
}

/**
 * Quick Action Button Smooth Scrolling
 */
function initQuickActionScrolls() {
    const actionBtns = document.querySelectorAll(".quick-action-btn[data-target]");
    actionBtns.forEach(btn => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
                targetEl.classList.add("highlight-pulse");
                setTimeout(() => targetEl.classList.remove("highlight-pulse"), 1500);
            }
        });
    });
}

/**
 * Task Status Change AJAX Handler
 */
function initTaskStatusHandlers() {
    const statusSelects = document.querySelectorAll(".stage-status-select");
    statusSelects.forEach(sel => {
        sel.addEventListener("change", function () {
            const taskKey = this.getAttribute("data-task-key");
            const newStatus = this.value;

            // Update class for visual styling
            this.className = `form-select form-select-sm stage-status-select status-${newStatus.replace(/\s+/g, '_')}`;

            fetch("/api/mentor/progress", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    task_key: taskKey,
                    status: newStatus
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "success" && data.progress_summary) {
                    updateProgressUI(data.progress_summary);
                }
            })
            .catch(err => console.error("Error updating task progress:", err));
        });
    });
}

/**
 * Updates Progress Metrics in real time
 */
function updateProgressUI(summary) {
    const pctBar = document.getElementById("progressPercentageBar");
    const pctText = document.getElementById("progressPercentageText");
    const compText = document.getElementById("completedTasksCountText");
    const remText = document.getElementById("remainingTasksCountText");
    const encouragementText = document.getElementById("mentorEncouragementText");

    if (pctBar) pctBar.style.width = `${summary.completion_percentage}%`;
    if (pctText) pctText.textContent = `${summary.completion_percentage}%`;
    if (compText) compText.textContent = summary.completed_tasks;
    if (remText) remText.textContent = summary.total_tasks - summary.completed_tasks;

    if (encouragementText && summary.encouragement_message) {
        encouragementText.textContent = summary.encouragement_message;
    }
}

/**
 * Study Plan Form Re-calculation
 */
function initStudyPlanForm() {
    const planForm = document.getElementById("studyPlanConfigForm");
    if (!planForm) return;

    planForm.addEventListener("submit", function (e) {
        // Allow standard form submission or AJAX reload
    });
}

/**
 * Allows user to edit target role dynamically
 */
function initTargetRoleEditor() {
    const editBtn = document.getElementById("editTargetRoleBtn");
    const saveBtn = document.getElementById("saveTargetRoleBtn");
    const cancelBtn = document.getElementById("cancelTargetRoleBtn");
    const inputGroup = document.getElementById("targetRoleInputGroup");
    const input = document.getElementById("targetRoleInput");

    if (!editBtn || !inputGroup) return;

    editBtn.addEventListener("click", function () {
        inputGroup.classList.remove("d-none");
        if (input) input.focus();
    });

    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            inputGroup.classList.add("d-none");
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener("click", function () {
            const newRole = input.value.trim();
            if (!newRole) {
                alert("Please enter a target role.");
                return;
            }
            fetch("/api/candidate/update-role", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target_role: newRole })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.reload();
                }
            })
            .catch(err => console.error("Failed to update target role:", err));
        });
    }
}

/**
 * Allows candidate to confirm their educational degree qualification
 */
function initEducationConfirmation() {
    const confirmBtn = document.getElementById("confirmEduBtn");
    const saveBtn = document.getElementById("saveEduBtn");
    const cancelBtn = document.getElementById("cancelEduBtn");
    const inputGroup = document.getElementById("eduInputGroup");
    const input = document.getElementById("eduInput");

    if (!confirmBtn || !inputGroup) return;

    confirmBtn.addEventListener("click", function () {
        inputGroup.classList.remove("d-none");
        if (input) input.focus();
    });

    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            inputGroup.classList.add("d-none");
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener("click", function () {
            const eduVal = input.value.trim();
            if (!eduVal) {
                alert("Please enter your degree / educational qualification.");
                return;
            }
            fetch("/api/candidate/confirm-education", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ education: eduVal })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.reload();
                }
            })
            .catch(err => console.error("Failed to confirm education:", err));
        });
    }
}

/**
 * Filter gaps by category (Core Technical, Tools, Professional, Productivity)
 */
function initCategoryFilters() {
    const filterBtns = document.querySelectorAll(".cat-filter-btn");
    const gapCards = document.querySelectorAll(".gap-item-card");

    if (!filterBtns.length) return;

    filterBtns.forEach(btn => {
        btn.addEventListener("click", function () {
            filterBtns.forEach(b => {
                b.classList.remove("active");
                b.classList.remove("btn-primary");
                b.classList.add("btn-outline-primary");
            });
            this.classList.add("active");
            this.classList.remove("btn-outline-primary");
            this.classList.add("btn-primary");

            const selectedCat = this.getAttribute("data-category");
            const collapseRemaining = document.getElementById("collapseRemainingGaps");
            if (collapseRemaining && selectedCat !== "all") {
                collapseRemaining.classList.add("show");
            }

            gapCards.forEach(card => {
                const cardCat = card.getAttribute("data-category");
                if (selectedCat === "all" || cardCat === selectedCat) {
                    card.style.display = "";
                } else {
                    card.style.display = "none";
                }
            });
        });
    });
}

/**
 * Expand and collapse all roadmaps in accordion
 */
function initAccordionControls() {
    const expandBtn = document.getElementById("expandAllRoadmapsBtn");
    const collapseBtn = document.getElementById("collapseAllRoadmapsBtn");

    if (expandBtn) {
        expandBtn.addEventListener("click", function () {
            const collapsibles = document.querySelectorAll("#roadmapsAccordion .accordion-collapse");
            collapsibles.forEach(el => {
                el.classList.add("show");
            });
            const buttons = document.querySelectorAll("#roadmapsAccordion .accordion-button");
            buttons.forEach(btn => {
                btn.classList.remove("collapsed");
                btn.setAttribute("aria-expanded", "true");
            });
        });
    }

    if (collapseBtn) {
        collapseBtn.addEventListener("click", function () {
            const collapsibles = document.querySelectorAll("#roadmapsAccordion .accordion-collapse");
            collapsibles.forEach(el => {
                el.classList.remove("show");
            });
            const buttons = document.querySelectorAll("#roadmapsAccordion .accordion-button");
            buttons.forEach(btn => {
                btn.classList.add("collapsed");
                btn.setAttribute("aria-expanded", "false");
            });
        });
    }
}
