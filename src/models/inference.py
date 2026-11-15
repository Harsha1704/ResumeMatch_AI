"""
Inference Engine for Multimodal Resume-Job Compatibility Matching.
Uses serialized trained models and preprocessing pipelines without LLMs.
Provides transparent predictions, calibrated probabilities, and skill gap insights.
"""

from pathlib import Path
import pathlib
from typing import Dict, List, Optional, Tuple, Union
import json
import joblib
import numpy as np
import pandas as pd

from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine
from src.features.feature_pipeline import ResumeJobFeaturePipeline


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "best_model.joblib"
DEFAULT_PIPELINE_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "feature_pipeline.joblib"
DEFAULT_LABEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "label_mapping.json"

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]


class ModelInferenceEngine:
    """
    Singleton-friendly inference manager for model predictions and explainable matching.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        pipeline_path: Optional[Union[str, Path]] = None
    ):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.pipeline_path = Path(pipeline_path) if pipeline_path else DEFAULT_PIPELINE_PATH
        self.model = None
        self.pipeline: Optional[ResumeJobFeaturePipeline] = None
        self.classes: List[str] = CLASSES
        self.skill_engine = SkillEngine()
        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Loads serialized artifacts, including Windows-trained paths, on Linux.

        Joblib artifacts created on Windows can contain pathlib.WindowsPath objects.
        Linux refuses to instantiate those during unpickling, so temporarily map the
        pickle reference to PosixPath while loading. Restore the standard pathlib
        class immediately afterward.
        """
        original_windows_path = pathlib.WindowsPath
        try:
            pathlib.WindowsPath = pathlib.PosixPath
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
            if self.pipeline_path.exists():
                self.pipeline = ResumeJobFeaturePipeline.load(self.pipeline_path)
        finally:
            pathlib.WindowsPath = original_windows_path

    def predict_match(
        self,
        resume_text: Optional[str],
        job_text: Optional[str]
    ) -> Dict:
        """
        Predicts compatibility fit for a single resume-job pair.
        Returns prediction, class probabilities, compatibility score, and skill analysis.
        """
        # Handle empty/invalid inputs gracefully
        if not resume_text or not str(resume_text).strip() or not job_text or not str(job_text).strip():
            return {
                "predicted_class": "No Fit",
                "confidence": 0.0,
                "compatibility_score": 0.0,
                "probabilities": {c: 0.0 for c in self.classes},
                "skill_analysis": {
                    "matched_skills": [],
                    "missing_skills": [],
                    "job_coverage_ratio": 0.0,
                    "jaccard_similarity": 0.0
                },
                "experience_evidence": {
                    "resume_years_exp": 0.0,
                    "job_years_exp": 0.0,
                    "exp_difference": 0.0,
                    "meets_requirement": False
                },
                "status": "invalid_input",
                "message": "Both resume text and job description must be provided."
            }

        if self.model is None or self.pipeline is None:
            self._load_artifacts()
            if self.model is None or self.pipeline is None:
                raise RuntimeError("Model or Feature Pipeline artifacts not found on disk. Run training first.")

        # Transform features
        pair_df = pd.DataFrame([{
            "resume_text": str(resume_text),
            "job_description_text": str(job_text)
        }])
        X_feat = self.pipeline.transform(pair_df)

        # Predict class
        pred_raw = self.model.predict(X_feat)[0]
        pred_class = str(pred_raw)

        # Calibrated/model probabilities
        if hasattr(self.model, "predict_proba"):
            probs_arr = self.model.predict_proba(X_feat)[0]
            # Ensure ordering matches self.classes
            if hasattr(self.model, "classes_"):
                model_cls = list(self.model.classes_)
                prob_dict = {c: float(round(probs_arr[model_cls.index(c)], 4)) if c in model_cls else 0.0 for c in self.classes}
            else:
                prob_dict = {c: float(round(probs_arr[i], 4)) for i, c in enumerate(self.classes)}
            confidence = float(round(max(probs_arr), 4))
        else:
            confidence = 1.0
            prob_dict = {c: (1.0 if c == pred_class else 0.0) for c in self.classes}

        # Transparent compatibility score:
        # Derived strictly from model class probabilities without random numbers
        # Good Fit weight = 100%, Potential Fit weight = 50%, No Fit weight = 0%
        good_p = prob_dict.get("Good Fit", 0.0)
        pot_p = prob_dict.get("Potential Fit", 0.0)
        compat_score = round((good_p * 100.0) + (pot_p * 50.0), 1)

        # Extract domain skill and experience evidence
        skill_gap = self.skill_engine.analyze_skill_gap(resume_text, job_text)
        r_struct = parse_structural_features(resume_text)
        j_struct = parse_structural_features(job_text)

        r_exp = r_struct["explicit_years_exp"]
        j_exp = j_struct["explicit_years_exp"]

        return {
            "predicted_class": pred_class,
            "confidence": confidence,
            "compatibility_score": compat_score,
            "probabilities": prob_dict,
            "skill_analysis": skill_gap,
            "experience_evidence": {
                "resume_years_exp": r_exp,
                "job_years_exp": j_exp,
                "exp_difference": round(r_exp - j_exp, 1),
                "meets_requirement": bool(r_exp >= j_exp if j_exp > 0 else True)
            },
            "status": "success",
            "message": "Analysis completed successfully."
        }

    def predict_match_batch(
        self,
        resumes: List[str],
        jobs: List[str]
    ) -> List[Dict]:
        """Runs predictions over a batch of resume-job pairs."""
        return [self.predict_match(r, j) for r, j in zip(resumes, jobs)]


# Global helper functions for modular access
_default_engine: Optional[ModelInferenceEngine] = None


def get_inference_engine() -> ModelInferenceEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = ModelInferenceEngine()
    return _default_engine


def load_model(model_path: Optional[Union[str, Path]] = None):
    return get_inference_engine().model


def load_feature_pipeline(pipeline_path: Optional[Union[str, Path]] = None):
    return get_inference_engine().pipeline


def predict_match(resume_text: Optional[str], job_text: Optional[str]) -> Dict:
    return get_inference_engine().predict_match(resume_text, job_text)


def predict_match_batch(resumes: List[str], jobs: List[str]) -> List[Dict]:
    return get_inference_engine().predict_match_batch(resumes, jobs)
