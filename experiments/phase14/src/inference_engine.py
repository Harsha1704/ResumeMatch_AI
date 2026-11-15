"""
experiments/phase14/src/inference_engine.py
Optimized cached-embedding inference pipeline for ResumeMatch AI Model 5:
- Retrieves cached embeddings (and optional profile metadata).
- Computes exact fusion features (1537 SBERT interaction features + 28 domain features = 1565 total features).
- Applies existing Model 5 scalers (scaler_sbert, scaler_dom).
- Executes existing Model 5 LogisticRegression classifier checkpoint.
- Returns canonical probabilities for No Fit, Potential Fit, and Good Fit.
- Ensures numerical equivalence with direct uncached SBERT inference.
"""

import sys
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List
import numpy as np
import pandas as pd
import joblib

REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

from experiments.phase14.src.embedding_cache import (
    PersistentEmbeddingCache,
    normalize_text_for_caching
)
from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import (
    SkillEngine,
    categorize_competency,
    TAXONOMY_PROGRAMMING_LANGUAGES,
    TAXONOMY_FRAMEWORKS_LIBRARIES,
    TAXONOMY_DATABASES,
    TAXONOMY_DEVELOPER_TOOLS,
    TAXONOMY_CLOUD_INFRASTRUCTURE,
    TAXONOMY_SOFT
)
from src.analysis.job_analyzer import REQUIRED_PATTERNS, PREFERRED_PATTERNS, EDUCATION_PATTERNS


class ProfileExtractor:
    """Extracts modular resume and job profile metadata for zero-redundancy feature combination."""
    def __init__(self, skill_engine: Optional[SkillEngine] = None):
        self.skill_engine = skill_engine or SkillEngine()

    def extract_resume_profile(self, resume_raw: str) -> Dict[str, Any]:
        r_clean = clean_text(resume_raw)
        r_skill_set = self.skill_engine.extract_skills(r_clean)
        r_struct = parse_structural_features(resume_raw)
        r_has_degree = 1.0 if any(re.search(p, resume_raw.lower()) for p in EDUCATION_PATTERNS) else 0.0
        return {
            "skills": sorted(list(r_skill_set)),
            "exp": float(r_struct["explicit_years_exp"]),
            "words": float(max(r_struct["word_count"], 1)),
            "sections": float(r_struct["section_count"]),
            "has_degree": r_has_degree
        }

    def extract_job_profile(self, job_raw: str) -> Dict[str, Any]:
        j_clean = clean_text(job_raw)
        j_skill_set = self.skill_engine.extract_skills(j_clean)
        j_lines = [l.strip() for l in job_raw.split("\n") if l.strip()]
        mandatory_skills = set()
        preferred_skills = set()
        for line in j_lines:
            lower_l = line.lower()
            is_req = any(re.search(p, lower_l) for p in REQUIRED_PATTERNS)
            is_pref = any(re.search(p, lower_l) for p in PREFERRED_PATTERNS)
            line_skills = self.skill_engine.extract_skills(clean_text(line))
            if is_req and not is_pref:
                mandatory_skills.update(line_skills)
            elif is_pref:
                preferred_skills.update(line_skills)
        j_struct = parse_structural_features(job_raw)
        j_has_degree_req = 1.0 if any(re.search(p, job_raw.lower()) for p in EDUCATION_PATTERNS) else 0.0
        return {
            "skills": sorted(list(j_skill_set)),
            "mandatory_skills": sorted(list(mandatory_skills)),
            "preferred_skills": sorted(list(preferred_skills)),
            "exp": float(j_struct["explicit_years_exp"]),
            "words": float(max(j_struct["word_count"], 1)),
            "has_degree_req": j_has_degree_req
        }

    @staticmethod
    def combine_profiles(r_prof: Dict[str, Any], j_prof: Dict[str, Any]) -> Dict[str, float]:
        r_skill_set = set(r_prof["skills"])
        j_skill_set = set(j_prof["skills"])
        matched_skills = r_skill_set.intersection(j_skill_set)
        missing_skills = j_skill_set.difference(r_skill_set)
        n_matched = len(matched_skills)
        n_missing = len(missing_skills)
        n_resume_skills = len(r_skill_set)
        n_job_skills = len(j_skill_set)

        jaccard = n_matched / len(r_skill_set.union(j_skill_set)) if (r_skill_set or j_skill_set) else 0.0
        coverage = n_matched / n_job_skills if n_job_skills > 0 else 1.0
        relevance = n_matched / n_resume_skills if n_resume_skills > 0 else 0.0

        mandatory_skills = set(j_prof["mandatory_skills"])
        preferred_skills = set(j_prof["preferred_skills"])
        n_mand_total = len(mandatory_skills)
        n_mand_matched = len(mandatory_skills.intersection(r_skill_set))
        mand_coverage = n_mand_matched / n_mand_total if n_mand_total > 0 else coverage

        n_pref_total = len(preferred_skills)
        n_pref_matched = len(preferred_skills.intersection(r_skill_set))
        pref_coverage = n_pref_matched / n_pref_total if n_pref_total > 0 else 1.0

        cat_counts = {"prog": 0, "fw": 0, "db": 0, "cloud": 0, "tool": 0, "soft": 0}
        for s in matched_skills:
            cat = categorize_competency(s)
            if cat == TAXONOMY_PROGRAMMING_LANGUAGES:
                cat_counts["prog"] += 1
            elif cat == TAXONOMY_FRAMEWORKS_LIBRARIES:
                cat_counts["fw"] += 1
            elif cat == TAXONOMY_DATABASES:
                cat_counts["db"] += 1
            elif cat == TAXONOMY_CLOUD_INFRASTRUCTURE:
                cat_counts["cloud"] += 1
            elif cat == TAXONOMY_DEVELOPER_TOOLS:
                cat_counts["tool"] += 1
            elif cat == TAXONOMY_SOFT:
                cat_counts["soft"] += 1

        r_exp = r_prof["exp"]
        j_exp = j_prof["exp"]
        exp_diff = r_exp - j_exp
        has_req_exp = 1.0 if (j_exp > 0 and r_exp >= j_exp) or (j_exp == 0.0 and r_exp > 0) else 0.0

        j_has_degree_req = j_prof["has_degree_req"]
        r_has_degree = r_prof["has_degree"]
        edu_match = 1.0 if (not j_has_degree_req or r_has_degree) else 0.0

        r_words = r_prof["words"]
        j_words = j_prof["words"]
        length_ratio = r_words / j_words
        r_sections = r_prof["sections"]

        return {
            "skill_jaccard": float(jaccard),
            "job_coverage": float(coverage),
            "resume_relevance": float(relevance),
            "matched_skill_count": float(n_matched),
            "missing_skill_count": float(n_missing),
            "resume_skill_count": float(n_resume_skills),
            "job_skill_count": float(n_job_skills),
            "mandatory_skill_coverage": float(mand_coverage),
            "mandatory_matched_count": float(n_mand_matched),
            "mandatory_missing_count": float(max(0, n_mand_total - n_mand_matched)),
            "preferred_skill_coverage": float(pref_coverage),
            "preferred_matched_count": float(n_pref_matched),
            "cat_prog_overlap": float(cat_counts["prog"]),
            "cat_fw_overlap": float(cat_counts["fw"]),
            "cat_db_overlap": float(cat_counts["db"]),
            "cat_cloud_overlap": float(cat_counts["cloud"]),
            "cat_tool_overlap": float(cat_counts["tool"]),
            "cat_soft_overlap": float(cat_counts["soft"]),
            "resume_years_exp": r_exp,
            "job_years_exp": j_exp,
            "exp_diff": exp_diff,
            "has_required_exp": has_req_exp,
            "job_has_degree_req": j_has_degree_req,
            "education_match": edu_match,
            "resume_word_count": r_words,
            "job_word_count": j_words,
            "length_ratio": float(length_ratio),
            "resume_section_count": r_sections
        }


