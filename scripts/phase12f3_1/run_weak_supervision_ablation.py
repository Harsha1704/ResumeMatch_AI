"""
scripts/phase12f3_1/run_weak_supervision_ablation.py
Executes controlled weak supervision ablation:
A. Full five-LF consensus (N=2,092).
B. Four-LF consensus excluding Jaccard (N=391).
C. Full five-LF consensus downsampled to N=391 (same sample count as B).
D. Four-LF consensus replicated across 5 independent seeds ([42, 43, 44, 45, 46]).
Reports sample composition, class distribution, coverage, conflicts, per-class performance,
accuracy, balanced accuracy, and Macro F1.
"""

import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support

from src.phase12f.models import HybridStackingClassifier
from src.phase12f.weak_supervision import WeakLabelingSystem
from src.phase12f2.split_guard import load_guarded_dual_unseen_splits
from src.evaluation.split_validator import hash_text
from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine

REPO_ROOT = Path("D:/skillsync1")
OUT_DIR = REPO_ROOT / "experiments" / "phase12f3_1" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CACHE_PATH = REPO_ROOT / "results" / "phase12b_embeddings" / "minilm_l6_v2_cache.npz"
CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}
SEEDS = [42, 43, 44, 45, 46]

def extract_dense_features(df: pd.DataFrame, skill_engine: SkillEngine) -> np.ndarray:
    rows = []
    for r_raw, j_raw in zip(df["resume_text"], df["job_description_text"]):
        r_clean = clean_text(r_raw)
        j_clean = clean_text(j_raw)
        r_struct = parse_structural_features(r_raw)
        j_struct = parse_structural_features(j_raw)
        
        r_skills = set(skill_engine.extract_skills(r_clean))
        j_skills = set(skill_engine.extract_skills(j_clean))
        n_j_skills = max(len(j_skills), 1)
        skill_overlap = len(r_skills.intersection(j_skills))
        skill_overlap_ratio = skill_overlap / n_j_skills
        jaccard = skill_overlap / max(len(r_skills.union(j_skills)), 1)
        
        r_words = set(r_clean.split())
        j_words = set(j_clean.split())
        word_overlap = len(r_words.intersection(j_words)) / max(len(j_words), 1)
        
        r_chars, j_chars = float(len(r_raw)), float(len(j_raw))
        r_wcnt, j_wcnt = float(len(r_words)), float(len(j_words))
        char_ratio = r_chars / max(j_chars, 1.0)
        word_ratio = r_wcnt / max(j_wcnt, 1.0)
        
        r_exp = float(r_struct.get("explicit_years_exp", r_struct.get("experience_years", 0)))
        j_exp = float(j_struct.get("explicit_years_exp", j_struct.get("experience_years", 0)))
        exp_diff = r_exp - j_exp
        exp_ratio = r_exp / max(j_exp, 1.0)
        
        r_has_proj = 1.0 if r_struct.get("has_projects", False) else 0.0
        r_has_cert = 1.0 if r_struct.get("has_certifications", False) else 0.0
        r_has_edu = 1.0 if r_struct.get("has_education", False) else 0.0
        senior_mismatch = 1.0 if (j_exp >= 5.0 and r_exp < 3.0) else 0.0
        
        dense_vec = [
            skill_overlap_ratio, jaccard, word_overlap,
            float(skill_overlap), float(len(r_skills)), float(len(j_skills)),
            r_chars, j_chars, char_ratio, r_wcnt, j_wcnt, word_ratio,
            r_exp, j_exp, exp_diff, exp_ratio,
            r_has_proj, r_has_cert, r_has_edu,
            float(r_struct.get("project_count", 0)),
            float(r_struct.get("cert_count", 0)),
            1.0 if r_exp >= j_exp else 0.0,
            1.0 if skill_overlap >= 3 else 0.0,
            float(len(r_skills.difference(j_skills))),
            senior_mismatch
        ]
        rows.append(dense_vec)
    return np.array(rows, dtype=np.float32)

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    p_m, r_m, f1_m, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    
    per_class_p, per_class_r, per_class_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    per_class = {}
    for idx, c in enumerate(CLASSES):
        per_class[c] = {
            "precision": round(float(per_class_p[idx]), 4),
            "recall": round(float(per_class_r[idx]), 4),
            "f1": round(float(per_class_f1[idx]), 4)
        }
    return {
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "macro_precision": round(float(p_m), 4),
        "macro_recall": round(float(r_m), 4),
        "macro_f1": round(float(f1_m), 4),
        "per_class": per_class
    }

