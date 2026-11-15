import os
import shutil
import zipfile

# 1. Preserve backup15
if os.path.exists("ResumeMatch-AI-Final.zip"):
    shutil.copyfile("ResumeMatch-AI-Final.zip", "ResumeMatch-AI-Final.backup15.zip")
    print("Created ResumeMatch-AI-Final.backup15.zip successfully.")

# 2. Files and directories to package
include_dirs = ["src", "tests", "models", "data", "static", "templates", "results"]
include_files = [
    "app.py",
    "requirements.txt",
    "README.md",
    "run_phase10_audit_suite.py",
    "PHASE10_REAL_WORLD_AUDIT.md",
    "PHASE10_FAILURE_CASES.md",
    "PHASE10_QUALITY_METRICS.md",
    "PHASE10_CHANGED_FILES.md",
    "PHASE10_TEST_RESULTS.md",
    "PHASE10_HUMAN_EVALUATION_PACKAGE.md"
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
                # Filter out excluded directories
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
