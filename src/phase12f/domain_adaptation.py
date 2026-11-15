"""
src/phase12f/domain_adaptation.py
Unsupervised Domain Adaptation and Self-Supervised Representation Learning
using the official English Djinni corpus (210,250 CVs and 141,897 JDs).
Learns domain-specific skill representations, co-occurrence topologies,
and contrastive projection heads without requiring human ground-truth labels.
"""

import os
import re
from typing import Dict, List, Optional, Tuple, Set
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.feature_extraction.text import TfidfVectorizer

from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text


class DomainSkillGraph:
    """
    Learns skill co-occurrence topologies and domain clustering from unlabelled Djinni documents.
    """

    def __init__(self, top_n_skills: int = 150):
        self.top_n_skills = top_n_skills
        self.skill_engine = SkillEngine()
        self.skill_to_idx: Dict[str, int] = {}
        self.idx_to_skill: Dict[int, str] = {}
        self.cooccurrence_matrix: Optional[np.ndarray] = None
        self.domain_clusters: Dict[str, List[str]] = {}

    def fit_from_corpus(self, text_corpus: List[str]) -> "DomainSkillGraph":
        """Builds co-occurrence graph across a sample of documents."""
        doc_skills_list = []
        skill_counts: Dict[str, int] = {}

        for text in text_corpus:
            skills = self.skill_engine.extract_skills(clean_text(text))
            if skills:
                doc_skills_list.append(skills)
                for s in skills:
                    skill_counts[s] = skill_counts.get(s, 0) + 1

        # Select top N most frequent skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:self.top_n_skills]
        self.skill_to_idx = {s: i for i, (s, _) in enumerate(sorted_skills)}
        self.idx_to_skill = {i: s for s, i in self.skill_to_idx.items()}

        V = len(self.skill_to_idx)
        self.cooccurrence_matrix = np.zeros((V, V), dtype=np.float32)

        for skills in doc_skills_list:
            indices = [self.skill_to_idx[s] for s in skills if s in self.skill_to_idx]
            for i in indices:
                for j in indices:
                    if i != j:
                        self.cooccurrence_matrix[i, j] += 1.0

        # Normalize to conditional probabilities P(s_j | s_i)
        row_sums = self.cooccurrence_matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        self.cooccurrence_matrix = self.cooccurrence_matrix / row_sums

        return self

    def get_related_skills(self, skill: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Returns the most co-occurring skills in the domain corpus."""
        skill_clean = skill.lower().strip()
        if skill_clean not in self.skill_to_idx or self.cooccurrence_matrix is None:
            return []
        idx = self.skill_to_idx[skill_clean]
        probs = self.cooccurrence_matrix[idx]
        top_indices = np.argsort(probs)[::-1][:top_k]
        return [(self.idx_to_skill[i], float(probs[i])) for i in top_indices if probs[i] > 0]


class ContrastivePairDataset(Dataset):
    """
    Dataset of defensible self-supervised positive and hard-negative pairs.
    Positive pairs:
    - View A: Candidate title/summary vs View B: Candidate technical skills & responsibilities
    - View A: JD title/requirements vs View B: JD duties & tech stack
    Negative pairs:
    - Sampled from different tech domains.
    """

    def __init__(self, anchor_texts: List[str], positive_texts: List[str], negative_texts: List[str]):
        self.anchors = anchor_texts
        self.positives = positive_texts
        self.negatives = negative_texts
        self.length = min(len(self.anchors), len(self.positives), len(self.negatives))

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        return {
            "anchor": self.anchors[idx],
            "positive": self.positives[idx],
            "negative": self.negatives[idx]
        }


class DomainAdaptiveProjector(nn.Module):
    """
    Lightweight self-supervised domain adaptation projection head.
    Projects general embeddings (e.g. MiniLM 384-d or SBERT 768-d) into a specialized
    resume-job matching subspace trained with Triplet / InfoNCE contrastive loss.
    """

    def __init__(self, input_dim: int = 384, hidden_dim: int = 256, output_dim: int = 128):
        super().__init__()
        self.projector = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.projector(x)
        # L2 normalize
        return nn.functional.normalize(z, p=2, dim=-1)


def train_domain_projector(
    projector: DomainAdaptiveProjector,
    anchor_embs: np.ndarray,
    pos_embs: np.ndarray,
    neg_embs: np.ndarray,
    epochs: int = 5,
    batch_size: int = 64,
    lr: float = 1e-3,
    margin: float = 0.3
) -> Dict:
    """
    Trains domain projection head using Triplet Margin Loss on CPU.
    """
    device = torch.device("cpu")
    projector.to(device)
    optimizer = optim.AdamW(projector.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.TripletMarginLoss(margin=margin, p=2)

    n_samples = len(anchor_embs)
    indices = np.arange(n_samples)

    loss_history = []
    projector.train()

    for epoch in range(epochs):
        np.random.shuffle(indices)
        epoch_losses = []
        for start_idx in range(0, n_samples, batch_size):
            batch_idx = indices[start_idx:start_idx + batch_size]
            a = torch.tensor(anchor_embs[batch_idx], dtype=torch.float32, device=device)
            p = torch.tensor(pos_embs[batch_idx], dtype=torch.float32, device=device)
            n = torch.tensor(neg_embs[batch_idx], dtype=torch.float32, device=device)

            optimizer.zero_grad()
            z_a = projector(a)
            z_p = projector(p)
            z_n = projector(n)

            loss = criterion(z_a, z_p, z_n)
            loss.backward()
            optimizer.step()

            epoch_losses.append(loss.item())

        mean_loss = float(np.mean(epoch_losses))
        loss_history.append(mean_loss)

    return {
        "final_loss": round(loss_history[-1], 4),
        "loss_history": [round(l, 4) for l in loss_history],
        "epochs": epochs
    }
