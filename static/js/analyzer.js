/**
 * ResumeMatch AI — Resume Analyzer Interaction Handler
 * Supports Drag & Drop, File Validation, Live Counters, and Submission Feedback
 */

document.addEventListener("DOMContentLoaded", function () {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("resume_file");
    const filePreview = document.getElementById("filePreview");
    const fileNameDisplay = document.getElementById("fileNameDisplay");
    const fileSizeDisplay = document.getElementById("fileSizeDisplay");
    const removeFileBtn = document.getElementById("removeFileBtn");
    const jobTextarea = document.getElementById("job_description");
    const charCounter = document.getElementById("jobCharCount");
    const clearJobBtn = document.getElementById("clearJobBtn");
    const analyzeForm = document.getElementById("analyzeForm");
    const loadingOverlay = document.getElementById("loading-overlay");

    // 1. Drag & Drop File Handling
    if (dropzone && fileInput) {
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            }, false);
        });

        dropzone.addEventListener("drop", function (e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFileDisplay(files[0]);
            }
        });

        dropzone.addEventListener("click", function () {
            fileInput.click();
        });

        fileInput.addEventListener("change", function () {
            if (fileInput.files.length > 0) {
                updateFileDisplay(fileInput.files[0]);
            }
        });
    }

    function updateFileDisplay(file) {
        if (!file) return;

        // Check size (16MB limit)
        if (file.size > 16 * 1024 * 1024) {
            alert("File exceeds maximum allowed size of 16 MB.");
            clearFileInput();
            return;
        }

        const validExts = [".pdf", ".docx", ".txt"];
        const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
        if (!validExts.includes(ext)) {
            alert("Invalid file format. Please upload a PDF, DOCX, or TXT resume.");
            clearFileInput();
            return;
        }

        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = (file.size / 1024).toFixed(1) + " KB (" + ext.toUpperCase().replace(".", "") + ")";
        dropzone.style.display = "none";
        filePreview.style.display = "block";
    }

    function clearFileInput() {
        if (fileInput) fileInput.value = "";
        if (filePreview) filePreview.style.display = "none";
        if (dropzone) dropzone.style.display = "block";
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            clearFileInput();
        });
    }

    // 2. Character counter for job description
    if (jobTextarea && charCounter) {
        function updateCount() {
            const len = jobTextarea.value.length;
            charCounter.textContent = len.toLocaleString() + " chars";
        }
        jobTextarea.addEventListener("input", updateCount);
        updateCount();
    }

    // 3. Clear Job Description
    if (clearJobBtn && jobTextarea) {
        clearJobBtn.addEventListener("click", function () {
            jobTextarea.value = "";
            if (charCounter) charCounter.textContent = "0 chars";
        });
    }

    // 4. Form Submit with Loading Feedback
    if (analyzeForm && loadingOverlay) {
        analyzeForm.addEventListener("submit", function (e) {
            const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
            const pastedResume = document.getElementById("resume_text");
            const hasPasted = pastedResume && pastedResume.value.trim().length > 0;
            const hasJob = jobTextarea && jobTextarea.value.trim().length > 0;

            if (!hasFile && !hasPasted) {
                e.preventDefault();
                alert("Please provide a resume by uploading a file (PDF, DOCX, TXT) or pasting text.");
                return;
            }

            if (!hasJob) {
                e.preventDefault();
                alert("Please provide the target job description.");
                return;
            }

            // Display loading overlay
            loadingOverlay.style.display = "flex";
        });
    }
});
