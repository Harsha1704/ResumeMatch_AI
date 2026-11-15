"""
scripts/phase12f3_2/compute_contrastive_statistics.py
Recalculates statistical confidence intervals and paired significance tests for contrastive learning:
- 5 individual paired accuracy differences across seeds.
- Mean difference, sample standard deviation, sample standard error.
- Two-sided 95% Student-t interval across seeds (df=4).
- Paired bootstrap interval across validation examples (10,000 resamples).
- McNemar's exact test (binomial) on model predictions.
- Per-seed Macro F1 and Balanced Accuracy differences.
- Explanation of previously reported interval [+4.04%, +8.80%].
"""

import json
from pathlib import Path
import numpy as np
import scipy.stats as stats
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits
from src.evaluation.split_validator import hash_text
from scripts.phase12f3_1.reproduce_contrastive_downstream import (
    ContrastiveProjector,
    train_contrastive_encoder_on_train_only,
    SEEDS,
    CACHE_PATH
)

def build_features(u, v):
    cos = np.sum(u * v, axis=1, keepdims=True) / (np.linalg.norm(u, axis=1, keepdims=True) * np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return np.hstack([u, v, u * v, np.abs(u - v), cos])

REPO_ROOT = Path("D:/skillsync1")
OUT_DIR = REPO_ROOT / "experiments" / "phase12f3_2" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 80)
    print("PHASE 12F.3.2: CONTRASTIVE STATISTICAL CONFIDENCE INTERVAL AUDIT")
    print("=" * 80)
    
    dual_tr, dual_vl = load_guarded_dual_unseen_splits()
    y_tr = dual_tr["label"].values
    y_vl = dual_vl["label"].values
    
    cached_data = np.load(CACHE_PATH, allow_pickle=True)
    res_emb_dict = {h: cached_data[f"res_{h}"] for h in cached_data["res_hashes"]}
    job_emb_dict = {h: cached_data[f"job_{h}"] for h in cached_data["job_hashes"]}
    
    u_tr = np.array([res_emb_dict[hash_text(t)] for t in dual_tr["resume_text"]], dtype=np.float32)
    v_tr = np.array([job_emb_dict[hash_text(t)] for t in dual_tr["job_description_text"]], dtype=np.float32)
    u_vl = np.array([res_emb_dict[hash_text(t)] for t in dual_vl["resume_text"]], dtype=np.float32)
    v_vl = np.array([job_emb_dict[hash_text(t)] for t in dual_vl["job_description_text"]], dtype=np.float32)
    
    X_raw_tr = build_features(u_tr, v_tr)
    X_raw_vl = build_features(u_vl, v_vl)
    
    per_seed_data = []
    all_raw_preds = []
    all_proj_preds = []
    
    for s in SEEDS:
        projector = train_contrastive_encoder_on_train_only(u_tr, v_tr, y_tr, seed=s)
        with torch.no_grad():
            z_u_tr = projector(torch.tensor(u_tr)).numpy()
            z_v_tr = projector(torch.tensor(v_tr)).numpy()
            z_u_vl = projector(torch.tensor(u_vl)).numpy()
            z_v_vl = projector(torch.tensor(v_vl)).numpy()
            
        X_proj_tr = build_features(z_u_tr, z_v_tr)
        X_proj_vl = build_features(z_u_vl, z_v_vl)
        
        # Raw classifier
        sc_raw = StandardScaler().fit(X_raw_tr)
        clf_raw = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=s)
        clf_raw.fit(sc_raw.transform(X_raw_tr), y_tr)
        pred_raw = clf_raw.predict(sc_raw.transform(X_raw_vl))
        acc_raw = float(accuracy_score(y_vl, pred_raw))
        bal_raw = float(balanced_accuracy_score(y_vl, pred_raw))
        _, _, f1_raw, _ = precision_recall_fscore_support(y_vl, pred_raw, average="macro", zero_division=0)
        
        # Proj classifier
        sc_proj = StandardScaler().fit(X_proj_tr)
        clf_proj = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=s)
        clf_proj.fit(sc_proj.transform(X_proj_tr), y_tr)
        pred_proj = clf_proj.predict(sc_proj.transform(X_proj_vl))
        acc_proj = float(accuracy_score(y_vl, pred_proj))
        bal_proj = float(balanced_accuracy_score(y_vl, pred_proj))
        _, _, f1_proj, _ = precision_recall_fscore_support(y_vl, pred_proj, average="macro", zero_division=0)
        
        per_seed_data.append({
            "seed": s,
            "raw_accuracy": round(acc_raw, 4),
            "proj_accuracy": round(acc_proj, 4),
            "accuracy_delta": round(acc_proj - acc_raw, 4),
            "raw_balanced_acc": round(bal_raw, 4),
            "proj_balanced_acc": round(bal_proj, 4),
            "balanced_acc_delta": round(bal_proj - bal_raw, 4),
            "raw_macro_f1": round(float(f1_raw), 4),
            "proj_macro_f1": round(float(f1_proj), 4),
            "macro_f1_delta": round(float(f1_proj) - float(f1_raw), 4)
        })
        all_raw_preds.append(pred_raw)
        all_proj_preds.append(pred_proj)
        
    acc_deltas = [d["accuracy_delta"] for d in per_seed_data]
    bal_deltas = [d["balanced_acc_delta"] for d in per_seed_data]
    f1_deltas = [d["macro_f1_delta"] for d in per_seed_data]
    
    n_seeds = len(SEEDS)
    mean_delta = float(np.mean(acc_deltas))
    sample_std = float(np.std(acc_deltas, ddof=1))
    pop_std = float(np.std(acc_deltas, ddof=0))
    sem = sample_std / np.sqrt(n_seeds)
    
    # Student-t interval (df = 4)
    t_crit = float(stats.t.ppf(0.975, df=n_seeds - 1))
    ci_t_lower = mean_delta - t_crit * sem
    ci_t_upper = mean_delta + t_crit * sem
    
    # Explanation of previously reported interval
    prev_lower = mean_delta - 1.96 * pop_std / np.sqrt(n_seeds)
    prev_upper = mean_delta + 1.96 * pop_std / np.sqrt(n_seeds)
    
    # 2. Validation-sample paired bootstrap on Seed 42 (10,000 resamples)
    np.random.seed(42)
    n_val = len(y_vl)
    correct_raw_seed42 = (all_raw_preds[0] == y_vl).astype(int)
    correct_proj_seed42 = (all_proj_preds[0] == y_vl).astype(int)
    
    boot_deltas = []
    for _ in range(10000):
        boot_idx = np.random.choice(n_val, size=n_val, replace=True)
        acc_r_b = np.mean(correct_raw_seed42[boot_idx])
        acc_p_b = np.mean(correct_proj_seed42[boot_idx])
        boot_deltas.append(acc_p_b - acc_r_b)
        
    ci_boot_lower = float(np.percentile(boot_deltas, 2.5))
    ci_boot_upper = float(np.percentile(boot_deltas, 97.5))
    
    # 3. McNemar's exact test on Seed 42 predictions
    # b: raw correct & proj wrong; c: raw wrong & proj correct
    b = int(np.sum((correct_raw_seed42 == 1) & (correct_proj_seed42 == 0)))
    c = int(np.sum((correct_raw_seed42 == 0) & (correct_proj_seed42 == 1)))
    a = int(np.sum((correct_raw_seed42 == 0) & (correct_proj_seed42 == 0)))
    d = int(np.sum((correct_raw_seed42 == 1) & (correct_proj_seed42 == 1)))
    
    binom_res = stats.binomtest(min(b, c), b + c, p=0.5, alternative="two-sided")
    mcnemar_p = float(binom_res.pvalue)
    
    report = {
        "individual_seed_runs": per_seed_data,
        "seed_variation_statistics": {
            "n_seeds": n_seeds,
            "degrees_of_freedom": n_seeds - 1,
            "mean_accuracy_delta": round(mean_delta, 4),
            "sample_standard_deviation_ddof1": round(sample_std, 4),
            "population_standard_deviation_ddof0": round(pop_std, 4),
            "standard_error_of_mean": round(sem, 4),
            "two_sided_student_t_critical_value": round(t_crit, 4),
            "certified_student_t_95_ci": [round(ci_t_lower, 4), round(ci_t_upper, 4)],
            "previous_interval_reconciliation": {
                "previously_reported_interval": [round(prev_lower, 4), round(prev_upper, 4)],
                "methodological_defect": (
                    "The previously reported interval [+4.04%, +8.80%] was computed using the asymptotic normal z=1.96 "
                    "with population standard deviation (ddof=0). For N=5 observations, the Student-t distribution with df=4 "
                    "(t_crit=2.776) and sample standard deviation (ddof=1) must be used. "
                    "The proper cross-seed Student-t 95% CI is [+2.65%, +10.18%]."
                )
            }
        },
        "validation_sample_uncertainty_seed42": {
            "validation_sample_size": n_val,
            "paired_bootstrap_10000_resamples_95_ci": [round(ci_boot_lower, 4), round(ci_boot_upper, 4)],
            "contingency_table": {
                "both_incorrect_n00": a,
                "raw_correct_proj_incorrect_n10": b,
                "raw_incorrect_proj_correct_n01": c,
                "both_correct_n11": d
            },
            "mcnemar_exact_test": {
                "discordant_pairs": b + c,
                "p_value": round(mcnemar_p, 4),
                "statistically_significant_at_alpha_0_05": bool(mcnemar_p < 0.05)
            }
        },
        "macro_f1_and_balanced_accuracy_summary": {
            "balanced_accuracy_delta_mean": round(float(np.mean(bal_deltas)), 4),
            "balanced_accuracy_delta_std": round(float(np.std(bal_deltas, ddof=1)), 4),
            "macro_f1_delta_mean": round(float(np.mean(f1_deltas)), 4),
            "macro_f1_delta_std": round(float(np.std(f1_deltas, ddof=1)), 4)
        }
    }
    
    with open(OUT_DIR / "contrastive_statistical_reconciliation.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nMean Accuracy Delta across seeds: {mean_delta*100:+.2f}%")
    print(f"Sample Std: {sample_std*100:.2f}%, SEM: {sem*100:.2f}%")
    print(f"Certified Student-t 95% CI: [{ci_t_lower*100:+.2f}%, {ci_t_upper*100:+.2f}%]")
    print(f"Validation Paired Bootstrap 95% CI (Seed 42): [{ci_boot_lower*100:+.2f}%, {ci_boot_upper*100:+.2f}%]")
    print(f"McNemar Exact Test (Seed 42): Discordant={b+c} (b={b}, c={c}), p-value={mcnemar_p:.4f} (Significant: {mcnemar_p < 0.05})")
    print(f"Report written to: {OUT_DIR / 'contrastive_statistical_reconciliation.json'}")

if __name__ == "__main__":
    main()
