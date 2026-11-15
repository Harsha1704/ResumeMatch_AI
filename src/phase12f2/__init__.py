"""
src/phase12f2/__init__.py
Phase 12F.2 Leakage-Proof Learning Architecture & Dual-Unseen Generalization Recovery Package.
"""
from src.phase12f2.split_guard import (
    ProtocolSplitGuard,
    load_guarded_dual_unseen_splits,
    load_guarded_job_disjoint_splits,
    PROTOCOL_DUAL_UNSEEN,
    PROTOCOL_JOB_DISJOINT,
)

__all__ = [
    "ProtocolSplitGuard",
    "load_guarded_dual_unseen_splits",
    "load_guarded_job_disjoint_splits",
    "PROTOCOL_DUAL_UNSEEN",
    "PROTOCOL_JOB_DISJOINT",
]
