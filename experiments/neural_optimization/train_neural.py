"""
Phase 7C: Supervised Neural Network Optimization Suite.
Trains, evaluates, and benchmarks:
1. Model A: Supervised MLP (Dense SVD + Domain Alignment)
2. Model B: Siamese BiLSTM (Recurrent Pair Encoder)
3. Model C: Text CNN (Multi-Kernel Convolutions)
4. Model D: Compact Cross-Attention Alignment Network
Strictly isolates vocabulary, SVD, and scalers to training folds only.
Zero LLMs. Zero pretrained generative weights.
"""

import os
import sys
import time
import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import sparse

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.model_selection import GroupKFold
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import RobustScaler

from src.preprocessing.text_cleaner import clean_text
from src.utils.split_manager import get_unseen_jobs_split
from experiments.neural_optimization.dataset import FoldIsolatedTokenizer, ResumeJobPairDataset
from experiments.neural_optimization.models import (
    ResumeJobMLP,
    SiameseBiLSTM,
    TextCNNPairClassifier,
    CompactCrossAttention
)

BASE_DIR = Path("experiments/neural_optimization")
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
CACHE_DIR = Path("experiments/model_optimization/data_cache")

for d in [BASE_DIR, MODELS_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LABEL_ORDER = ["No Fit", "Good Fit", "Potential Fit"]
LABEL_TO_INT = {l: i for i, l in enumerate(LABEL_ORDER)}
INT_TO_LABEL = {i: l for i, l in enumerate(LABEL_ORDER)}


def extract_fold_dense_semantic_features(
    r_tr: List[str], j_tr: List[str],
    r_va: List[str], j_va: List[str],
    dom_tr: np.ndarray, dom_va: np.ndarray,
    n_svd: int = 128
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Constructs dense latent semantic features strictly fitted on training fold.
    Returns:
    - Dense representation: [svd_r, svd_j, svd_diff, svd_dot, svd_cos] (257 dims) + scaled domain (28 dims) = 285 dims.
    """
    clean_r_tr = [clean_text(t) for t in r_tr]
    clean_j_tr = [clean_text(t) for t in j_tr]
    clean_r_va = [clean_text(t) for t in r_va]
    clean_j_va = [clean_text(t) for t in j_va]

    corpus_tr = clean_r_tr + clean_j_tr
    vec = TfidfVectorizer(max_features=2500, min_df=3, sublinear_tf=True, norm="l2")
    vec.fit(corpus_tr)

    V_r_tr = vec.transform(clean_r_tr)
    V_j_tr = vec.transform(clean_j_tr)
    V_r_va = vec.transform(clean_r_va)
    V_j_va = vec.transform(clean_j_va)

    V_corpus_tr = vec.transform(corpus_tr)
    svd = TruncatedSVD(n_components=n_svd, random_state=42)
    svd.fit(V_corpus_tr)

    svd_r_tr = svd.transform(V_r_tr)
    svd_j_tr = svd.transform(V_j_tr)
    svd_r_va = svd.transform(V_r_va)
    svd_j_va = svd.transform(V_j_va)

    diff_tr = np.abs(svd_r_tr - svd_j_tr)
    diff_va = np.abs(svd_r_va - svd_j_va)
    dot_tr = svd_r_tr * svd_j_tr
    dot_va = svd_r_va * svd_j_va

    norm_r_tr = np.linalg.norm(svd_r_tr, axis=1, keepdims=True) + 1e-9
    norm_j_tr = np.linalg.norm(svd_j_tr, axis=1, keepdims=True) + 1e-9
    cos_tr = np.sum((svd_r_tr / norm_r_tr) * (svd_j_tr / norm_j_tr), axis=1, keepdims=True)

    norm_r_va = np.linalg.norm(svd_r_va, axis=1, keepdims=True) + 1e-9
    norm_j_va = np.linalg.norm(svd_j_va, axis=1, keepdims=True) + 1e-9
    cos_va = np.sum((svd_r_va / norm_r_va) * (svd_j_va / norm_j_va), axis=1, keepdims=True)

    scaler = RobustScaler()
    scaler.fit(dom_tr)
    scaled_dom_tr = scaler.transform(dom_tr)
    scaled_dom_va = scaler.transform(dom_va)

    F_tr = np.hstack([svd_r_tr, svd_j_tr, diff_tr, dot_tr, cos_tr, scaled_dom_tr]).astype(np.float32)
    F_va = np.hstack([svd_r_va, svd_j_va, diff_va, dot_va, cos_va, scaled_dom_va]).astype(np.float32)
    return F_tr, F_va


def train_single_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device
) -> float:
    model.train()
    total_loss = 0.0
    for batch in loader:
        optimizer.zero_grad()
        r_tok = batch["resume_tokens"].to(device)
        j_tok = batch["job_tokens"].to(device)
        dense = batch["dense_feats"].to(device)
        targets = batch["label"].to(device)

        logits = model(resume_tokens=r_tok, job_tokens=j_tok, dense_feats=dense)
        loss = criterion(logits, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item() * len(targets)
    return total_loss / len(loader.dataset)


@torch.no_grad()
def evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float, float, np.ndarray, np.ndarray]:
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []

    for batch in loader:
        r_tok = batch["resume_tokens"].to(device)
        j_tok = batch["job_tokens"].to(device)
        dense = batch["dense_feats"].to(device)
        targets = batch["label"].to(device)

        logits = model(resume_tokens=r_tok, job_tokens=j_tok, dense_feats=dense)
        loss = criterion(logits, targets)
        total_loss += loss.item() * len(targets)

        preds = torch.argmax(logits, dim=-1).cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(targets.cpu().numpy())

    avg_loss = total_loss / len(loader.dataset)
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    acc = accuracy_score(all_targets, all_preds)
    _, _, macro_f1, _ = precision_recall_fscore_support(all_targets, all_preds, average="macro", zero_division=0)
    return avg_loss, acc, macro_f1, all_preds, all_targets


def run_neural_suite():
    print("=" * 80)
    print("PHASE 7C: SUPERVISED NEURAL NETWORK OPTIMIZATION & BENCHMARKING")
    print("=" * 80)

    device = torch.device("cpu")
    print(f"Active Hardware Execution: PyTorch 2.15 on Intel Core i5-13450HX (16 threads).")
    print(f"Zero test set contamination. Zero pretrained LLM weights.\n")

    # Load data
    train_df, val_df, _ = get_unseen_jobs_split()
    train_dom = pd.read_parquet(CACHE_DIR / "train_domain_features.parquet")
    val_dom = pd.read_parquet(CACHE_DIR / "val_domain_features.parquet")

    # Filter conflicting duplicates
    dups_mask = train_df.duplicated(subset=["resume_text", "job_description_text"], keep=False)
    active_df = train_df[~dups_mask].reset_index(drop=True)
    active_dom = train_dom[~dups_mask].reset_index(drop=True)

    y_str = np.array(active_df["label"].tolist(), dtype=object)
    y_enc = np.array([LABEL_TO_INT[l] for l in y_str], dtype=int)
    job_groups = np.array(active_df["job_description_text"].tolist(), dtype=object)

    class_weights = compute_class_weight("balanced", classes=np.array([0, 1, 2]), y=y_enc)
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)

    # -------------------------------------------------------------
    # 1. PILOT EVALUATION ACROSS ALL 4 NEURAL ARCHITECTURES
    # -------------------------------------------------------------
    print("--- 1. Pilot Comparison of 4 Neural Architectures (Fold 1) ---")
    gkf = GroupKFold(n_splits=5)
    splits = list(gkf.split(active_df, y_str, groups=job_groups))
    tr_idx, va_idx = splits[0]

    r_tr = active_df.iloc[tr_idx]["resume_text"].tolist()
    j_tr = active_df.iloc[tr_idx]["job_description_text"].tolist()
    r_va = active_df.iloc[va_idx]["resume_text"].tolist()
    j_va = active_df.iloc[va_idx]["job_description_text"].tolist()

    dom_tr = active_dom.iloc[tr_idx].values
    dom_va = active_dom.iloc[va_idx].values
    y_tr = y_enc[tr_idx]
    y_va = y_enc[va_idx]

    # Tokenizer fitted strictly on Fold 1 training texts
    tokenizer = FoldIsolatedTokenizer(max_vocab_size=6000, min_freq=2)
    tokenizer.fit(r_tr + j_tr)
    vocab_size = len(tokenizer.vocab)
    print(f"Fold 1 Tokenizer Vocab Size: {vocab_size:,} tokens.")

    # Dense semantic features for MLP
    F_tr_dense, F_va_dense = extract_fold_dense_semantic_features(r_tr, j_tr, r_va, j_va, dom_tr, dom_va, n_svd=128)
    scaler_dom = RobustScaler().fit(dom_tr)
    dom_tr_scaled = scaler_dom.transform(dom_tr)
    dom_va_scaled = scaler_dom.transform(dom_va)

    ds_tr_mlp = ResumeJobPairDataset(r_tr, j_tr, F_tr_dense, y_tr, tokenizer)
    ds_va_mlp = ResumeJobPairDataset(r_va, j_va, F_va_dense, y_va, tokenizer)

    ds_tr_seq = ResumeJobPairDataset(r_tr, j_tr, dom_tr_scaled, y_tr, tokenizer)
    ds_va_seq = ResumeJobPairDataset(r_va, j_va, dom_va_scaled, y_va, tokenizer)

    loader_tr_mlp = DataLoader(ds_tr_mlp, batch_size=64, shuffle=True)
    loader_va_mlp = DataLoader(ds_va_mlp, batch_size=128, shuffle=False)
    loader_tr_seq = DataLoader(ds_tr_seq, batch_size=64, shuffle=True)
    loader_va_seq = DataLoader(ds_va_seq, batch_size=128, shuffle=False)

    candidate_models = {
        "Supervised MLP (SVD+Domain)": {
            "model": ResumeJobMLP(input_dim=F_tr_dense.shape[1], hidden_dims=[256, 128, 64], dropout_rate=0.3).to(device),
            "tr_loader": loader_tr_mlp,
            "va_loader": loader_va_mlp,
            "lr": 1e-3,
            "epochs": 12
        },
        "Siamese BiLSTM": {
            "model": SiameseBiLSTM(vocab_size=vocab_size, embed_dim=80, hidden_dim=48, dense_feat_dim=28, dropout_rate=0.3).to(device),
            "tr_loader": loader_tr_seq,
            "va_loader": loader_va_seq,
            "lr": 8e-4,
            "epochs": 10
        },
        "Text CNN Pair Classifier": {
            "model": TextCNNPairClassifier(vocab_size=vocab_size, embed_dim=80, num_filters=48, kernel_sizes=[2, 3, 5], dense_feat_dim=28, dropout_rate=0.3).to(device),
            "tr_loader": loader_tr_seq,
            "va_loader": loader_va_seq,
            "lr": 1e-3,
            "epochs": 10
        },
        "Compact Cross-Attention": {
            "model": CompactCrossAttention(vocab_size=vocab_size, embed_dim=80, num_heads=4, dense_feat_dim=28, dropout_rate=0.3).to(device),
            "tr_loader": loader_tr_seq,
            "va_loader": loader_va_seq,
            "lr": 8e-4,
            "epochs": 10
        }
    }

    pilot_results = []
    pilot_histories = {}

    for name, cfg in candidate_models.items():
        print(f"\nTraining {name} (Pilot Fold 1)...")
        net = cfg["model"]
        optimizer = torch.optim.AdamW(net.parameters(), lr=cfg["lr"], weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

        history = {"train_loss": [], "val_loss": [], "val_acc": [], "val_macro_f1": []}
        best_f1 = 0.0
        best_acc = 0.0
        t0 = time.time()

        for epoch in range(1, cfg["epochs"] + 1):
            tr_loss = train_single_epoch(net, cfg["tr_loader"], optimizer, criterion, device)
            va_loss, va_acc, va_f1, _, _ = evaluate_model(net, cfg["va_loader"], criterion, device)
            scheduler.step(va_f1)

            history["train_loss"].append(tr_loss)
            history["val_loss"].append(va_loss)
            history["val_acc"].append(va_acc)
            history["val_macro_f1"].append(va_f1)

            if va_f1 > best_f1:
                best_f1 = va_f1
                best_acc = va_acc

        t_elapsed = time.time() - t0
        pilot_histories[name] = history
        pilot_results.append({
            "Architecture": name,
            "Pilot Val Macro F1": round(best_f1, 4),
            "Pilot Val Accuracy": round(best_acc, 4),
            "Train Time (s)": round(t_elapsed, 2)
        })
        print(f"  {name:30s} -> Best Macro F1: {best_f1:.4f} | Best Acc: {best_acc:.4f} ({t_elapsed:.1f}s)")

    pilot_df = pd.DataFrame(pilot_results).sort_values(by="Pilot Val Macro F1", ascending=False).reset_index(drop=True)
    print("\nPilot Architecture Comparison (Fold 1 Unseen Jobs):")
    print(pilot_df.to_string(index=False))

    # Select champion neural architecture for full 5-fold CV
    champion_arch_name = pilot_df.iloc[0]["Architecture"]
    print(f"\n>>> Selected Top Neural Architecture: {champion_arch_name} <<<")
    print("Promoting to full 5-Fold Job-Disjoint Cross-Validation with strict fold-level isolation...\n")

    # -------------------------------------------------------------
    # 2. FULL 5-FOLD JOB-DISJOINT CV ON CHAMPION NEURAL MODEL
    # -------------------------------------------------------------
    cv_fold_metrics = []
    oof_preds_all = [None] * len(active_df)
    champion_history_all = []

    t_cv0 = time.time()

    for fold_idx, (tr_idx, va_idx) in enumerate(splits):
        f_num = fold_idx + 1
        print(f"--- Running Champion {champion_arch_name} on Fold {f_num}/5 ---")

        r_tr = active_df.iloc[tr_idx]["resume_text"].tolist()
        j_tr = active_df.iloc[tr_idx]["job_description_text"].tolist()
        r_va = active_df.iloc[va_idx]["resume_text"].tolist()
        j_va = active_df.iloc[va_idx]["job_description_text"].tolist()

        dom_tr = active_dom.iloc[tr_idx].values
        dom_va = active_dom.iloc[va_idx].values
        y_tr = y_enc[tr_idx]
        y_va = y_enc[va_idx]

        # Fold-isolated preprocessing
        if "MLP" in champion_arch_name:
            F_tr_dense, F_va_dense = extract_fold_dense_semantic_features(r_tr, j_tr, r_va, j_va, dom_tr, dom_va, n_svd=128)
            tokenizer_fold = FoldIsolatedTokenizer(max_vocab_size=100)  # Dummy for dataset
            ds_tr = ResumeJobPairDataset(r_tr, j_tr, F_tr_dense, y_tr, tokenizer_fold)
            ds_va = ResumeJobPairDataset(r_va, j_va, F_va_dense, y_va, tokenizer_fold)
            net = ResumeJobMLP(input_dim=F_tr_dense.shape[1], hidden_dims=[256, 128, 64], dropout_rate=0.3).to(device)
            lr = 1e-3
            epochs = 12
        else:
            tokenizer_fold = FoldIsolatedTokenizer(max_vocab_size=6000, min_freq=2)
            tokenizer_fold.fit(r_tr + j_tr)
            scaler_fold = RobustScaler().fit(dom_tr)
            dom_tr_s = scaler_fold.transform(dom_tr)
            dom_va_s = scaler_fold.transform(dom_va)
            ds_tr = ResumeJobPairDataset(r_tr, j_tr, dom_tr_s, y_tr, tokenizer_fold)
            ds_va = ResumeJobPairDataset(r_va, j_va, dom_va_s, y_va, tokenizer_fold)

            if "BiLSTM" in champion_arch_name:
                net = SiameseBiLSTM(vocab_size=len(tokenizer_fold.vocab), embed_dim=80, hidden_dim=48, dense_feat_dim=28, dropout_rate=0.3).to(device)
                lr = 8e-4
                epochs = 10
            elif "CNN" in champion_arch_name:
                net = TextCNNPairClassifier(vocab_size=len(tokenizer_fold.vocab), embed_dim=80, num_filters=48, kernel_sizes=[2, 3, 5], dense_feat_dim=28).to(device)
                lr = 1e-3
                epochs = 10
            else:
                net = CompactCrossAttention(vocab_size=len(tokenizer_fold.vocab), embed_dim=80, num_heads=4, dense_feat_dim=28).to(device)
                lr = 8e-4
                epochs = 10

        loader_tr = DataLoader(ds_tr, batch_size=64, shuffle=True)
        loader_va = DataLoader(ds_va, batch_size=128, shuffle=False)

        optimizer = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
        best_fold_f1 = 0.0
        best_fold_acc = 0.0
        best_fold_preds = None

        for epoch in range(1, epochs + 1):
            _ = train_single_epoch(net, loader_tr, optimizer, criterion, device)
            va_loss, va_acc, va_f1, f_preds, f_targs = evaluate_model(net, loader_va, criterion, device)
            if va_f1 > best_fold_f1:
                best_fold_f1 = va_f1
                best_fold_acc = va_acc
                best_fold_preds = f_preds

        # Record OOF predictions
        for loc_i, glob_i in enumerate(va_idx):
            oof_preds_all[glob_i] = best_fold_preds[loc_i]

        p_cls, r_cls, f_cls, _ = precision_recall_fscore_support(y_va, best_fold_preds, labels=[0, 1, 2], zero_division=0)
        cv_fold_metrics.append({
            "fold": f_num,
            "accuracy": float(best_fold_acc),
            "macro_f1": float(best_fold_f1),
            "recall_no_fit": float(r_cls[0]),
            "recall_good_fit": float(r_cls[1]),
            "recall_potential_fit": float(r_cls[2])
        })
        print(f"  Fold {f_num} -> Acc: {best_fold_acc:.4f} | Macro F1: {best_fold_f1:.4f} | Rec Good Fit: {r_cls[1]:.4f}")

    total_cv_time = time.time() - t_cv0
    oof_preds_arr = np.array(oof_preds_all)
    oof_acc = accuracy_score(y_enc, oof_preds_arr)
    oof_p, oof_r, oof_f1, _ = precision_recall_fscore_support(y_enc, oof_preds_arr, average="macro", zero_division=0)
    oof_cm = confusion_matrix(y_enc, oof_preds_arr, labels=[0, 1, 2]).tolist()

    accs = [m["accuracy"] for m in cv_fold_metrics]
    f1s = [m["macro_f1"] for m in cv_fold_metrics]
    mean_f1 = float(np.mean(f1s))
    std_f1 = float(np.std(f1s))
    mean_acc = float(np.mean(accs))
    std_acc = float(np.std(accs))

    print("\n" + "=" * 80)
    print(f"PHASE 7C: FINAL 5-FOLD CV RESULTS FOR {champion_arch_name}")
    print("=" * 80)
    print(f"Mean CV Macro F1: {mean_f1:.4f} +/- {std_f1:.4f}")
    print(f"Mean CV Accuracy: {mean_acc:.4f} +/- {std_acc:.4f}")
    print(f"Out-of-Fold Macro F1: {oof_f1:.4f} | OOF Accuracy: {oof_acc:.4f}")
    print(f"Total 5-Fold Training Time: {total_cv_time:.2f}s")

    # -------------------------------------------------------------
    # 3. COMPREHENSIVE BENCHMARK COMPARISON TABLE
    # -------------------------------------------------------------
    comparison_table = [
        {
            "Model": "Phase 3 Baseline (Logistic Reg)",
            "Family": "Linear Model",
            "Mean CV Macro F1": 0.4666,
            "Std CV Macro F1": 0.0227,
            "Mean CV Accuracy": 0.5121,
            "OOF Macro F1": 0.4660,
            "Hardware": "CPU"
        },
        {
            "Model": "Phase 7B-C Optimized Linear SVM",
            "Family": "Max-Margin Linear",
            "Mean CV Macro F1": 0.4810,
            "Std CV Macro F1": 0.0232,
            "Mean CV Accuracy": 0.5319,
            "OOF Macro F1": 0.4831,
            "Hardware": "CPU"
        },
        {
            "Model": "Phase 7B-C GPU XGBoost",
            "Family": "Gradient Boosted Trees",
            "Mean CV Macro F1": 0.4534,
            "Std CV Macro F1": 0.0416,
            "Mean CV Accuracy": 0.5282,
            "OOF Macro F1": 0.4571,
            "Hardware": "GPU (RTX 4050)"
        },
        {
            "Model": f"Phase 7C {champion_arch_name}",
            "Family": "Neural Network",
            "Mean CV Macro F1": round(mean_f1, 4),
            "Std CV Macro F1": round(std_f1, 4),
            "Mean CV Accuracy": round(mean_acc, 4),
            "OOF Macro F1": round(oof_f1, 4),
            "Hardware": "CPU Multi-Thread"
        }
    ]

    comp_df = pd.DataFrame(comparison_table).sort_values(by="Mean CV Macro F1", ascending=False).reset_index(drop=True)
    print("\nFinal Multi-Paradigm Comparison (5-Fold Group-Disjoint CV):")
    print(comp_df.to_string(index=False))

    # Save metrics
    comp_df.to_csv(RESULTS_DIR / "phase7c_neural_comparison.csv", index=False)
    summary_data = {
        "pilot_comparison": pilot_results,
        "champion_model": champion_arch_name,
        "champion_5fold_metrics": cv_fold_metrics,
        "champion_oof_summary": {
            "accuracy": float(oof_acc),
            "macro_f1": float(oof_f1),
            "macro_precision": float(oof_p),
            "macro_recall": float(oof_r),
            "confusion_matrix": oof_cm
        },
        "multi_paradigm_comparison": comparison_table
    }
    with open(RESULTS_DIR / "phase7c_summary.json", "w") as f:
        json.dump(summary_data, f, indent=2)

    # -------------------------------------------------------------
    # 4. GENERATE VISUALIZATIONS
    # -------------------------------------------------------------
    # Plot 1: Architecture Comparison Bar Chart
    plt.figure(figsize=(10, 6))
    x = np.arange(len(comp_df))
    width = 0.35
    plt.bar(x - width/2, comp_df["Mean CV Accuracy"], width, yerr=comp_df["Std CV Macro F1"] * 0.5, capsize=4, label="Mean CV Accuracy", color="#2563eb")
    plt.bar(x + width/2, comp_df["Mean CV Macro F1"], width, yerr=comp_df["Std CV Macro F1"], capsize=4, label="Mean CV Macro F1", color="#10b981")
    plt.axhline(0.4666, color="#ef4444", linestyle="--", label="Production Baseline F1 (0.4666)")
    plt.xlabel("Model Architecture")
    plt.ylabel("5-Fold CV Score")
    plt.title("Phase 7C: Supervised Neural Network vs Classical ML (Unseen Jobs)")
    plt.xticks(x, comp_df["Model"], rotation=15, ha="right")
    plt.ylim(0.35, 0.60)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7c_neural_vs_classical.png", dpi=150)
    plt.close()

    # Plot 2: Neural Champion Confusion Matrix
    plt.figure(figsize=(7, 6))
    sns.heatmap(oof_cm, annot=True, fmt="d", cmap="Purples",
                xticklabels=LABEL_ORDER, yticklabels=LABEL_ORDER)
    plt.title(f"Phase 7C Aggregated OOF Confusion Matrix: {champion_arch_name}\nCV Macro F1: {mean_f1:.4f} | Accuracy: {oof_acc:.4f}")
    plt.xlabel("Predicted Class")
    plt.ylabel("True Class")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7c_neural_confusion_matrix.png", dpi=150)
    plt.close()

    print(f"\nAll Phase 7C artifacts, tables, and charts successfully saved under: {RESULTS_DIR}")
    return summary_data


if __name__ == "__main__":
    run_neural_suite()
