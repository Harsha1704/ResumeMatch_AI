"""
experiments/phase13/scripts/evaluate_contrastive_domain_seeds.py
Tests Contrastive Projector + Domain Fusion across all 5 seeds.
"""
import sys
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, precision_score, confusion_matrix

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
    
    sc_dom = StandardScaler().fit(tr_dom)
    X_dom_tr_sc = sc_dom.transform(tr_dom)
    X_dom_vl_sc = sc_dom.transform(vl_dom_clean)
    
    SEEDS = [42, 43, 44, 45, 46]
    
    print("=== Testing Contrastive + Domain Fusion across 5 Seeds ===")
    results = []
    for s in SEEDS:
        projector = train_contrastive_encoder_on_train_only(u_tr, v_tr, y_tr, seed=s)
        with torch.no_grad():
            z_u_tr = projector(torch.tensor(u_tr)).numpy()
            z_v_tr = projector(torch.tensor(v_tr)).numpy()
            z_u_vl = projector(torch.tensor(u_vl)).numpy()
            z_v_vl = projector(torch.tensor(v_vl)).numpy()
            
        X_proj_tr = build_features(z_u_tr, z_v_tr)
        X_proj_vl = build_features(z_u_vl, z_v_vl)
        
        sc_proj = StandardScaler().fit(X_proj_tr)
        X_proj_tr_sc = sc_proj.transform(X_proj_tr)
        X_proj_vl_sc = sc_proj.transform(X_proj_vl)
        
        X_fuse_tr = np.hstack([X_proj_tr_sc, X_dom_tr_sc])
        X_fuse_vl = np.hstack([X_proj_vl_sc, X_dom_vl_sc])
        
        # Test C=0.001 balanced
        clf = LogisticRegression(C=0.001, max_iter=1000, class_weight="balanced", random_state=s)
        clf.fit(X_fuse_tr, y_tr)
        pred = clf.predict(X_fuse_vl)
        
        acc = accuracy_score(y_vl, pred)
        mf1 = f1_score(y_vl, pred, average="macro")
        gfr = recall_score(y_vl, pred, labels=["Good Fit"], average=None)[0]
        cm = confusion_matrix(y_vl, pred, labels=["No Fit", "Potential Fit", "Good Fit"])
        results.append({"seed": s, "acc": acc, "mf1": mf1, "gfr": gfr, "cm": cm.tolist()})
        print(f"Seed {s}: Acc={acc*100:.2f}%, MacroF1={mf1:.4f}, GoodFitRec={gfr*100:.1f}% ({cm[2,2]}/93)")
        
    accs = [r["acc"] for r in results]
    mf1s = [r["mf1"] for r in results]
    gfrs = [r["gfr"] for r in results]
    print(f"Mean Acc: {np.mean(accs)*100:.2f}% (std: {np.std(accs)*100:.2f}%), Mean MacroF1: {np.mean(mf1s):.4f}, Mean GoodFitRec: {np.mean(gfrs)*100:.1f}%")

if __name__ == "__main__":
    main()
