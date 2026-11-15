/**
 * Interview Intelligence Studio Client-side Interactions
 */

document.addEventListener("DOMContentLoaded", function () {
    initWordCounter();
    initStopwatchTimer();
    initGuidanceToggles();
    initCopyAnswerButtons();
    initHeuristicEvaluator();
    initReferenceAnswerToggle();
    initAnswerModeToggles();
    initCustomizationPanels();
});

/**
 * Live Word and Character Counter
 */
function initWordCounter() {
    const textarea = document.getElementById("practiceAnswerInput");
    const wordCounterEl = document.getElementById("wordCountDisplay");
    if (!textarea || !wordCounterEl) return;

    function updateCount() {
        const text = textarea.value.trim();
        const words = text ? text.split(/\s+/).length : 0;
        const chars = text.length;
        wordCounterEl.textContent = `${words} words (${chars} chars)`;

        if (words < 30) {
            wordCounterEl.className = "text-muted small";
        } else if (words < 120) {
            wordCounterEl.className = "text-primary fw-semibold small";
        } else {
            wordCounterEl.className = "text-success fw-bold small";
        }
    }

    textarea.addEventListener("input", updateCount);
    updateCount();
}

/**
 * Optional Stopwatch Timer for Practice Mode
 */
function initStopwatchTimer() {
    const timerDisplay = document.getElementById("sessionTimerDisplay");
    if (!timerDisplay) return;

    let seconds = 0;
    const interval = setInterval(function () {
        seconds++;
        const mins = Math.floor(seconds / 60);
        const remSecs = seconds % 60;
        const fmtMins = mins < 10 ? "0" + mins : mins;
        const fmtSecs = remSecs < 10 ? "0" + remSecs : remSecs;
        timerDisplay.textContent = `${fmtMins}:${fmtSecs}`;
    }, 1000);

    const form = document.getElementById("practiceAnswerForm");
    if (form) {
        form.addEventListener("submit", function () {
            const timerInput = document.getElementById("elapsedSecondsInput");
            if (timerInput) {
                timerInput.value = seconds;
            }
        });
    }
}

/**
 * Toggle Guidance Drawers & Accordions
 */
function initGuidanceToggles() {
    const toggleBtns = document.querySelectorAll(".toggle-guidance-btn, .drawer-toggle-btn");
    toggleBtns.forEach(btn => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const drawer = document.getElementById(targetId);
            if (drawer) {
                const isHidden = drawer.style.display === "none" || drawer.classList.contains("d-none");
                if (isHidden) {
                    drawer.style.display = "block";
                    drawer.classList.remove("d-none");
                    const icon = this.querySelector(".toggle-icon");
                    if (icon) {
                        icon.className = "bi bi-chevron-up toggle-icon";
                    }
                } else {
                    drawer.style.display = "none";
                    drawer.classList.add("d-none");
                    const icon = this.querySelector(".toggle-icon");
                    if (icon) {
                        icon.className = "bi bi-chevron-down toggle-icon";
                    }
                }
            }
        });
    });
}

/**
 * Copy Complete Answer to Clipboard
 */
function initCopyAnswerButtons() {
    const copyBtns = document.querySelectorAll(".copy-answer-btn");
    copyBtns.forEach(btn => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target-text");
            let textToCopy = "";

            if (targetId) {
                const targetEl = document.getElementById(targetId);
                if (targetEl) {
                    textToCopy = targetEl.innerText || targetEl.textContent;
                }
            } else {
                textToCopy = this.getAttribute("data-answer") || "";
            }

            if (!textToCopy) return;

            navigator.clipboard.writeText(textToCopy.trim()).then(() => {
                const origHtml = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check-lg text-success me-1"></i>Copied!';
                this.classList.add("btn-success");
                this.classList.remove("btn-outline-primary", "btn-outline-secondary");

                setTimeout(() => {
                    this.innerHTML = origHtml;
                    this.classList.remove("btn-success");
                    this.classList.add("btn-outline-primary");
                }, 2000);
            }).catch(err => {
                console.error("Failed to copy text: ", err);
            });
        });
    });
}

/**
 * Toggle Reference Answer in Practice Mode
 */
function initReferenceAnswerToggle() {
    const toggleRefBtn = document.getElementById("toggleReferenceAnswerBtn");
    const refContainer = document.getElementById("referenceAnswerContainer");
    if (!toggleRefBtn || !refContainer) return;

    toggleRefBtn.addEventListener("click", function () {
        const isHidden = refContainer.classList.contains("d-none");
        if (isHidden) {
            refContainer.classList.remove("d-none");
            this.innerHTML = '<i class="bi bi-eye-slash me-1"></i>Hide Reference Answer';
            this.classList.remove("btn-outline-success");
            this.classList.add("btn-success");
        } else {
            refContainer.classList.add("d-none");
            this.innerHTML = '<i class="bi bi-eye me-1"></i>Reveal Reference Answer';
            this.classList.remove("btn-success");
            this.classList.add("btn-outline-success");
        }
    });
}

