"""
experiments/phase13/scripts/test_contrastive_domain_fusion.py
Tests combining Contrastive Projector (128-d) representations with 28 Domain features.
"""
import sys
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, confusion_matrix
import lightgbm as lgb

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits
from scripts.phase12f3_1.reproduce_contrastive_downstream import (
    ContrastiveProjector,
    train_contrastive_encoder_on_train_only
)

def build_features(u, v):
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
    
    # Train contrastive projector on train split only (Seed 42)
    projector = train_contrastive_encoder_on_train_only(u_tr, v_tr, y_tr, seed=42)
    with torch.no_grad():
        z_u_tr = projector(torch.tensor(u_tr)).numpy()
        z_v_tr = projector(torch.tensor(v_tr)).numpy()
        z_u_vl = projector(torch.tensor(u_vl)).numpy()
        z_v_vl = projector(torch.tensor(v_vl)).numpy()
        
    X_proj_tr = build_features(z_u_tr, z_v_tr) # 128*4 + 1 = 513 features
    X_proj_vl = build_features(z_u_vl, z_v_vl)
    
    sc_proj = StandardScaler().fit(X_proj_tr)
    X_proj_tr_sc = sc_proj.transform(X_proj_tr)
    X_proj_vl_sc = sc_proj.transform(X_proj_vl)
    
    sc_dom = StandardScaler().fit(tr_dom)
    X_dom_tr_sc = sc_dom.transform(tr_dom)
    X_dom_vl_sc = sc_dom.transform(vl_dom_clean)
    
    # Fusion 1: Full concatenation (513 proj + 28 dom = 541 features)
    X_fuse_tr = np.hstack([X_proj_tr_sc, X_dom_tr_sc])
    X_fuse_vl = np.hstack([X_proj_vl_sc, X_dom_vl_sc])
    
    print("\n--- Contrastive + Domain Fusion with Logistic Regression ---")
    for C in [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]:
        clf = LogisticRegression(C=C, max_iter=1000, class_weight="balanced", random_state=42)
        clf.fit(X_fuse_tr, y_tr)
        pred = clf.predict(X_fuse_vl)
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gf_r = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        cm = confusion_matrix(y_vl, pred, labels=["No Fit", "Potential Fit", "Good Fit"])
        print(f"C={C:5f}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gf_r*100:.1f}% ({cm[2,2]}/93)")
        
    print("\n--- Contrastive + Domain Fusion with LightGBM ---")
    for lr in [0.02, 0.05]:
        for leaves in [15, 31]:
            clf = lgb.LGBMClassifier(n_estimators=100, learning_rate=lr, num_leaves=leaves, class_weight="balanced", random_state=42, verbose=-1)
            clf.fit(X_fuse_tr, y_tr)
            pred = clf.predict(X_fuse_vl)
            acc = accuracy_score(y_vl, pred)
            mf1 = f1_score(y_vl, pred, average="macro")
            gf_r = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
            cm = confusion_matrix(y_vl, pred, labels=["No Fit", "Potential Fit", "Good Fit"])
            print(f"LGBM lr={lr}, leaves={leaves}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gf_r*100:.1f}% ({cm[2,2]}/93)")

if __name__ == "__main__":
    main()
