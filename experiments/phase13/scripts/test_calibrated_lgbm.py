"""
experiments/phase13/scripts/test_calibrated_lgbm.py
Tests LightGBM + CalibratedClassifierCV on combined SBERT + Domain features.
"""
import sys
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, confusion_matrix, brier_score_loss
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits

def compute_ece(probs, labels, n_bins=10):
    # Multiclass ECE
    pred_labels = np.argmax(probs, axis=1)
    confidences = np.max(probs, axis=1)
    accuracies = (pred_labels == labels).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i+1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            avg_conf = np.mean(confidences[in_bin])
            avg_acc = np.mean(accuracies[in_bin])
            ece += prop_in_bin * np.abs(avg_conf - avg_acc)
    return ece

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
    
    cos_tr = np.sum(u_tr * v_tr, axis=1, keepdims=True)
    cos_vl = np.sum(u_vl * v_vl, axis=1, keepdims=True)
    
    y_tr = tr_clean["label"].values
    y_vl = vl_clean["label"].values
    
    label_map = {"No Fit": 0, "Potential Fit": 1, "Good Fit": 2}
    y_tr_num = np.array([label_map[y] for y in y_tr])
    y_vl_num = np.array([label_map[y] for y in y_vl])
    
    # Let's test feature combinations
    # Combo 1: 28 domain features
    # Combo 2: cos + 28 domain features
    # Combo 3: SBERT top 16 PCA + 28 domain features
    
    from sklearn.decomposition import PCA
    pca = PCA(n_components=16, random_state=42)
    diff_tr = np.abs(u_tr - v_tr)
    diff_vl = np.abs(u_vl - v_vl)
    prod_tr = u_tr * v_tr
    prod_vl = u_vl * v_vl
    dense_tr = np.hstack([diff_tr, prod_tr])
    dense_vl = np.hstack([diff_vl, prod_vl])
    pca_tr = pca.fit_transform(dense_tr)
    pca_vl = pca.transform(dense_vl)
    
    combos = {
        "Dom28": (tr_dom.values, vl_dom_clean.values),
        "Cos+Dom28 (29 feats)": (np.hstack([cos_tr, tr_dom.values]), np.hstack([cos_vl, vl_dom_clean.values])),
        "Cos+PCA16+Dom28 (45 feats)": (np.hstack([cos_tr, pca_tr, tr_dom.values]), np.hstack([cos_vl, pca_vl, vl_dom_clean.values]))
    }
    
    for cname, (X_tr, X_vl) in combos.items():
        print(f"\n=== Testing {cname} ===")
        for cw in ["balanced", None]:
            base_clf = lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.03,
                num_leaves=15,
                class_weight=cw,
                random_state=42,
                verbose=-1
            )
            # Calibration with GroupKFold or simple 5-fold CV
            cal_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=5)
            cal_clf.fit(X_tr, y_tr_num)
            
            probs = cal_clf.predict_proba(X_vl)
            preds = np.argmax(probs, axis=1)
            
            acc = accuracy_score(y_vl_num, preds)
            mf1 = f1_score(y_vl_num, preds, average="macro")
            gf_rec = recall_score(y_vl_num, preds, labels=[2], average=None)[0]
            cm = confusion_matrix(y_vl_num, preds)
            
            # One-hot labels for Brier
            y_onehot = np.zeros_like(probs)
            for i, val in enumerate(y_vl_num):
                y_onehot[i, val] = 1.0
            brier = np.mean(np.sum((probs - y_onehot)**2, axis=1))
            ece = compute_ece(probs, y_vl_num)
            
            print(f"CW={cw} -> Acc: {acc*100:.2f}%, MacroF1: {mf1:.4f}, GoodFitRec: {gf_rec*100:.1f}% ({cm[2,2]}/93), Brier: {brier:.4f}, ECE: {ece:.4f}")

if __name__ == "__main__":
    main()
