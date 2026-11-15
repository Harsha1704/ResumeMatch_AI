"""
experiments/phase13/scripts/evaluate_model5_seeds.py
Tests Model 5 across all 5 seeds (42, 43, 44, 45, 46) for stability and performance.
"""
import sys
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, precision_score, confusion_matrix
import lightgbm as lgb

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits

def build_sbert_features(u, v):
    cos = np.sum(u * v, axis=1, keepdims=True) / (np.linalg.norm(u, axis=1, keepdims=True) * np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return np.hstack([u, v, u * v, np.abs(u - v), cos])

def main():
    tr_clean, vl_clean = load_guarded_dual_unseen_splits()
    tr_dom = pd.read_parquet(REPO_ROOT / "experiments/dataset_improvement/splits/train_domain_raw.parquet")
    vl_dom = pd.read_parquet(REPO_ROOT / "experiments/dataset_improvement/splits/val_domain_raw.parquet")
    
    tr_norm_res = set(tr_clean["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" "))
    vl_norm_res = pd.read_parquet(REPO_ROOT / "manifests/v1/dual_unseen_val_v1.parquet")["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" ")
    clean_mask = ~vl_norm_res.isin(tr_norm_res)
    vl_dom_clean = vl_dom[clean_mask].reset_index(drop=True)
    
    sbert_data = np.load(REPO_ROOT / "experiments/phase13/cache/sbert_embeddings.npz")
    res_dict = {rid: emb for rid, emb in zip(sbert_data["res_ids"], sbert_data["res_embs"])}
    job_dict = {jid: emb for jid, emb in zip(sbert_data["job_ids"], sbert_data["job_embs"])}
    
    u_tr = np.array([res_dict[rid] for rid in tr_clean["resume_id"]], dtype=np.float32)
    v_tr = np.array([job_dict[jid] for jid in tr_clean["job_id"]], dtype=np.float32)
    u_vl = np.array([res_dict[rid] for rid in vl_clean["resume_id"]], dtype=np.float32)
    v_vl = np.array([job_dict[jid] for jid in vl_clean["job_id"]], dtype=np.float32)
    
    y_tr = tr_clean["label"].values
    y_vl = vl_clean["label"].values
    
    X_sbert_tr = build_sbert_features(u_tr, v_tr)
    X_sbert_vl = build_sbert_features(u_vl, v_vl)
    
    sc_sbert = StandardScaler().fit(X_sbert_tr)
    X_sbert_tr_sc = sc_sbert.transform(X_sbert_tr)
    X_sbert_vl_sc = sc_sbert.transform(X_sbert_vl)
    
    sc_dom = StandardScaler().fit(tr_dom)
    X_dom_tr_sc = sc_dom.transform(tr_dom)
    X_dom_vl_sc = sc_dom.transform(vl_dom_clean)
    
    X_combined_tr = np.hstack([X_sbert_tr_sc, X_dom_tr_sc])
    X_combined_vl = np.hstack([X_sbert_vl_sc, X_dom_vl_sc])
    
    SEEDS = [42, 43, 44, 45, 46]
    
    # Test Architecture A: Regularized Logistic Regression Fusion (C=0.001)
    print("=== Architecture A: Regularized Logistic Regression Fusion (C=0.001) ===")
    arch_a_accs = []
    arch_a_f1s = []
    arch_a_gfrs = []
    for s in SEEDS:
        clf = LogisticRegression(C=0.001, max_iter=1000, class_weight="balanced", random_state=s)
        clf.fit(X_combined_tr, y_tr)
        pred = clf.predict(X_combined_vl)
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gfr = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        arch_a_accs.append(acc)
        arch_a_f1s.append(mf1)
        arch_a_gfrs.append(gfr)
        print(f"Seed {s}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gfr*100:.1f}%")
    print(f"Arch A Mean Acc: {np.mean(arch_a_accs)*100:.2f}% (std: {np.std(arch_a_accs)*100:.2f}%), Mean MacroF1: {np.mean(arch_a_f1s):.4f}, Mean GoodFitRec: {np.mean(arch_a_gfrs)*100:.1f}%")
    
    # Test Architecture B: LightGBM on SBERT Cosine + 28 Domain Features
    print("\n=== Architecture B: LightGBM on SBERT Cosine + 28 Domain Features ===")
    cos_tr = np.sum(u_tr * v_tr, axis=1, keepdims=True)
    cos_vl = np.sum(u_vl * v_vl, axis=1, keepdims=True)
    X_b_tr = np.hstack([cos_tr, tr_dom.values])
    X_b_vl = np.hstack([cos_vl, vl_dom_clean.values])
    
    arch_b_accs = []
    arch_b_f1s = []
    arch_b_gfrs = []
    for s in SEEDS:
        clf = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, class_weight="balanced", random_state=s, verbose=-1)
        clf.fit(X_b_tr, y_tr)
        pred = clf.predict(X_b_vl)
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gfr = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        arch_b_accs.append(acc)
        arch_b_f1s.append(mf1)
        arch_b_gfrs.append(gfr)
        print(f"Seed {s}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gfr*100:.1f}%")
    print(f"Arch B Mean Acc: {np.mean(arch_b_accs)*100:.2f}% (std: {np.std(arch_b_accs)*100:.2f}%), Mean MacroF1: {np.mean(arch_b_f1s):.4f}, Mean GoodFitRec: {np.mean(arch_b_gfrs)*100:.1f}%")

    # Test Architecture C: Two-Head Ensemble (SBERT Dense Head + Domain GBDT Head)
    print("\n=== Architecture C: Two-Head Soft Voting Ensemble ===")
    arch_c_accs = []
    arch_c_f1s = []
    arch_c_gfrs = []
    for s in SEEDS:
        # Head 1: SBERT LogReg
        h1 = LogisticRegression(C=0.01, max_iter=1000, class_weight="balanced", random_state=s)
        h1.fit(X_sbert_tr_sc, y_tr)
        p1 = h1.predict_proba(X_sbert_vl_sc)
        
        # Head 2: Domain LightGBM
        h2 = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, class_weight="balanced", random_state=s, verbose=-1)
        h2.fit(tr_dom.values, y_tr)
        p2 = h2.predict_proba(vl_dom_clean.values)
        
        # Soft blend (0.5 * h1 + 0.5 * h2)
        p_blend = 0.5 * p1 + 0.5 * p2
        pred = h1.classes_[np.argmax(p_blend, axis=1)]
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gfr = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        arch_c_accs.append(acc)
        arch_c_f1s.append(mf1)
        arch_c_gfrs.append(gfr)
        print(f"Seed {s}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gfr*100:.1f}%")
    print(f"Arch C Mean Acc: {np.mean(arch_c_accs)*100:.2f}% (std: {np.std(arch_c_accs)*100:.2f}%), Mean MacroF1: {np.mean(arch_c_f1s):.4f}, Mean GoodFitRec: {np.mean(arch_c_gfrs)*100:.1f}%")

if __name__ == "__main__":
    main()
