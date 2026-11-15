"""
src/services/challenger_service.py
Service adapter for Model 5 (Semantic & Skill Fusion Challenger):
- Provides high-throughput cached inference for candidate-job matching.
- ZERO PyTorch / SentenceTransformer execution in the web serving process.
- Instantly returns cached predictions (< 50ms) when both embeddings exist.
- Non-blocking cache-miss handling: delegates to background worker queue.
- Explicit fallback telemetry: tracks requested model, actual model, and fallback reasons.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import numpy as np

from experiments.phase14.src.inference_engine import OptimizedInferenceEngine
from src.services.embedding_service import get_embedding_service, EmbeddingService

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHALLENGER_PATH = REPO_ROOT / "models" / "phase13" / "semantic_skill_fusion_challenger.joblib"
DEFAULT_CACHE_DB = REPO_ROOT / "data" / "cache" / "embedding_cache.sqlite"


class ChallengerMatchingService:
    """
    High-level service wrapping Model 5 cached inference for the Flask application.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        cache_db_path: Optional[Union[str, Path]] = None
    ):
        self.model_path = Path(model_path or DEFAULT_CHALLENGER_PATH)
        self.cache_db_path = Path(cache_db_path or DEFAULT_CACHE_DB)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine: Optional[OptimizedInferenceEngine] = None
        self.embedding_service: EmbeddingService = get_embedding_service(cache_db_path=self.cache_db_path)
        self._init_engine()

    def _init_engine(self):
        try:
            # We initialize OptimizedInferenceEngine with lazy_load_encoder=False or without encoder
            # to guarantee that sentence_transformers is never imported in the serving process
            self._engine = OptimizedInferenceEngine(
                model_checkpoint_path=self.model_path,
                cache_db_path=self.cache_db_path,
                lazy_load_encoder=True  # encoder will not be loaded because we bypass it
            )
            logger.info("ChallengerMatchingService initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize ChallengerMatchingService: %s", e)
            self._engine = None

    def is_available(self) -> bool:
        return self._engine is not None and self.model_path.exists()

    def predict_match(
        self,
        resume_text: str,
        job_description_text: str
    ) -> Dict[str, Any]:
        """
        Executes Model 5 cached inference without blocking.
        If embeddings are present in cache: executes feature fusion in < 50ms.
        If cache miss occurs: enqueues jobs in persistent queue and returns pending status.
        """
        t0 = time.perf_counter()

        if self._engine is None:
            self._init_engine()
            if self._engine is None:
                return {
                    "status": "error",
                    "model_requested": "challenger_m5",
                    "model_used": None,
                    "fallback_triggered": True,
                    "fallback_reason": "challenger_engine_unavailable",
                    "is_challenger": False,
                    "latency_ms": (time.perf_counter() - t0) * 1000.0
                }

        # Check cache for both embeddings via EmbeddingService (no torch import)
        r_cached = self.embedding_service.cache.get(resume_text, entity_type="resume")
        j_cached = self.embedding_service.cache.get(job_description_text, entity_type="job")

        r_hit = (r_cached is not None)
        j_hit = (j_cached is not None)

        if not (r_hit and j_hit):
            # Cache miss on one or both: Enqueue for background worker without blocking web request
            r_job_id = None
            j_job_id = None
            if not r_hit:
                r_job_id = self.embedding_service.queue.enqueue(resume_text, entity_type="resume")
            if not j_hit:
                j_job_id = self.embedding_service.queue.enqueue(job_description_text, entity_type="job")

            latency_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "status": "cache_miss_pending",
                "model_requested": "challenger_m5",
                "model_used": None,
                "fallback_triggered": True,
                "fallback_reason": "cache_miss_pending_worker_generation",
                "is_challenger": False,
                "cache_status": {
                    "resume_hit": r_hit,
                    "job_hit": j_hit
                },
                "job_ids": {
                    "resume_job_id": r_job_id,
                    "job_job_id": j_job_id
                },
                "latency_ms": latency_ms
            }

        # Cache Hit on both: execute fusion features and classifier head
        u = r_cached[0]
        v = j_cached[0]

        # Extract domain features
        r_prof = self._engine.profile_extractor.extract_resume_profile(resume_text)
        j_prof = self._engine.profile_extractor.extract_job_profile(job_description_text)
        d_feats = self._engine.profile_extractor.combine_profiles(r_prof, j_prof)

        # Build 1565-dim fusion vector and apply scalers
        X = self._engine.build_fusion_features(u, v, d_feats)

        # Classifier forward pass
        probs_arr = self._engine.classifier.predict_proba(X)[0]
        pred_idx = int(np.argmax(probs_arr))
        classes_list = list(self._engine.clf_classes)
        pred_class = classes_list[pred_idx]

        probs = {
            cls_name: float(probs_arr[i])
            for i, cls_name in enumerate(classes_list)
        }

        p_good = probs.get("Good Fit", 0.0)
        p_pot = probs.get("Potential Fit", 0.0)
        compat_score = round(p_good * 100.0 + p_pot * 50.0, 1)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "status": "success",
            "model_requested": "challenger_m5",
            "model_used": "challenger_m5",
            "fallback_triggered": False,
            "fallback_reason": None,
            "is_challenger": True,
            "predicted_class": pred_class,
            "probabilities": probs,
            "confidence": float(probs_arr[pred_idx]),
            "compatibility_score": compat_score,
            "cache_status": {"resume_hit": True, "job_hit": True},
            "latency_ms": latency_ms,
            "model_identifier": "challenger_model_5_semantic_skill_fusion",
            "is_experimental": True,
            "calibration_status": "uncalibrated_softmax_cross_entropy"
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.embedding_service.get_stats()


# Singleton instance
_GLOBAL_CHALLENGER_SERVICE: Optional[ChallengerMatchingService] = None

def get_challenger_service(
    model_path: Optional[Union[str, Path]] = None,
    cache_db_path: Optional[Union[str, Path]] = None
) -> ChallengerMatchingService:
    global _GLOBAL_CHALLENGER_SERVICE
    if _GLOBAL_CHALLENGER_SERVICE is None:
        _GLOBAL_CHALLENGER_SERVICE = ChallengerMatchingService(
            model_path=model_path,
            cache_db_path=cache_db_path
        )
    return _GLOBAL_CHALLENGER_SERVICE
