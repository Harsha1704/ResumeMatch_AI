import pandas as pd
import re

def norm(t):
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", str(t).lower()).split())

tr = pd.read_parquet("manifests/v1/dual_unseen_train_v1.parquet")
vl = pd.read_parquet("manifests/v1/dual_unseen_val_v1.parquet")

tr_norm = {norm(t): t for t in tr["resume_text"]}
for t in vl["resume_text"].unique():
    nt = norm(t)
    if nt in tr_norm:
        orig_tr = tr_norm[nt]
        print("Found match!")
        print("Length:", len(nt))
        print("Raw equal:", t == orig_tr)
        if t != orig_tr:
            print("Difference in whitespace/punct only!")
            for i in range(min(len(t), len(orig_tr))):
                if t[i] != orig_tr[i]:
                    print(f"Diff at char {i}: {repr(t[i:i+20])} vs {repr(orig_tr[i:i+20])}")
                    break