class OptimizedInferenceEngine:
    """
    Production-grade cached-embedding inference engine for Model 5:
    - Lazy encoder loading to preserve RSS memory under pure cache hits.
    - Zero data leakage, strict model weight preservation.
    - Canonical class probability ordering: No Fit, Potential Fit, Good Fit.
    """

    CANONICAL_CLASSES = ["No Fit", "Potential Fit", "Good Fit"]

    def __init__(
        self,
        model_checkpoint_path: Union[str, Path] = "models/phase13/semantic_skill_fusion_challenger.joblib",
        cache_db_path: Union[str, Path] = "experiments/phase14/cache/embedding_cache.sqlite",
        encoder_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        encoder_version: str = "sentence-transformers/all-MiniLM-L6-v2:v1",
        lazy_load_encoder: bool = True
    ):
        self.model_path = Path(model_checkpoint_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model 5 checkpoint not found at: {self.model_path}")

        # Load Model 5 artifact components
        self.m5_obj = joblib.load(self.model_path)
        self.scaler_sbert = self.m5_obj["scaler_sbert"]
        self.scaler_dom = self.m5_obj["scaler_dom"]
        self.classifier = self.m5_obj["model"]
        self.domain_feature_names = self.m5_obj["domain_feature_names"]

        # Map internal classifier classes to canonical indices
        # self.classifier.classes_ is ['Good Fit', 'No Fit', 'Potential Fit']
        self.clf_classes = list(self.classifier.classes_)
        self.idx_good = self.clf_classes.index("Good Fit")
        self.idx_no = self.clf_classes.index("No Fit")
        self.idx_pot = self.clf_classes.index("Potential Fit")

        # Persistent Embedding Cache
        self.encoder_name = encoder_name
        self.encoder_version = encoder_version
        self.cache = PersistentEmbeddingCache(db_path=cache_db_path, encoder_version=encoder_version)

        # Profile Extractor for domain features
        self.profile_extractor = ProfileExtractor()

        # Lazy-loaded encoder
        self._encoder = None
        if not lazy_load_encoder:
            self._get_encoder()

    def _get_encoder(self):
        """Loads SentenceTransformer encoder on demand (lazy loading)."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.encoder_name)
        return self._encoder

    def _encode_text(self, text: str) -> np.ndarray:
        encoder = self._get_encoder()
        # Ensure single string input and normalized unit vectors
        emb = encoder.encode([text], normalize_embeddings=True)[0]
        return np.ascontiguousarray(emb, dtype=np.float32)

    def get_or_create_resume_embedding(self, resume_text: str) -> Tuple[np.ndarray, Dict[str, Any], bool]:
        """Retrieves or creates resume embedding and profile metadata."""
        def _encode(t):
            return self._encode_text(t)

        # Check cache first
        cached = self.cache.get(resume_text, entity_type="resume")
        if cached is not None and cached[1] is not None:
            return cached[0], cached[1], True

        # Compute profile metadata if missing or on miss
        r_prof = self.profile_extractor.extract_resume_profile(resume_text)
        emb, meta, hit = self.cache.get_or_encode(
            text=resume_text,
            encode_func=_encode,
            entity_type="resume",
            metadata=r_prof
        )
        return emb, r_prof, hit

    def get_or_create_job_embedding(self, job_text: str) -> Tuple[np.ndarray, Dict[str, Any], bool]:
        """Retrieves or creates job embedding and profile metadata."""
        def _encode(t):
            return self._encode_text(t)

        cached = self.cache.get(job_text, entity_type="job")
        if cached is not None and cached[1] is not None:
            return cached[0], cached[1], True

        j_prof = self.profile_extractor.extract_job_profile(job_text)
        emb, meta, hit = self.cache.get_or_encode(
            text=job_text,
            encode_func=_encode,
            entity_type="job",
            metadata=j_prof
        )
        return emb, j_prof, hit

    def build_fusion_features(
        self,
        u: np.ndarray,
        v: np.ndarray,
        domain_features_dict: Dict[str, float]
    ) -> np.ndarray:
        """
        Builds exact Model 5 fusion feature array:
        - SBERT interaction features: [u, v, u * v, |u - v|, cos(u, v)] (1537-dim)
        - Scaled by scaler_sbert
        - Domain features (28-dim) in exact domain_feature_names order
        - Scaled by scaler_dom
        - Concatenated into 1565-dim feature vector
        """
        # SBERT interaction vector
        cos_sim = float(np.dot(u, v))
        u_arr = np.asarray(u, dtype=np.float32)
        v_arr = np.asarray(v, dtype=np.float32)
        x_sbert = np.hstack([u_arr, v_arr, u_arr * v_arr, np.abs(u_arr - v_arr), [cos_sim]]).reshape(1, -1)

        # Domain vector
        dom_vals = [domain_features_dict[k] for k in self.domain_feature_names]
        x_dom = pd.DataFrame([dom_vals], columns=self.domain_feature_names)

        # Apply existing scalers
        x_sbert_sc = self.scaler_sbert.transform(x_sbert)
        x_dom_sc = self.scaler_dom.transform(x_dom)

        # Fusion concatenation
        return np.hstack([x_sbert_sc, x_dom_sc])

    def predict(
        self,
        resume_text: str,
        job_description_text: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Performs candidate-job matching inference.
        Returns:
            - probabilities: canonical dictionary {'No Fit': p_no, 'Potential Fit': p_pot, 'Good Fit': p_good}
            - predicted_class: string ('No Fit', 'Potential Fit', 'Good Fit')
            - confidence: float (max probability)
            - cache_status: dict {'resume_hit': bool, 'job_hit': bool}
            - latency_ms: float
        """
        t0 = time.perf_counter()

        if use_cache:
            u, r_prof, r_hit = self.get_or_create_resume_embedding(resume_text)
            v, j_prof, j_hit = self.get_or_create_job_embedding(job_description_text)
            d_feats = self.profile_extractor.combine_profiles(r_prof, j_prof)
        else:
            # Full uncached baseline path
            u = self._encode_text(resume_text)
            v = self._encode_text(job_description_text)
            r_prof = self.profile_extractor.extract_resume_profile(resume_text)
            j_prof = self.profile_extractor.extract_job_profile(job_description_text)
            d_feats = self.profile_extractor.combine_profiles(r_prof, j_prof)
            r_hit = False
            j_hit = False

        # Build scaled fusion features
        x_fuse = self.build_fusion_features(u, v, d_feats)

        # Classifier inference
        raw_probs = self.classifier.predict_proba(x_fuse)[0]
        pred_raw = self.classifier.predict(x_fuse)[0]

        # Extract probabilities in canonical order
        p_good = float(raw_probs[self.idx_good])
        p_no = float(raw_probs[self.idx_no])
        p_pot = float(raw_probs[self.idx_pot])

        t_elapsed = (time.perf_counter() - t0) * 1000.0

        return {
            "probabilities": {
                "No Fit": round(p_no, 6),
                "Potential Fit": round(p_pot, 6),
                "Good Fit": round(p_good, 6)
            },
            "predicted_class": str(pred_raw),
            "confidence": round(float(np.max(raw_probs)), 6),
            "cache_status": {
                "resume_hit": r_hit,
                "job_hit": j_hit,
                "both_hit": (r_hit and j_hit)
            },
            "latency_ms": round(t_elapsed, 3)
        }
