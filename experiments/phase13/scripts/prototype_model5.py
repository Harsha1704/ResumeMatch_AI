"""
experiments/phase13/scripts/prototype_model5.py
Exploratory script to test feature combinations, scaling, and models for Model 4 and Model 5.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score, classification_report, confusion_matrix, brier_score_loss
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits

REPO_ROOT = Path("D:/skillsync1")
CACHE_PATH = REPO_ROOT / "experiments" / "phase13" / "cache" / "sbert_embeddings.npz"

def main():
    print("Loading data...")
    tr_clean, vl_clean = load_guarded_dual_unseen_splits()
    
    # Domain features
    tr_dom = pd.read_parquet(REPO_ROOT / "experiments/dataset_improvement/splits/train_domain_raw.parquet")
    vl_dom = pd.read_parquet(REPO_ROOT / "experiments/dataset_improvement/splits/val_domain_raw.parquet")
    
    # Align vl_dom with vl_clean
    tr_norm_res = set(tr_clean["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" "))
    vl_norm_res = vl_df = pd.read_parquet(REPO_ROOT / "manifests/v1/dual_unseen_val_v1.parquet")["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" ")
    clean_mask = ~vl_norm_res.isin(tr_norm_res)
    vl_dom_clean = vl_dom[clean_mask].reset_index(drop=True)
    
    # SBERT embeddings
    sbert_data = np.load(CACHE_PATH)
    res_dict = {rid: emb for rid, emb in zip(sbert_data["res_ids"], sbert_data["res_embs"])}
    job_dict = {jid: emb for jid, emb in zip(sbert_data["job_ids"], sbert_data["job_embs"])}
    
    u_tr = np.array([res_dict[rid] for rid in tr_clean["resume_id"]], dtype=np.float32)
    v_tr = np.array([job_dict[jid] for jid in tr_clean["job_id"]], dtype=np.float32)
    u_vl = np.array([res_dict[rid] for rid in vl_clean["resume_id"]], dtype=np.float32)
    v_vl = np.array([job_dict[jid] for jid in vl_clean["job_id"]], dtype=np.float32)
    
    # Interactions
    cos_tr = np.sum(u_tr * v_tr, axis=1, keepdims=True)
    cos_vl = np.sum(u_vl * v_vl, axis=1, keepdims=True)
    diff_tr = np.abs(u_tr - v_tr)
    diff_vl = np.abs(u_vl - v_vl)
    prod_tr = u_tr * v_tr
    prod_vl = u_vl * v_vl
    
    y_tr = tr_clean["label"].values
    y_vl = vl_clean["label"].values
    
    label_map = {"No Fit": 0, "Potential Fit": 1, "Good Fit": 2}
    inv_map = {0: "No Fit", 1: "Potential Fit", 2: "Good Fit"}
    y_tr_num = np.array([label_map[y] for y in y_tr])
    y_vl_num = np.array([label_map[y] for y in y_vl])
    
    print(f"Data ready. Train N={len(y_tr)}, Val N={len(y_vl)}")
    
    # Experiments
    # 1. Domain only (Model 4)
    print("\n--- Model 4: LightGBM on 28 Domain Features ---")
    for cw in [None, "balanced", {0: 1.0, 1: 1.5, 2: 2.0}]:
        clf = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=15,
            class_weight=cw,
            random_state=42,
            verbose=-1
        )
        clf.fit(tr_dom, y_tr_num)
        y_pred = clf.predict(vl_dom_clean)
        acc = accuracy_score(y_vl_num, y_pred)
        macro_f1 = f1_score(y_vl_num, y_pred, average="macro")
        gf_rec = recall_score(y_vl_num, y_pred, labels=[2], average=None)[0]
        print(f"CW: {cw} -> Acc: {acc:.4f}, Macro F1: {macro_f1:.4f}, Good Fit Rec: {gf_rec:.4f} ({confusion_matrix(y_vl_num, y_pred)[2,2]}/93)")
        
    # 2. Semantic + Domain Features (Model 5)
    print("\n--- Model 5 Prototypes: SBERT + Domain Features ---")
    # Test feature combinations:
    # Option A: cos + 28 domain features
    X_tr_A = np.hstack([cos_tr, tr_dom.values])
    X_vl_A = np.hstack([cos_vl, vl_dom_clean.values])
    
    # Option B: cos + diff + prod + 28 domain features (769 features)
    X_tr_B = np.hstack([cos_tr, diff_tr, prod_tr, tr_dom.values])
    X_vl_B = np.hstack([cos_vl, diff_vl, prod_vl, vl_dom_clean.values])
    
    # Option C: cos + top PCA components of diff/prod + 28 domain features
    from sklearn.decomposition import PCA
    pca = PCA(n_components=32, random_state=42)
    dense_tr = np.hstack([diff_tr, prod_tr])
    dense_vl = np.hstack([diff_vl, prod_vl])
    dense_pca_tr = pca.fit_transform(dense_tr)
    dense_pca_vl = pca.transform(dense_vl)
    X_tr_C = np.hstack([cos_tr, dense_pca_tr, tr_dom.values])
    X_vl_C = np.hstack([cos_vl, dense_pca_vl, vl_dom_clean.values])
    
    for name, X_tr_opt, X_vl_opt in [("Cos+Dom (29 feats)", X_tr_A, X_vl_A), 
                                     ("Cos+Dense+Dom (797 feats)", X_tr_B, X_vl_B),
                                     ("Cos+PCA32+Dom (61 feats)", X_tr_C, X_vl_C)]:
        print(f"\nFeature Set: {name}")
        for lr in [0.03, 0.05]:
            for leaves in [15, 31]:
                clf = lgb.LGBMClassifier(
                    n_estimators=120,
                    learning_rate=lr,
                    num_leaves=leaves,
                    class_weight="balanced",
                    random_state=42,
                    verbose=-1
                )
                clf.fit(X_tr_opt, y_tr_num)
                y_pred = clf.predict(X_vl_opt)
                acc = accuracy_score(y_vl_num, y_pred)
                macro_f1 = f1_score(y_vl_num, y_pred, average="macro")
                gf_rec = recall_score(y_vl_num, y_pred, labels=[2], average=None)[0]
                cm = confusion_matrix(y_vl_num, y_pred)
                print(f"lr={lr}, leaves={leaves} -> Acc: {acc*100:.2f}%, Macro F1: {macro_f1:.4f}, Good Fit Rec: {gf_rec*100:.1f}% ({cm[2,2]}/93)")

if __name__ == "__main__":
    main()