/**
 * Heuristic Evaluator AJAX Trigger in Practice Mode
 */
function initHeuristicEvaluator() {
    const evalBtn = document.getElementById("evaluateAnswerBtn");
    const textarea = document.getElementById("practiceAnswerInput");
    const feedbackBox = document.getElementById("heuristicFeedbackContainer");
    if (!evalBtn || !textarea || !feedbackBox) return;

    evalBtn.addEventListener("click", function () {
        const text = textarea.value.trim();
        if (!text) {
            alert("Please type your response in the answer box before requesting heuristic evaluation.");
            return;
        }

        const questionId = this.getAttribute("data-question-id");
        const frameworkId = this.getAttribute("data-framework-id");
        const questionText = this.getAttribute("data-question-text") || "";
        const expectedPointsAttr = this.getAttribute("data-expected-points") || "[]";
        const importantConceptsAttr = this.getAttribute("data-important-concepts") || "[]";

        let expectedPoints = [];
        let importantConcepts = [];
        try {
            expectedPoints = JSON.parse(expectedPointsAttr);
        } catch (e) {
            expectedPoints = [];
        }
        try {
            importantConcepts = JSON.parse(importantConceptsAttr);
        } catch (e) {
            importantConcepts = [];
        }

        evalBtn.disabled = true;
        evalBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Analyzing...';

        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || "";

        fetch("/api/interview/evaluate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {})
            },
            body: JSON.stringify({
                user_answer: text,
                question_id: questionId,
                framework_id: frameworkId,
                question_text: questionText,
                expected_key_points: expectedPoints,
                important_concepts: importantConcepts
            })
        })
        .then(response => response.json())
        .then(data => {
            evalBtn.disabled = false;
            evalBtn.innerHTML = '<i class="bi bi-cpu me-1"></i>Evaluate Answer';

            if (data.status === "error") {
                feedbackBox.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                feedbackBox.classList.remove("d-none");
                return;
            }

            renderFeedback(data, feedbackBox);
        })
        .catch(err => {
            evalBtn.disabled = false;
            evalBtn.innerHTML = '<i class="bi bi-cpu me-1"></i>Evaluate Answer';
            console.error("Evaluation error:", err);
            feedbackBox.innerHTML = '<div class="alert alert-warning">Could not evaluate answer at this time.</div>';
            feedbackBox.classList.remove("d-none");
        });
    });
}

/**
 * Render Heuristic Evaluation Feedback Block
 */
