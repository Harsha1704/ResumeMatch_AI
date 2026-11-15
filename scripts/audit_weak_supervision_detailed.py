import os
import sys
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score

sys.path.insert(0, ".")
from src.phase12f.weak_supervision import WeakLabelingSystem, NO_FIT, POTENTIAL_FIT, GOOD_FIT, ABSTAIN, CLASSES

job_tr = pd.read_parquet("manifests/v1/job_disjoint_train_v1.parquet")
resumes = job_tr["resume_text"].tolist()
jobs = job_tr["job_description_text"].tolist()
y_true_str = job_tr["label"].tolist()
y_true_int = [CLASSES.index(l) for l in y_true_str]

weak_sys = WeakLabelingSystem()
L = weak_sys.apply_lfs(resumes, jobs)
N, M = L.shape

print("=== DETAILED WEAK SUPERVISION LF AUDIT ===")
print(f"Total Evaluated Pairs: {N}")

lf_names = [name for name, _ in weak_sys.labeling_functions]
lf_audit_results = {}

for j, name in enumerate(lf_names):
    votes = L[:, j]
    active_mask = (votes != ABSTAIN)
    n_active = np.sum(active_mask)
    cov = n_active / N
    
    # Class distribution among non-abstain
    unique, counts = np.unique(votes[active_mask], return_counts=True)
    dist = {CLASSES[u]: int(c) for u, c in zip(unique, counts)}
    
    # Agreement with ground truth on active subset
    if n_active > 0:
        active_true = np.array(y_true_int)[active_mask]
        active_pred = votes[active_mask]
        acc_vs_truth = accuracy_score(active_true, active_pred)
        kappa_vs_truth = cohen_kappa_score(active_true, active_pred)
    else:
        acc_vs_truth, kappa_vs_truth = 0.0, 0.0
        
    print(f"\nLF {j+1}: {name}")
    print(f"  Coverage: {n_active} / {N} ({cov*100:.2f}%)")
    print(f"  Emitted Class Distribution: {dist}")
    print(f"  Accuracy vs Ground Truth (on active): {acc_vs_truth*100:.2f}%")
    print(f"  Cohen's Kappa vs Ground Truth: {kappa_vs_truth:.4f}")
    
    lf_audit_results[name] = {
        "coverage": round(cov, 4),
        "active_count": int(n_active),
        "class_distribution": dist,
        "acc_vs_truth": round(acc_vs_truth, 4),
        "kappa_vs_truth": round(kappa_vs_truth, 4)
    }

# Aggregated weak labels
weak_labels, weak_conf = weak_sys.aggregate_weak_labels(L)
active_agg = (weak_labels != -1)
high_conf = (weak_conf >= 0.70) & active_agg
print(f"\nAggregated Weak Labels:")
print(f"  Total with at least one vote: {np.sum(active_agg)} / {N} ({np.mean(active_agg)*100:.2f}%)")
print(f"  High confidence (>= 0.70): {np.sum(high_conf)} / {N} ({np.mean(high_conf)*100:.2f}%)")
unique_agg, counts_agg = np.unique(weak_labels[high_conf], return_counts=True)
print(f"  High-confidence class distribution: {[CLASSES[u] + ': ' + str(c) for u, c in zip(unique_agg, counts_agg)]}")
print(f"  High-confidence Accuracy vs Ground Truth: {accuracy_score(np.array(y_true_int)[high_conf], weak_labels[high_conf])*100:.2f}%")
print(f"  High-confidence Kappa vs Ground Truth: {cohen_kappa_score(np.array(y_true_int)[high_conf], weak_labels[high_conf]):.4f}")
