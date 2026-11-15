"""
experiments/phase13/scripts/test_fusion_variants.py
Systematically tests classifiers and feature combinations on Dual-Unseen train/val.
"""
import sys
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, confusion_matrix
import lightgbm as lgb
from sklearn.ensemble import HistGradientBoostingClassifier

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
    
    print(f"Combined features shape: {X_combined_tr.shape}")
    
    print("\n--- 1. Logistic Regression on Combined Features ---")
    for C in [0.001, 0.01, 0.05, 0.1, 0.5, 1.0]:
        clf = LogisticRegression(C=C, max_iter=1000, class_weight="balanced", random_state=42)
        clf.fit(X_combined_tr, y_tr)
        pred = clf.predict(X_combined_vl)
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gf_r = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        cm = confusion_matrix(y_vl, pred, labels=["No Fit", "Potential Fit", "Good Fit"])
        print(f"LogReg C={C:5f}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gf_r*100:.1f}% ({cm[2,2]}/93)")
        
    print("\n--- 2. Logistic Regression on Domain Only ---")
    for C in [0.01, 0.1, 1.0, 10.0]:
        clf = LogisticRegression(C=C, max_iter=1000, class_weight="balanced", random_state=42)
        clf.fit(X_dom_tr_sc, y_tr)
        pred = clf.predict(X_dom_vl_sc)
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gf_r = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        print(f"LogReg Dom C={C}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gf_r*100:.1f}%")

    print("\n--- 3. Ensemble / Probability Stacking of SBERT LogReg + Domain GBDT ---")
    clf_sbert = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    clf_sbert.fit(X_sbert_tr_sc, y_tr)
    prob_sbert_vl = clf_sbert.predict_proba(X_sbert_vl_sc)
    
    clf_dom = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, class_weight="balanced", random_state=42, verbose=-1)
    clf_dom.fit(tr_dom, y_tr)
    prob_dom_vl = clf_dom.predict_proba(vl_dom_clean)
    
    classes = clf_sbert.classes_
    print(f"Classes order: {classes}")
    
    for w in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
        prob_blend = w * prob_sbert_vl + (1 - w) * prob_dom_vl
        pred_blend = classes[np.argmax(prob_blend, axis=1)]
        acc = accuracy_score(y_vl, pred_blend)
        mf1 = f1_score(y_vl, pred_blend, average="macro")
        gf_r = recall_score(y_vl, pred_blend, labels=["Good Fit"], average=None)[0]
        cm = confusion_matrix(y_vl, pred_blend, labels=["No Fit", "Potential Fit", "Good Fit"])
        print(f"Weight SBERT={w:.1f}, Dom={1-w:.1f} -> Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gf_r*100:.1f}% ({cm[2,2]}/93)")

if __name__ == "__main__":
    main()
