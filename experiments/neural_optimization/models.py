"""
Neural Architectures for Supervised Resume-Job Matching (Phase 7C):
1. Model A: ResumeJobMLP (Dense Latent Semantic & Domain Alignment Network)
2. Model B: SiameseBiLSTM (Recurrent Pair Encoder with Interaction Head)
3. Model C: TextCNNPairClassifier (Multi-Kernel Convolutions with Max-Pooling)
4. Model D: CompactCrossAttention (Supervised Cross-Attention Alignment Network)
Zero external generative language models. Zero pretrained LLM weights.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResumeJobMLP(nn.Module):
    """
    Model A: Compact, regularized Multi-Layer Perceptron.
    Takes dense latent semantic features (SVD components, cosine distances) + domain alignment metrics.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list = [256, 128, 64],
        num_classes: int = 3,
        dropout_rate: float = 0.3
    ):
        super().__init__()
        layers = []
        in_dim = input_dim

        for i, h_dim in enumerate(hidden_dims):
            layers.append(nn.Linear(in_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.GELU())
            rate = dropout_rate if i == 0 else dropout_rate * 0.75
            layers.append(nn.Dropout(rate))
            in_dim = h_dim

        layers.append(nn.Linear(in_dim, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, dense_feats: torch.Tensor, **kwargs) -> torch.Tensor:
        return self.network(dense_feats)


class SiameseBiLSTM(nn.Module):
    """
    Model B: Siamese Bidirectional LSTM Text Encoder.
    Processes resume and job tokens through a shared BiLSTM, computes
    rich vector interactions ([u, v, |u-v|, u*v, cos]), fuses domain metrics,
    and classifies via a multiclass MLP head.
    """

    def __init__(
        self,
        vocab_size: int,
        embed_dim: int = 100,
        hidden_dim: int = 64,
        dense_feat_dim: int = 28,
        num_classes: int = 3,
        dropout_rate: float = 0.3
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=1,
            bidirectional=True,
            batch_first=True
        )

        encoder_out_dim = hidden_dim * 2  # Bidirectional

        # Interaction dimension: [h_r, h_j, |h_r - h_j|, h_r * h_j, cos] -> 4 * encoder_out_dim + 1
        interaction_dim = (4 * encoder_out_dim) + 1 + dense_feat_dim

        self.classifier = nn.Sequential(
            nn.Linear(interaction_dim, 128),
            nn.BatchNorm1d(128),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(64, num_classes)
        )

    def _encode(self, tokens: torch.Tensor) -> torch.Tensor:
        # tokens: (batch, seq_len)
        embeds = self.embedding(tokens)  # (batch, seq_len, embed_dim)
        lstm_out, _ = self.lstm(embeds)  # (batch, seq_len, 2*hidden_dim)

        # Max pooling over time dimension
        mask = (tokens != 0).unsqueeze(-1)  # (batch, seq_len, 1)
        lstm_out_masked = lstm_out.masked_fill(~mask, -1e9)
        pooled = torch.max(lstm_out_masked, dim=1)[0]  # (batch, 2*hidden_dim)
        return pooled

    def forward(
        self,
        resume_tokens: torch.Tensor,
        job_tokens: torch.Tensor,
        dense_feats: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        u = self._encode(resume_tokens)
        v = self._encode(job_tokens)

        diff = torch.abs(u - v)
        prod = u * v
        cos = F.cosine_similarity(u, v, dim=-1, eps=1e-8).unsqueeze(-1)

        fused = torch.cat([u, v, diff, prod, cos, dense_feats], dim=-1)
        return self.classifier(fused)


class TextCNNPairClassifier(nn.Module):
    """
    Model C: Parallel Multi-Scale Convolutional Pair Classifier.
    Extracts n-gram phrase patterns via kernel sizes [2, 3, 5], applies 1D adaptive
    max-pooling, computes pair alignment, and predicts compatibility.
    """

    def __init__(
        self,
        vocab_size: int,
        embed_dim: int = 100,
        num_filters: int = 64,
        kernel_sizes: list = [2, 3, 5],
        dense_feat_dim: int = 28,
        num_classes: int = 3,
        dropout_rate: float = 0.3
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(in_channels=embed_dim, out_channels=num_filters, kernel_size=k, padding=k // 2)
            for k in kernel_sizes
        ])

        total_filters = num_filters * len(kernel_sizes)
        interaction_dim = (4 * total_filters) + 1 + dense_feat_dim

        self.classifier = nn.Sequential(
            nn.Linear(interaction_dim, 128),
            nn.BatchNorm1d(128),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(64, num_classes)
        )

    def _encode(self, tokens: torch.Tensor) -> torch.Tensor:
        # tokens: (batch, seq_len)
        embeds = self.embedding(tokens).transpose(1, 2)  # (batch, embed_dim, seq_len)
        conv_outs = []
        for conv in self.convs:
            c = F.relu(conv(embeds))  # (batch, num_filters, seq_len)
            p = F.adaptive_max_pool1d(c, 1).squeeze(-1)  # (batch, num_filters)
            conv_outs.append(p)
        return torch.cat(conv_outs, dim=-1)

    def forward(
        self,
        resume_tokens: torch.Tensor,
        job_tokens: torch.Tensor,
        dense_feats: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        u = self._encode(resume_tokens)
        v = self._encode(job_tokens)

        diff = torch.abs(u - v)
        prod = u * v
        cos = F.cosine_similarity(u, v, dim=-1, eps=1e-8).unsqueeze(-1)

        fused = torch.cat([u, v, diff, prod, cos, dense_feats], dim=-1)
        return self.classifier(fused)


class CompactCrossAttention(nn.Module):
    """
    Model D: Supervised Cross-Attention Alignment Network.
    Job requirements act as queries attending over candidate resume tokens (keys/values).
    """

    def __init__(
        self,
        vocab_size: int,
        embed_dim: int = 96,
        num_heads: int = 4,
        dense_feat_dim: int = 28,
        num_classes: int = 3,
        dropout_rate: float = 0.3
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.cross_attn = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=dropout_rate,
            batch_first=True
        )
        self.norm = nn.LayerNorm(embed_dim)

        fused_dim = (2 * embed_dim) + dense_feat_dim
        self.classifier = nn.Sequential(
            nn.Linear(fused_dim, 128),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(128, num_classes)
        )

    def forward(
        self,
        resume_tokens: torch.Tensor,
        job_tokens: torch.Tensor,
        dense_feats: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        r_embed = self.embedding(resume_tokens)  # (batch, seq_len_r, embed_dim)
        j_embed = self.embedding(job_tokens)     # (batch, seq_len_j, embed_dim)

        # Job queries attend over resume keys & values
        attn_out, _ = self.cross_attn(query=j_embed, key=r_embed, value=r_embed)
        attended_j = self.norm(j_embed + attn_out)

        # Global average pooling
        r_pool = torch.mean(r_embed, dim=1)
        j_pool = torch.mean(attended_j, dim=1)

        fused = torch.cat([r_pool, j_pool, dense_feats], dim=-1)
        return self.classifier(fused)
