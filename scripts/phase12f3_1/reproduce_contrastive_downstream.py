"""
scripts/phase12f3_1/reproduce_contrastive_downstream.py
Replication of contrastive learning representation evaluation across 5 independent seeds ([42, 43, 44, 45, 46]).
Confirms:
- Projection is fitted using training data only.
- Validation labels are never used in representation learning.
- Hyperparameters are not selected using final test labels.
- Downstream classifier and tuning budget are strictly comparable (LogisticRegression C=1.0 balanced).
- Reports mean, standard deviation, and paired confidence intervals.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits
from src.evaluation.split_validator import hash_text

REPO_ROOT = Path("D:/skillsync1")
OUT_DIR = REPO_ROOT / "experiments" / "phase12f3_1" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CACHE_PATH = REPO_ROOT / "results" / "phase12b_embeddings" / "minilm_l6_v2_cache.npz"
CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}
SEEDS = [42, 43, 44, 45, 46]

class ContrastiveProjector(nn.Module):
    def __init__(self, input_dim: int = 384, proj_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Linear(256, proj_dim)
        )
    def forward(self, x):
        z = self.net(x)
        return nn.functional.normalize(z, dim=-1)

def train_contrastive_encoder_on_train_only(u_tr: np.ndarray, v_tr: np.ndarray, y_tr: np.ndarray, seed: int = 42) -> ContrastiveProjector:
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    # Strictly training split only
    pos_mask = (y_tr == "Good Fit") | (y_tr == "Potential Fit")
    u_pos = torch.tensor(u_tr[pos_mask], dtype=torch.float32)
    v_pos = torch.tensor(v_tr[pos_mask], dtype=torch.float32)
    
    projector = ContrastiveProjector(input_dim=384, proj_dim=128)
    optimizer = torch.optim.AdamW(projector.parameters(), lr=1e-3, weight_decay=1e-4)
    
    dataset = torch.utils.data.TensorDataset(u_pos, v_pos)
    loader = torch.utils.data.DataLoader(dataset, batch_size=128, shuffle=True, drop_last=True)
    
    projector.train()
    criterion = nn.CrossEntropyLoss()
    for epoch in range(10):
        for b_u, b_v in loader:
            z_u = projector(b_u)
            z_v = projector(b_v)
            sim = torch.matmul(z_u, z_v.T) / 0.07
            labels = torch.arange(len(b_u))
            loss = criterion(sim, labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
    projector.eval()
    return projector

def main():
    print("=" * 80)
    print("PHASE 12F.3.1: CONTRASTIVE REPRESENTATION 5-SEED REPLICATION BENCHMARK")
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
    
    # 1. Raw SBERT Features (384-d resume + 384-d job + interaction)
    def build_features(u, v):
        cos = np.sum(u * v, axis=1, keepdims=True) / (np.linalg.norm(u, axis=1, keepdims=True) * np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
        return np.hstack([u, v, u * v, np.abs(u - v), cos])
        
    X_raw_tr = build_features(u_tr, v_tr)
    X_raw_vl = build_features(u_vl, v_vl)
    
    raw_results = []
    proj_results = []
    paired_deltas = []
    
    for s in SEEDS:
        print(f"\n--- Running Seed {s} ---")
        # Train contrastive projector on training partition ONLY
        projector = train_contrastive_encoder_on_train_only(u_tr, v_tr, y_tr, seed=s)
        
        with torch.no_grad():
            z_u_tr = projector(torch.tensor(u_tr)).numpy()
            z_v_tr = projector(torch.tensor(v_tr)).numpy()
            z_u_vl = projector(torch.tensor(u_vl)).numpy()
            z_v_vl = projector(torch.tensor(v_vl)).numpy()
            
        X_proj_tr = build_features(z_u_tr, z_v_tr)
        X_proj_vl = build_features(z_u_vl, z_v_vl)
        
        # A. Baseline Raw SBERT Classifier
        sc_raw = StandardScaler().fit(X_raw_tr)
        clf_raw = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=s)
        clf_raw.fit(sc_raw.transform(X_raw_tr), y_tr)
        pred_raw = clf_raw.predict(sc_raw.transform(X_raw_vl))
        acc_raw = float(accuracy_score(y_vl, pred_raw))
        bal_raw = float(balanced_accuracy_score(y_vl, pred_raw))
        p_r, r_r, f1_raw, _ = precision_recall_fscore_support(y_vl, pred_raw, average="macro", zero_division=0)
        
        # B. Projected Subspace Classifier
        sc_proj = StandardScaler().fit(X_proj_tr)
        clf_proj = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=s)
        clf_proj.fit(sc_proj.transform(X_proj_tr), y_tr)
        pred_proj = clf_proj.predict(sc_proj.transform(X_proj_vl))
        acc_proj = float(accuracy_score(y_vl, pred_proj))
        bal_proj = float(balanced_accuracy_score(y_vl, pred_proj))
        p_p, r_p, f1_proj, _ = precision_recall_fscore_support(y_vl, pred_proj, average="macro", zero_division=0)
        
        raw_results.append({"seed": s, "accuracy": round(acc_raw, 4), "balanced_acc": round(bal_raw, 4), "macro_f1": round(float(f1_raw), 4)})
        proj_results.append({"seed": s, "accuracy": round(acc_proj, 4), "balanced_acc": round(bal_proj, 4), "macro_f1": round(float(f1_proj), 4)})
        paired_deltas.append({
            "seed": s,
            "accuracy_delta": round(acc_proj - acc_raw, 4),
            "macro_f1_delta": round(float(f1_proj) - float(f1_raw), 4)
        })
        print(f"  Raw SBERT:   Acc={acc_raw:.4f}, MacroF1={f1_raw:.4f}")
        print(f"  Contrastive: Acc={acc_proj:.4f}, MacroF1={f1_proj:.4f} (Delta: {acc_proj - acc_raw:+.4f})")
        
    accs_raw = [r["accuracy"] for r in raw_results]
    f1s_raw = [r["macro_f1"] for r in raw_results]
    accs_proj = [r["accuracy"] for r in proj_results]
    f1s_proj = [r["macro_f1"] for r in proj_results]
    deltas_acc = [r["accuracy_delta"] for r in paired_deltas]
    deltas_f1 = [r["macro_f1_delta"] for r in paired_deltas]
    
    report = {
        "benchmark_metadata": {
            "evaluation_set": "dual_unseen_val_v1 (296 rows post-quarantine)",
            "representation_protocol": "InfoNCE on positive pairs (Good Fit + Potential Fit) in train partition ONLY",
            "zero_leakage_guarantee": "Validation partition never touched during projector training or scaler fitting",
            "classifier_standard": "LogisticRegression(C=1.0, class_weight='balanced', max_iter=1000)"
        },
        "raw_sbert_5seeds": {
            "accuracy_mean": round(float(np.mean(accs_raw)), 4),
            "accuracy_std": round(float(np.std(accs_raw)), 4),
            "macro_f1_mean": round(float(np.mean(f1s_raw)), 4),
            "macro_f1_std": round(float(np.std(f1s_raw)), 4),
            "runs": raw_results
        },
        "contrastive_projection_5seeds": {
            "accuracy_mean": round(float(np.mean(accs_proj)), 4),
            "accuracy_std": round(float(np.std(accs_proj)), 4),
            "macro_f1_mean": round(float(np.mean(f1s_proj)), 4),
            "macro_f1_std": round(float(np.std(f1s_proj)), 4),
            "runs": proj_results
        },
        "paired_representation_gain": {
            "accuracy_delta_mean": round(float(np.mean(deltas_acc)), 4),
            "accuracy_delta_std": round(float(np.std(deltas_acc)), 4),
            "macro_f1_delta_mean": round(float(np.mean(deltas_f1)), 4),
            "macro_f1_delta_std": round(float(np.std(deltas_f1)), 4),
            "95_ci_accuracy_delta": [
                round(float(np.mean(deltas_acc) - 1.96 * np.std(deltas_acc) / np.sqrt(len(SEEDS))), 4),
                round(float(np.mean(deltas_acc) + 1.96 * np.std(deltas_acc) / np.sqrt(len(SEEDS))), 4)
            ]
        }
    }
    
    with open(OUT_DIR / "contrastive_5seed_replication.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print("\nContrastive 5-seed report saved to experiments/phase12f3_1/results/contrastive_5seed_replication.json")
    print(f"Raw SBERT Mean Acc:     {report['raw_sbert_5seeds']['accuracy_mean']:.4f} +/- {report['raw_sbert_5seeds']['accuracy_std']:.4f}")
    print(f"Contrastive Mean Acc:   {report['contrastive_projection_5seeds']['accuracy_mean']:.4f} +/- {report['contrastive_projection_5seeds']['accuracy_std']:.4f}")
    print(f"Mean Accuracy Gain:     {report['paired_representation_gain']['accuracy_delta_mean']:+.4f} (95% CI: {report['paired_representation_gain']['95_ci_accuracy_delta']})")

if __name__ == "__main__":
    main()
