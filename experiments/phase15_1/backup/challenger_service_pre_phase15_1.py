"""
src/services/challenger_service.py
Service adapter for Model 5 (Semantic & Skill Fusion Challenger):
- Provides unified access to Phase 14 OptimizedInferenceEngine.
- Encapsulates error handling and diagnostic telemetry.
- Guarantees zero retrained weights or modified production checkpoints.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import numpy as np

from experiments.phase14.src.inference_engine import OptimizedInferenceEngine

logger = logging.getLogger(__name__)

REPO_ROOT = Path("D:/skillsync1")
DEFAULT_CHALLENGER_PATH = REPO_ROOT / "models" / "phase13" / "semantic_skill_fusion_challenger.joblib"
DEFAULT_CACHE_DB = REPO_ROOT / "data" / "cache" / "embedding_cache.sqlite"


class ChallengerMatchingService:
    """
    High-level service wrapping Model 5 cached inference for the Flask application.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        cache_db_path: Optional[Union[str, Path]] = None,
        lazy_load_encoder: bool = True
    ):
        self.model_path = Path(model_path or DEFAULT_CHALLENGER_PATH)
        self.cache_db_path = Path(cache_db_path or DEFAULT_CACHE_DB)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = None
        self.lazy_load_encoder = lazy_load_encoder
        self._init_engine()

    def _init_engine(self):
        try:
            self._engine = OptimizedInferenceEngine(
                model_checkpoint_path=self.model_path,
                cache_db_path=self.cache_db_path,
                lazy_load_encoder=self.lazy_load_encoder
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
        job_description_text: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Executes Model 5 cached inference.
        Returns prediction dictionary with probabilities, confidence, compatibility score, and cache telemetry.
        """
        if self._engine is None:
            self._init_engine()
            if self._engine is None:
                raise RuntimeError("ChallengerMatchingService engine is not available.")

        res = self._engine.predict(
            resume_text=resume_text,
            job_description_text=job_description_text,
            use_cache=use_cache
        )

        probs = res["probabilities"]
        p_good = probs.get("Good Fit", 0.0)
        p_pot = probs.get("Potential Fit", 0.0)
        # Compatibility score derived from Good Fit and Potential Fit proportions
        compat_score = round(p_good * 100.0 + p_pot * 50.0, 1)

        return {
            "predicted_class": res["predicted_class"],
            "probabilities": probs,
            "confidence": res["confidence"],
            "compatibility_score": compat_score,
            "cache_status": res.get("cache_status", {}),
            "latency_ms": res.get("latency_ms", 0.0),
            "model_identifier": "challenger_model_5_semantic_skill_fusion",
            "is_experimental": True,
            "calibration_status": "uncalibrated_softmax_cross_entropy"
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        if self._engine and self._engine.cache:
            return self._engine.cache.get_stats()
        return {}


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
