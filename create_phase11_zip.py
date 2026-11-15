import os
import shutil
import zipfile

# 1. Create backup16 without touching backup15
if os.path.exists("ResumeMatch-AI-Final.zip") and not os.path.exists("ResumeMatch-AI-Final.backup16.zip"):
    shutil.copyfile("ResumeMatch-AI-Final.zip", "ResumeMatch-AI-Final.backup16.zip")
    print("Created ResumeMatch-AI-Final.backup16.zip successfully.")

# 2. Files and directories to package
include_dirs = ["src", "tests", "models", "data", "static", "templates", "results", "scripts"]
include_files = [
    "app.py",
    "requirements.txt",
    "README.md",
    "PHASE11_DATASET_AUDIT.md",
    "PHASE11_BASELINE_EVALUATION.md",
    "PHASE11_ERROR_ANALYSIS.md",
    "PHASE11_FEATURE_EXPERIMENTS.md",
    "PHASE11_MODEL_COMPARISON.md",
    "PHASE11_GENERALIZATION_REPORT.md",
    "PHASE11_RECOMMENDATION.md",
    "PHASE11_CHANGED_FILES.md",
    "PHASE11_TEST_RESULTS.md"
]

target_zip = "ResumeMatch-AI-Final.zip"
temp_zip = "ResumeMatch-AI-Final.new.zip"

exclude_extensions = {".pyc", ".pyo"}
exclude_dir_names = {"__pycache__", ".pytest_cache", ".git", ".venv", "env"}

total_files = 0
with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    # Add loose files
    for fname in include_files:
        if os.path.exists(fname):
            zf.write(fname, arcname=fname)
            total_files += 1

    # Add directories
    for dname in include_dirs:
        if os.path.exists(dname):
            for root, dirs, files in os.walk(dname):
                dirs[:] = [d for d in dirs if d not in exclude_dir_names]
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in exclude_extensions:
                        continue
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ".")
                    zf.write(full_path, arcname=rel_path)
                    total_files += 1

# Atomic replacement
if os.path.exists(target_zip):
    os.remove(target_zip)
os.rename(temp_zip, target_zip)

size_mb = os.path.getsize(target_zip) / (1024 * 1024)
print(f"Packaged {total_files} files into {target_zip} ({size_mb:.2f} MB).")
