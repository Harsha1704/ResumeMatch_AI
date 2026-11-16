"""
Master Resume Matching & Skill Gap Analysis Engine.
Integrates:
- Document Parsing (PDF, DOCX, TXT)
- Job Description Analysis (REQUIRED, PREFERRED, UNSPECIFIED tiers)
- Supervised ML Compatibility Prediction (Logistic Regression)
- Skill Gap & Partial Evidence Categorization with Strict Mathematical Accounting
- Experience & Structured Project Alignment
- Resume Improvement Recommendations & Verified Learning Resources
Zero LLM reliance. Fully deterministic.
"""

from typing import Dict, List, Optional, Union
import logging
import uuid
import re

logger = logging.getLogger(__name__)

from src.analysis.resume_parser import parse_resume
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.analysis.skill_gap import SkillGapAnalyzer
from src.analysis.experience_analyzer import ExperienceAnalyzer
from src.analysis.recommendation_engine import RecommendationEngine
from src.models.inference import get_inference_engine, CLASSES
from src.services.challenger_service import get_challenger_service
from src.common.evidence_registry import build_unified_evidence_registry


class ResumeMatchingEngine:
    """
    Unified end-to-end matching and skill gap engine.
    Supports both stable Production Baseline and experimental Challenger Model 5.
    """

    def __init__(self):
        self.job_analyzer = JobDescriptionAnalyzer()
        self.gap_analyzer = SkillGapAnalyzer()
        self.exp_analyzer = ExperienceAnalyzer()
        self.rec_engine = RecommendationEngine()
        self._inference_engine = None
        self._challenger_service = None

    @property
    def inference_engine(self):
        if self._inference_engine is None:
            self._inference_engine = get_inference_engine()
        return self._inference_engine

    @property
    def challenger_service(self):
        if self._challenger_service is None:
            self._challenger_service = get_challenger_service()
        return self._challenger_service

    def analyze(
        self,
        resume_input: Union[str, bytes],
        job_description_input: str,
        resume_filename: Optional[str] = None,
        model_backend: Optional[str] = None,
        target_role_input: Optional[str] = None
    ) -> Dict:
        """
        Runs the full analysis pipeline on a resume and job description.
        Returns a complete, structured, JSON-serializable dictionary.
        """
        analysis_id = str(uuid.uuid4())
        warnings: List[str] = []

        # 1. Parse Resume
        if isinstance(resume_input, bytes):
            parsed_resume = parse_resume(resume_input, filename=resume_filename)
        else:
            parsed_resume = parse_resume(resume_input.encode("utf-8"), filename=resume_filename or "resume.txt")

        if parsed_resume["status"] != "success":
            return {
                "analysis_id": analysis_id,
                "status": parsed_resume["status"],
                "error_message": parsed_resume["error_message"],
                "warnings": parsed_resume.get("warnings", []),
                "predicted_class": "No Fit",
                "class_probabilities": {c: 0.0 for c in CLASSES},
                "model_confidence": 0.0,
                "compatibility_score": 0.0,
                "skill_coverage": 0.0,
                "skill_coverage_pct": 0.0,
                "full_coverage_pct": 0.0,
                "any_coverage_pct": 0.0,
                "full_coverage_display": "Not Available",
                "any_coverage_display": "Not Available",
                "skill_coverage_display": "Not Available",
                "fully_matched_coverage_pct": 0.0,
                "skill_evidence_coverage_pct": 0.0,
                "skill_gap_summary": {
                    "total_required_count": 0,
                    "fully_matched_required_count": 0,
                    "partially_evidenced_required_count": 0,
                    "matched_required_count": 0,
                    "missing_required_count": 0,
                    "total_preferred_count": 0,
                    "matched_preferred_count": 0,
                    "missing_preferred_count": 0,
                    "full_coverage_pct": 0.0,
                    "any_coverage_pct": 0.0,
                    "full_coverage_display": "Not Available",
                    "any_coverage_display": "Not Available",
                    "skill_coverage_pct": None,
                    "skill_coverage_display": "Not Available"
                },
                "matched_skills": [],
                "missing_skills": [],
                "partially_evidenced_skills": [],
                "required_skills": [],
                "preferred_skills": [],
                "resume_skills": [],
                "projects": [],
                "relevant_projects": [],
                "internships": [],
                "professional_experience": [],
                "experience_summary": {
                    "has_full_time": False,
                    "full_time_years": 0.0,
                    "has_internships": False,
                    "internships_count": 0,
                    "has_projects": False,
                    "projects_count": 0,
                    "primary_classification": "Experience not established",
                    "display_summary": "Professional experience not established"
                },
                "experience_analysis": {},
                "education_analysis": {},
                "recommendations": [],
                "learning_resources": []
            }

        warnings.extend(parsed_resume.get("warnings", []))
        resume_raw_text = parsed_resume["raw_text"]

        # 2. Analyze Job Description
        job_res = self.job_analyzer.analyze(job_description_input)
        if job_res["status"] != "success":
            return {
                "analysis_id": analysis_id,
                "status": "error",
                "error_message": "Job description input was empty or invalid.",
                "warnings": warnings,
                "predicted_class": "No Fit"
            }

        detected_job_title = job_res["job_title"]
        target_role = ""
        if isinstance(target_role_input, str):
            target_role = re.sub(r"\s+", " ", target_role_input).strip()
            target_role = re.sub(r"[\x00-\x1f\x7f]", "", target_role)[:120].strip()
        job_title = target_role or detected_job_title
        job_required_skills = job_res["required_skills"]
        job_preferred_skills = job_res["preferred_skills"]
        job_unspecified_skills = job_res.get("unspecified_skills", [])
        job_exp_years = job_res["required_years_exp"]

        # 3. Supervised Machine Learning Compatibility Prediction
        is_challenger = False
        inference_latency_ms = 0.0
        cache_status = None
        model_requested = model_backend or "production"
        fallback_triggered = False
        fallback_reason = None
        pending_jobs = None

        if model_backend == "challenger_m5":
            try:
                c_pred = self.challenger_service.predict_match(resume_raw_text, job_description_input)
                if c_pred.get("status") == "cache_miss_pending":
                    # Non-blocking miss: background worker queued
                    fallback_triggered = True
                    fallback_reason = c_pred.get("fallback_reason", "cache_miss_pending_worker_generation")
                    pending_jobs = c_pred.get("job_ids")
                    logger.info("Challenger cache miss. Jobs queued: %s. Serving Production Baseline fallback.", pending_jobs)
                    warnings.append("Neural embeddings are queued for background generation. Temporary analysis computed via Production Baseline.")
                    ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
                    predicted_class = ml_prediction["predicted_class"]
                    class_probabilities = ml_prediction["probabilities"]
                    model_confidence = ml_prediction["confidence"]
                    compatibility_score = ml_prediction["compatibility_score"]
                    model_used = "Production Baseline (Fallback: Embeddings Queued for Background Worker)"
                    model_backend_applied = "production_fallback"
                    inference_latency_ms = c_pred.get("latency_ms", 0.0)
                    cache_status = c_pred.get("cache_status", {})
                    is_challenger = False
                    calibration_note = "Production Baseline: Calibrated probabilities while neural embeddings generate in background."
                elif c_pred.get("status") == "error":
                    fallback_triggered = True
                    fallback_reason = c_pred.get("fallback_reason", "challenger_error")
                    logger.error("Challenger error: %s. Falling back to Production Baseline.", fallback_reason)
                    warnings.append(f"Challenger Model 5 encountered an issue ({fallback_reason}); safely reverted to Production Baseline.")
                    ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
                    predicted_class = ml_prediction["predicted_class"]
                    class_probabilities = ml_prediction["probabilities"]
                    model_confidence = ml_prediction["confidence"]
                    compatibility_score = ml_prediction["compatibility_score"]
                    model_used = "Production Baseline (Fallback from Challenger Error)"
                    model_backend_applied = "production_fallback"
                    is_challenger = False
                    calibration_note = "Production Model: Calibrated probabilities based on TF-IDF baseline."
                else:
                    predicted_class = c_pred["predicted_class"]
                    class_probabilities = c_pred["probabilities"]
                    model_confidence = c_pred["confidence"]
                    compatibility_score = c_pred["compatibility_score"]
                    model_used = "Challenger Model 5 (Semantic & Skill Fusion - Experimental)"
                    model_backend_applied = "challenger_m5"
                    inference_latency_ms = c_pred.get("latency_ms", 0.0)
                    cache_status = c_pred.get("cache_status", {})
                    is_challenger = True
                    calibration_note = "Experimental Model Notice: Probabilities reflect softmax cross-entropy output from the multi-modal fusion challenger. Calibration refinement is active."
            except Exception as e:
                fallback_triggered = True
                fallback_reason = f"challenger_exception: {type(e).__name__} - {str(e)[:80]}"
                logger.error("Challenger Model 5 unexpected exception, falling back to Production Baseline: %s", e)
                warnings.append(f"Challenger Model 5 encountered an exception ({str(e)[:60]}); safely reverted to Production Baseline.")
                ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
                predicted_class = ml_prediction["predicted_class"]
                class_probabilities = ml_prediction["probabilities"]
                model_confidence = ml_prediction["confidence"]
                compatibility_score = ml_prediction["compatibility_score"]
                model_used = "Production Baseline (Fallback from Challenger Error)"
                model_backend_applied = "production_fallback"
                is_challenger = False
                calibration_note = "Production Model: Calibrated probabilities based on TF-IDF baseline."
        else:
            ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
            predicted_class = ml_prediction["predicted_class"]
            class_probabilities = ml_prediction["probabilities"]
            model_confidence = ml_prediction["confidence"]
            compatibility_score = ml_prediction["compatibility_score"]
            model_used = "Production Baseline (TF-IDF + Logistic Regression)"
            model_backend_applied = "production"
            calibration_note = "Production Model: Calibrated probabilities based on TF-IDF baseline."

        # 4. Comparative Skill Gap Analysis
        gap_res = self.gap_analyzer.analyze_gap(
            resume_raw_text,
            job_res,
            job_raw_text=job_description_input
        )

        # Clean and sanitize skill lists (filter out any empty, whitespace-only, or None values)
        def _clean_skills(skill_list: List[str], tier_name: str) -> List[str]:
            cleaned = []
            for s in skill_list:
                if s and isinstance(s, str) and s.strip():
                    cleaned.append(s.strip())
                else:
                    logger.warning("Omitted empty %s skill badge: %r", tier_name, s)
            return cleaned

        matched_skills = _clean_skills(gap_res["matched_skills"], "matched")
        matched_required = _clean_skills(gap_res["matched_required_skills"], "matched_required")
        fully_matched_required = _clean_skills(gap_res["fully_matched_required_skills"], "fully_matched_required")
        partially_evidenced_required = _clean_skills(gap_res["partially_evidenced_required_skills"], "partially_evidenced_required")
        missing_required = _clean_skills(gap_res["missing_required_skills"], "missing_required")
        matched_preferred = _clean_skills(gap_res["matched_preferred_skills"], "matched_preferred")
        missing_preferred = _clean_skills(gap_res["missing_preferred_skills"], "missing_preferred")
        missing_all = missing_required + [s for s in missing_preferred if s not in missing_required]

        # 5. Experience Alignment & Project Evidence
        exp_res = self.exp_analyzer.analyze_experience(resume_raw_text, job_required_years=job_exp_years)
        relevant_projects = exp_res["detected_projects"]

        # 6. Improvement Recommendations & Verified Learning Resources
        recommendations = self.rec_engine.generate_recommendations(
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            partially_evidenced=partially_evidenced_required,
            experience_analysis=exp_res,
            job_title=job_title
        )
        learning_resources = self.rec_engine.get_learning_resources(missing_all)

        # 7. Unified Skill Gap Accounting Summary (Two clearly separated coverage calculations)
        full_cov_pct = gap_res.get("full_coverage_pct", 0.0)
        any_cov_pct = gap_res.get("any_coverage_pct", 0.0)
        full_cov_disp = gap_res.get("full_coverage_display", f"{full_cov_pct}%")
        any_cov_disp = gap_res.get("any_coverage_display", f"{any_cov_pct}%")

        skill_gap_summary = {
            "total_required_count": gap_res["total_required_count"],
            "fully_matched_required_count": gap_res["fully_matched_required_count"],
            "partially_evidenced_required_count": gap_res["partially_evidenced_required_count"],
            "matched_required_count": gap_res["matched_required_count"],
            "missing_required_count": gap_res["missing_required_count"],
            "total_preferred_count": gap_res["total_preferred_count"],
            "matched_preferred_count": gap_res["matched_preferred_count"],
            "missing_preferred_count": gap_res["missing_preferred_count"],
            "total_resume_skills_count": gap_res.get("total_resume_skills_count", 0),
            "full_coverage_pct": full_cov_pct,
            "any_coverage_pct": any_cov_pct,
            "full_coverage_display": full_cov_disp,
            "any_coverage_display": any_cov_disp,
            "skill_coverage_pct": any_cov_pct,
            "fully_matched_coverage_pct": full_cov_pct,
            "skill_evidence_coverage_pct": any_cov_pct,
            "skill_coverage_display": full_cov_disp
        }

        # Education verification
        lower_res_text = parsed_resume["cleaned_text"].lower()
        degree_tokens = ["bachelor", "master", "b.tech", "m.tech", "b.e", "m.e", "b.s", "m.s", "phd", "degree", "diploma", "btech", "mtech", "b.sc", "m.sc"]
        has_degree_mention = any(re.search(rf"\b{re.escape(tok)}\b", lower_res_text) for tok in degree_tokens)
        edu_notes = "Verified against degree mentions in parsed resume." if has_degree_mention else "Education details not confidently identified"

        from src.common.evidence_registry import build_unified_evidence_registry

        # 8. Assemble Complete Result
        result_payload = {
            "analysis_id": analysis_id,
            "status": "success",
            "filename": parsed_resume["filename"],
            "raw_text": resume_raw_text,
            "resume_raw_text": resume_raw_text,
            "cleaned_resume_text": parsed_resume.get("cleaned_text", ""),
            "job_title": job_title,
            "target_role": job_title,
            "detected_job_title": detected_job_title,
            "target_role_source": "user_override" if target_role else "job_description",
            "job_description_text": str(job_description_input),
            "raw_jd": str(job_description_input),
            "predicted_class": predicted_class,
            "class_probabilities": class_probabilities,
            "model_confidence": model_confidence,
            "compatibility_score": compatibility_score,
            "skill_coverage": any_cov_pct,
            "skill_coverage_pct": any_cov_pct,
            "full_coverage_pct": full_cov_pct,
            "any_coverage_pct": any_cov_pct,
            "skill_coverage_display": full_cov_disp,
            "full_coverage_display": full_cov_disp,
            "any_coverage_display": any_cov_disp,
            "fully_matched_coverage_pct": full_cov_pct,
            "skill_evidence_coverage_pct": any_cov_pct,
            "skill_gap_summary": skill_gap_summary,
            "matched_skills": matched_skills,
            "matched_required_skills": matched_required,
            "fully_matched_required_skills": fully_matched_required,
            "partially_evidenced_required_skills": partially_evidenced_required,
            "missing_skills": missing_all,
            "missing_required_skills": missing_required,
            "matched_preferred_skills": matched_preferred,
            "missing_preferred_skills": missing_preferred,
            "satisfied_alternatives": gap_res.get("satisfied_alternatives", []),
            "alternative_groups": job_res.get("alternative_groups", []),
            "partially_evidenced_skills": gap_res["partially_evidenced_skills"],
            "solidly_evidenced_skills": gap_res["solidly_evidenced_skills"],
            "required_skills": gap_res.get("effective_required_skills", job_required_skills),
            "preferred_skills": gap_res.get("effective_preferred_skills", job_preferred_skills),
            "unspecified_skills": job_unspecified_skills,
            "requirement_intelligence": job_res.get("requirement_intelligence", []),
            "resume_skills": gap_res["resume_skills"],
            "projects": relevant_projects,
            "relevant_projects": relevant_projects,
            "internships": exp_res.get("internships", []),
            "professional_experience": exp_res.get("professional_experience", []),
            "experience_summary": exp_res.get("experience_summary", {}),
            "experience_analysis": exp_res,
            "education_analysis": {
                "detected_job_requirements": job_res["education_requirements"],
                "notes": edu_notes
            },
            "prioritized_gaps": gap_res["prioritized_gaps"],
            "recommendations": recommendations,
            "learning_resources": learning_resources,
            "has_missing_skills": bool(missing_all),
            "structural_metadata": parsed_resume["structural_features"],
            "model_requested": model_requested,
            "model_used": model_used,
            "model_backend": model_backend_applied,
            "fallback_triggered": fallback_triggered,
            "fallback_reason": fallback_reason,
            "pending_jobs": pending_jobs,
            "is_challenger": is_challenger,
            "inference_latency_ms": inference_latency_ms,
            "cache_status": cache_status,
            "calibration_note": calibration_note,
            "warnings": warnings
        }

        # Build unified evidence registry
        evidence_reg = build_unified_evidence_registry(result_payload)
        result_payload["evidence_registry"] = evidence_reg.build_summary_dossier()

        return result_payload


# Global singleton instance
_default_matching_engine: Optional[ResumeMatchingEngine] = None


def get_matching_engine() -> ResumeMatchingEngine:
    global _default_matching_engine
    if _default_matching_engine is None:
        _default_matching_engine = ResumeMatchingEngine()
    return _default_matching_engine


def analyze_resume_and_job(
    resume_input: Union[str, bytes],
    job_description_input: str,
    resume_filename: Optional[str] = None,
    model_backend: Optional[str] = None,
    target_role_input: Optional[str] = None
) -> Dict:
    return get_matching_engine().analyze(
        resume_input,
        job_description_input,
        resume_filename=resume_filename,
        model_backend=model_backend,
        target_role_input=target_role_input
    )