function renderFeedback(data, container) {
    const adherence = data.framework_adherence || {};
    const keyPoints = data.key_point_coverage || {};
    const concepts = data.important_concepts_coverage || {};
    const strengths = data.strengths || [];
    const improvements = data.areas_for_improvement || [];

    let strengthsHtml = "";
    strengths.forEach(s => {
        strengthsHtml += `<li class="small text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i>${escapeHtml(s)}</li>`;
    });

    let improvementsHtml = "";
    improvements.forEach(imp => {
        improvementsHtml += `<li class="small text-danger mb-1"><i class="bi bi-exclamation-triangle-fill me-1"></i>${escapeHtml(imp)}</li>`;
    });

    let missingConceptsHtml = "";
    if (concepts.missing && concepts.missing.length > 0) {
        concepts.missing.forEach(mc => {
            missingConceptsHtml += `<span class="tag-badge-missing"><i class="bi bi-x-circle me-1"></i>${escapeHtml(mc)}</span>`;
        });
    }

    let coveredConceptsHtml = "";
    if (concepts.covered && concepts.covered.length > 0) {
        concepts.covered.forEach(cc => {
            coveredConceptsHtml += `<span class="tag-badge-covered"><i class="bi bi-check-circle me-1"></i>${escapeHtml(cc)}</span>`;
        });
    }

    container.innerHTML = `
        <div class="heuristic-feedback-box mt-3 shadow-sm">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 pb-2 border-bottom gap-2">
                <div>
                    <h6 class="fw-bold mb-0 text-dark"><i class="bi bi-robot text-primary me-2"></i>${escapeHtml(data.evaluator_label || "Heuristic Answer Feedback")}</h6>
                    <small class="text-muted" style="font-size: 0.75rem;">Completeness: <strong>${escapeHtml(data.completeness_level || "")}</strong> | Concept Coverage: <strong>${keyPoints.coverage_pct || 0}%</strong></small>
                </div>
                <span class="badge ${keyPoints.coverage_pct >= 60 ? 'bg-success' : 'bg-warning text-dark'} px-2 py-1">
                    ${keyPoints.covered ? keyPoints.covered.length : 0} of ${keyPoints.missing ? (keyPoints.covered.length + keyPoints.missing.length) : 0} Key Points Addressed
                </span>
            </div>

            <p class="small text-dark mb-2 fw-semibold">${escapeHtml(data.actionable_feedback || "")}</p>

            ${missingConceptsHtml ? `
            <div class="mb-3 p-2 bg-white rounded border">
                <span class="text-danger fw-bold small text-uppercase d-block mb-1" style="font-size: 0.72rem;">Important Missing Concepts:</span>
                ${missingConceptsHtml}
            </div>` : ''}

            ${coveredConceptsHtml ? `
            <div class="mb-3 p-2 bg-white rounded border">
                <span class="text-success fw-bold small text-uppercase d-block mb-1" style="font-size: 0.72rem;">Observed Concepts:</span>
                ${coveredConceptsHtml}
            </div>` : ''}

            <div class="row g-2 mt-1">
                <div class="col-md-6">
                    <span class="text-muted fw-bold small text-uppercase" style="font-size: 0.72rem;">Observed Strengths:</span>
                    <ul class="list-unstyled mt-1 mb-0">${strengthsHtml || '<li class="small text-muted">No specific strengths recorded yet.</li>'}</ul>
                </div>
                <div class="col-md-6">
                    <span class="text-muted fw-bold small text-uppercase" style="font-size: 0.72rem;">Areas for Improvement:</span>
                    <ul class="list-unstyled mt-1 mb-0">${improvementsHtml || '<li class="small text-muted">No major omissions detected.</li>'}</ul>
                </div>
            </div>

            <div class="mt-2 pt-2 border-top text-muted" style="font-size: 0.72rem;">
                <i class="bi bi-info-circle me-1"></i>${escapeHtml(data.disclaimer || "")}
            </div>
        </div>
    `;
    container.classList.remove("d-none");
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Toggle between Spoken Answer and Simpler Explanation views
 */
function initAnswerModeToggles() {
    document.querySelectorAll(".ans-toggle-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const idx = this.getAttribute("data-index");
            const mode = this.getAttribute("data-mode");
            const detailedEl = document.getElementById("ans-text-" + idx);
            const simplerEl = document.getElementById("ans-simpler-" + idx);
            const parentGroup = this.closest(".ans-mode-group");
            if (parentGroup) {
                parentGroup.querySelectorAll(".ans-toggle-btn").forEach(b => {
                    b.classList.remove("active", "btn-primary");
                    b.classList.add("btn-outline-primary");
                });
                this.classList.add("active", "btn-primary");
                this.classList.remove("btn-outline-primary");
            }
            if (mode === "simpler") {
                if (detailedEl) detailedEl.classList.add("d-none");
                if (simplerEl) simplerEl.classList.remove("d-none");
            } else {
                if (simplerEl) simplerEl.classList.add("d-none");
                if (detailedEl) detailedEl.classList.remove("d-none");
            }
        });
    });
}

/**
 * Interactive Personal Detail Customization Panel
 */
function initCustomizationPanels() {
    document.querySelectorAll(".customize-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const targetId = this.getAttribute("data-target");
            const formEl = document.getElementById(targetId);
            if (formEl) {
                formEl.classList.toggle("d-none");
            }
        });
    });

    document.querySelectorAll(".close-customization-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const targetId = this.getAttribute("data-target");
            const formEl = document.getElementById(targetId);
            if (formEl) {
                formEl.classList.add("d-none");
            }
        });
    });

    document.querySelectorAll(".apply-customization-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const idx = this.getAttribute("data-index");
            const ansEl = document.getElementById("ans-text-" + idx);
            if (!ansEl) return;

            const rawText = ansEl.getAttribute("data-raw") || ansEl.innerText;
            let updatedText = rawText;

            const panel = document.getElementById("cust-form-" + idx);
            if (panel) {
                panel.querySelectorAll(".placeholder-input").forEach(input => {
                    const ph = input.getAttribute("data-placeholder");
                    const val = input.value.trim();
                    if (ph && val) {
                        updatedText = updatedText.split(ph).join(val);
                    }
                });
            }

            ansEl.innerText = updatedText;
            const origHtml = this.innerHTML;
            this.innerHTML = '<i class="bi bi-check2-circle me-1"></i>Applied!';
            this.classList.remove("btn-warning");
            this.classList.add("btn-success");
            setTimeout(() => {
                this.innerHTML = origHtml;
                this.classList.remove("btn-success");
                this.classList.add("btn-warning");
            }, 2000);
        });
    });
}
