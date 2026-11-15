"""
Neural Dataset and Fold-Isolated Text Tokenizer for Phase 7C.
Strictly fits token vocabulary on training folds only.
Preserves technical tokens (e.g., C++, C#, .NET, Node.js).
"""

import re
from collections import Counter
from typing import Dict, List, Tuple, Optional
import numpy as np
import torch
from torch.utils.data import Dataset

from src.preprocessing.text_cleaner import clean_text


class FoldIsolatedTokenizer:
    """
    Word-level tokenizer fitted exclusively on training-fold texts.
    Preserves specialized technical tokens like C++, C#, .NET, etc.
    """

    TOKEN_PATTERN = re.compile(r"(?u)\b[a-zA-Z0-9_\.\#\+\-]+\b")

    def __init__(self, max_vocab_size: int = 8000, min_freq: int = 2):
        self.max_vocab_size = max_vocab_size
        self.min_freq = min_freq
        self.vocab: Dict[str, int] = {"<PAD>": 0, "<UNK>": 1}
        self.inv_vocab: Dict[int, str] = {0: "<PAD>", 1: "<UNK>"}
        self.is_fitted = False

    def tokenize(self, text: str) -> List[str]:
        cleaned = clean_text(text).lower()
        return self.TOKEN_PATTERN.findall(cleaned)

    def fit(self, texts: List[str]):
        counter = Counter()
        for t in texts:
            tokens = self.tokenize(t)
            counter.update(tokens)

        # Retain frequent tokens
        for token, count in counter.most_common(self.max_vocab_size):
            if count >= self.min_freq and token not in self.vocab:
                idx = len(self.vocab)
                self.vocab[token] = idx
                self.inv_vocab[idx] = token

        self.is_fitted = True
        return self

    def encode(self, text: str, max_len: int = 250) -> List[int]:
        tokens = self.tokenize(text)
        unk_idx = self.vocab["<UNK>"]
        ids = [self.vocab.get(tok, unk_idx) for tok in tokens[:max_len]]
        # Padding
        if len(ids) < max_len:
            ids = ids + [0] * (max_len - len(ids))
        return ids


class ResumeJobPairDataset(Dataset):
    """
    PyTorch Dataset providing:
    - resume_tokens: (seq_len_r,)
    - job_tokens: (seq_len_j,)
    - dense_features: (n_dense_features,)
    - label: int (0: No Fit, 1: Good Fit, 2: Potential Fit)
    """

    def __init__(
        self,
        resumes: List[str],
        jobs: List[str],
        dense_feats: np.ndarray,
        labels: Optional[np.ndarray],
        tokenizer: FoldIsolatedTokenizer,
        max_r_len: int = 250,
        max_j_len: int = 180
    ):
        self.resumes = resumes
        self.jobs = jobs
        self.dense_feats = torch.tensor(dense_feats, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long) if labels is not None else None
        self.tokenizer = tokenizer
        self.max_r_len = max_r_len
        self.max_j_len = max_j_len

        # Pre-encode tokens
        self.encoded_r = [
            torch.tensor(self.tokenizer.encode(r, max_len=self.max_r_len), dtype=torch.long)
            for r in self.resumes
        ]
        self.encoded_j = [
            torch.tensor(self.tokenizer.encode(j, max_len=self.max_j_len), dtype=torch.long)
            for j in self.jobs
        ]

    def __len__(self):
        return len(self.resumes)

    def __getitem__(self, idx):
        item = {
            "resume_tokens": self.encoded_r[idx],
            "job_tokens": self.encoded_j[idx],
            "dense_feats": self.dense_feats[idx]
        }
        if self.labels is not None:
            item["label"] = self.labels[idx]
        return item