def main():
    print("=" * 80)
    print("PHASE 12F.3.1: CONTROLLED WEAK SUPERVISION ABLATION EXPERIMENT")
    print("=" * 80)
    
    dual_tr, dual_vl = load_guarded_dual_unseen_splits()
    y_dual_tr = dual_tr["label"].values
    y_dual_vl = dual_vl["label"].values
    
    cached_data = np.load(CACHE_PATH, allow_pickle=True)
    res_emb_dict = {h: cached_data[f"res_{h}"] for h in cached_data["res_hashes"]}
    job_emb_dict = {h: cached_data[f"job_{h}"] for h in cached_data["job_hashes"]}
    
    def build_sbert(df):
        feats = []
        for r, j in zip(df["resume_text"], df["job_description_text"]):
            rh = hash_text(r)
            jh = hash_text(j)
            u = res_emb_dict[rh]
            v = job_emb_dict[jh]
            cos_sim = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
            feats.append(np.concatenate([u, v, u * v, np.abs(u - v), [cos_sim]]))
        return np.array(feats, dtype=np.float32)

    skill_engine = SkillEngine()
    print("Extracting features for Dual-Unseen partitions...")
    X_tr = np.hstack([build_sbert(dual_tr), extract_dense_features(dual_tr, skill_engine)])
    X_vl = np.hstack([build_sbert(dual_vl), extract_dense_features(dual_vl, skill_engine)])
    
    weak_sys = WeakLabelingSystem()
    print("Applying labeling functions to training partition...")
    L_matrix = weak_sys.apply_lfs(dual_tr["resume_text"].tolist(), dual_tr["job_description_text"].tolist())
    
    # 1. Full 5-LF consensus (conf >= 0.70)
    full_labels, full_conf = weak_sys.aggregate_weak_labels(L_matrix)
    mask_a = (full_labels != -1) & (full_conf >= 0.70)
    idx_a = np.where(mask_a)[0]
    labels_a = [CLASSES[full_labels[i]] for i in idx_a]
    dist_a = {c: int(np.sum(np.array(labels_a) == c)) for c in CLASSES}
    print(f"Condition A (Full 5-LF): {len(idx_a)} admitted pairs. Distribution: {dist_a}")
    
    # 2. Pruned 4-LF consensus (omitting column 4 - Jaccard)
    pruned_votes = L_matrix[:, :4]
    pruned_pairs = []
    for r in range(len(pruned_votes)):
        v = pruned_votes[r]
        valid_v = v[v != -1]
        if len(valid_v) >= 2:
            counts = np.bincount(valid_v, minlength=3)
            maj = np.argmax(counts)
            conf = counts[maj] / len(valid_v)
            if conf >= 0.70:
                pruned_pairs.append((r, CLASSES[maj]))
    idx_b = np.array([x[0] for x in pruned_pairs])
    labels_b = [x[1] for x in pruned_pairs]
    dist_b = {c: int(np.sum(np.array(labels_b) == c)) for c in CLASSES}
    print(f"Condition B (Pruned 4-LF): {len(idx_b)} admitted pairs. Distribution: {dist_b}")
    
    # 3. Downsampled 5-LF consensus (Condition C)
    np.random.seed(42)
    downsample_indices = np.random.choice(idx_a, size=len(idx_b), replace=False)
    labels_c = [CLASSES[full_labels[i]] for i in downsample_indices]
    dist_c = {c: int(np.sum(np.array(labels_c) == c)) for c in CLASSES}
    print(f"Condition C (Downsampled 5-LF): {len(downsample_indices)} admitted pairs. Distribution: {dist_c}")
    
    # Evaluate Condition A
    print("\nTraining Condition A (Full 5-LF, Seed 42)...")
    X_aug_a = np.vstack([X_tr, X_tr[idx_a]])
    y_aug_a = np.concatenate([y_dual_tr, labels_a])
    hyb_a = HybridStackingClassifier(random_state=42)
    hyb_a.fit(X_aug_a, y_aug_a)
    m_a = evaluate_predictions(y_dual_vl, hyb_a.predict(X_vl))
    
    # Evaluate Condition B (Seed 42)
    print("Training Condition B (Pruned 4-LF, Seed 42)...")
    X_aug_b = np.vstack([X_tr, X_tr[idx_b]])
    y_aug_b = np.concatenate([y_dual_tr, labels_b])
    hyb_b = HybridStackingClassifier(random_state=42)
    hyb_b.fit(X_aug_b, y_aug_b)
    m_b = evaluate_predictions(y_dual_vl, hyb_b.predict(X_vl))
    
    # Evaluate Condition C (Seed 42)
    print("Training Condition C (Downsampled 5-LF, Seed 42)...")
    X_aug_c = np.vstack([X_tr, X_tr[downsample_indices]])
    y_aug_c = np.concatenate([y_dual_tr, labels_c])
    hyb_c = HybridStackingClassifier(random_state=42)
    hyb_c.fit(X_aug_c, y_aug_c)
    m_c = evaluate_predictions(y_dual_vl, hyb_c.predict(X_vl))
    
    # Condition D: Four-LF consensus across 5 independent seeds
    print("\nRunning Condition D (Four-LF across 5 independent seeds)...")
    cond_d_runs = []
    for s in SEEDS:
        hyb_d = HybridStackingClassifier(random_state=s)
        hyb_d.fit(X_aug_b, y_aug_b)
        m_d = evaluate_predictions(y_dual_vl, hyb_d.predict(X_vl))
        cond_d_runs.append(m_d)
        print(f"  Seed {s}: Acc={m_d['accuracy']}, BalAcc={m_d['balanced_accuracy']}, MacroF1={m_d['macro_f1']}")
        
    accs_d = [r["accuracy"] for r in cond_d_runs]
    bal_accs_d = [r["balanced_accuracy"] for r in cond_d_runs]
    f1s_d = [r["macro_f1"] for r in cond_d_runs]
    
    summary_d = {
        "accuracy_mean": round(float(np.mean(accs_d)), 4),
        "accuracy_std": round(float(np.std(accs_d)), 4),
        "balanced_accuracy_mean": round(float(np.mean(bal_accs_d)), 4),
        "balanced_accuracy_std": round(float(np.std(bal_accs_d)), 4),
        "macro_f1_mean": round(float(np.mean(f1s_d)), 4),
        "macro_f1_std": round(float(np.std(f1s_d)), 4),
        "individual_runs": cond_d_runs
    }
    
    ablation_report = {
        "experiment_name": "Controlled Weak Supervision Ablation",
        "sample_compositions": {
            "condition_a_full_5lf": {"count": len(idx_a), "class_distribution": dist_a},
            "condition_b_pruned_4lf": {"count": len(idx_b), "class_distribution": dist_b},
            "condition_c_downsampled_5lf": {"count": len(downsample_indices), "class_distribution": dist_c}
        },
        "results": {
            "condition_a_full_5lf": m_a,
            "condition_b_pruned_4lf_seed42": m_b,
            "condition_c_downsampled_5lf_seed42": m_c,
            "condition_d_pruned_4lf_5seeds": summary_d
        },
        "comparative_analysis": {
            "volume_effect_delta_c_minus_a": round(m_c["accuracy"] - m_a["accuracy"], 4),
            "lf_rule_selection_delta_b_minus_c": round(m_b["accuracy"] - m_c["accuracy"], 4),
            "scientific_takeaway": (
                "Comparing B (391 pruned pairs) against C (391 downsampled 5-LF pairs) isolates the effect of LF rule selection "
                "from sample volume. Comparing C against A isolates the effect of weak augmentation sample size."
            )
        }
    }
    
    with open(OUT_DIR / "controlled_weak_supervision_ablation.json", "w") as f:
        json.dump(ablation_report, f, indent=2)
        
    print("\nControlled ablation results saved to experiments/phase12f3_1/results/controlled_weak_supervision_ablation.json")
    print(f"Condition A (Full 5-LF):       Acc={m_a['accuracy']:.4f}, MacroF1={m_a['macro_f1']:.4f}")
    print(f"Condition B (Pruned 4-LF):     Acc={m_b['accuracy']:.4f}, MacroF1={m_b['macro_f1']:.4f}")
    print(f"Condition C (Downsampled 5LF): Acc={m_c['accuracy']:.4f}, MacroF1={m_c['macro_f1']:.4f}")
    print(f"Condition D (4-LF 5 seeds):    Acc={summary_d['accuracy_mean']:.4f} +/- {summary_d['accuracy_std']:.4f}")

if __name__ == "__main__":
    main()
