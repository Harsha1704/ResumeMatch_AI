"""
experiments/phase13/scripts/test_class_weights.py
Explores class weighting and probability thresholding to balance accuracy and Good Fit recall.
"""
import sys
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, confusion_matrix, precision_score

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
    
    print("\n--- Tuning class weights on LogReg C=0.002 ---")
    weights = [
        "balanced",
        {"No Fit": 1.0, "Potential Fit": 1.2, "Good Fit": 1.5},
        {"No Fit": 1.0, "Potential Fit": 1.5, "Good Fit": 2.0},
        {"No Fit": 1.0, "Potential Fit": 1.2, "Good Fit": 2.5},
        {"No Fit": 0.8, "Potential Fit": 1.2, "Good Fit": 2.0},
        {"No Fit": 0.7, "Potential Fit": 1.0, "Good Fit": 2.2},
    ]
    for w in weights:
        clf = LogisticRegression(C=0.002, max_iter=1000, class_weight=w, random_state=42)
        clf.fit(X_combined_tr, y_tr)
        pred = clf.predict(X_combined_vl)
        acc = accuracy_score(y_vl, pred)
        bal_acc = balanced_accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gf_r = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        gf_p = precision_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        cm = confusion_matrix(y_vl, pred, labels=["No Fit", "Potential Fit", "Good Fit"])
        print(f"Weight: {w} -> Acc: {acc*100:.2f}%, BalAcc: {bal_acc*100:.2f}%, MacroF1: {mf1:.4f}, GoodFit: R={gf_r*100:.1f}%, P={gf_p*100:.1f}% ({cm[2,2]}/93)")

if __name__ == "__main__":
    main()
