import sys
import os
import torch
import psutil
import hashlib

def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

print("=" * 60)
print("STAGE 1 & 2: SYSTEM ENVIRONMENT & HARDWARE AUDIT")
print("=" * 60)
print("Python Version:", sys.version)
print("PyTorch Version:", torch.__version__)
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device Count:", torch.cuda.device_count())
    print("Device Name:", torch.cuda.get_device_name(0))
    print("VRAM:", round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2), "GB")
else:
    print("CUDA Note: Running on CPU.")

print("Physical CPU Cores:", psutil.cpu_count(logical=False))
print("Logical CPU Cores:", psutil.cpu_count(logical=True))
print("Total RAM (GB):", round(psutil.virtual_memory().total / (1024**3), 2))
print("Available RAM (GB):", round(psutil.virtual_memory().available / (1024**3), 2))

# Verify production model
prod_path = "models/best_model.joblib"
if os.path.exists(prod_path):
    prod_sha = get_file_hash(prod_path)
    print("\nProduction Checkpoint:", prod_path)
    print("SHA-256:", prod_sha)
    expected_sha = "1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A"
    assert prod_sha.lower() == expected_sha.lower(), "Production checkpoint SHA mismatch!"
    print("Production Model Hash Integrity: VERIFIED MATCH.")
else:
    print("Warning: Production model not found at", prod_path)

# Inspect production model object
import joblib
prod_obj = joblib.load(prod_path)
print("Production Object Type:", type(prod_obj))
if hasattr(prod_obj, "named_steps"):
    print("Pipeline steps:", list(prod_obj.named_steps.keys()))
    for name, step in prod_obj.named_steps.items():
        print(f"  Step '{name}': {type(step)}")
