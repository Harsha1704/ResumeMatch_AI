"""
Phase 7B Experimental Feature Engineering Pipeline.
Implements Feature Sets A, B, C, D, and E with strict zero-leakage fold-level fitting.
All experimental code is kept isolated under experiments/model_optimization/.
"""

import re
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, RobustScaler

from src.preprocessing.text_cleaner import clean_text, parse_structural_features, extract_explicit_experience_years
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


class ExperimentalDomainExtractor:
    """
    Extracts rich domain-engineered features for resume-job pairs:
    - Overall skill coverage, relevance, Jaccard
    - Mandatory vs preferred skill breakdown
    - Taxonomy-specific overlap (programming, frameworks, db, cloud, tools, soft)
    - Experience gap and requirement indicators
    - Education / degree requirement indicators
    - Structural length and complexity metrics
    """

    def __init__(self):
        self.skill_engine = SkillEngine()

    def extract_pair_features(self, resume_raw: str, job_raw: str) -> Dict[str, float]:
        r_clean = clean_text(resume_raw)
        j_clean = clean_text(job_raw)

        # 1. Skill Extraction
        r_skill_set = self.skill_engine.extract_skills(r_clean)
        j_skill_set = self.skill_engine.extract_skills(j_clean)

        matched_skills = r_skill_set.intersection(j_skill_set)
        missing_skills = j_skill_set.difference(r_skill_set)

        n_matched = len(matched_skills)
        n_missing = len(missing_skills)
        n_resume_skills = len(r_skill_set)
        n_job_skills = len(j_skill_set)

        jaccard = n_matched / len(r_skill_set.union(j_skill_set)) if (r_skill_set or j_skill_set) else 0.0
        coverage = n_matched / n_job_skills if n_job_skills > 0 else 1.0
        relevance = n_matched / n_resume_skills if n_resume_skills > 0 else 0.0

        # 2. Mandatory vs Preferred Job Skills
        # Segment job lines for mandatory vs preferred linguistic markers
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

        # Mandatory & Preferred metrics
        n_mand_total = len(mandatory_skills)
        n_mand_matched = len(mandatory_skills.intersection(r_skill_set))
        mand_coverage = n_mand_matched / n_mand_total if n_mand_total > 0 else coverage

        n_pref_total = len(preferred_skills)
        n_pref_matched = len(preferred_skills.intersection(r_skill_set))
        pref_coverage = n_pref_matched / n_pref_total if n_pref_total > 0 else 1.0

        # 3. Category-Specific Alignment
        cat_counts = {
            "prog": 0, "fw": 0, "db": 0, "cloud": 0, "tool": 0, "soft": 0
        }
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

        # 4. Experience Metrics
        r_struct = parse_structural_features(resume_raw)
        j_struct = parse_structural_features(job_raw)

        r_exp = float(r_struct["explicit_years_exp"])
        j_exp = float(j_struct["explicit_years_exp"])
        exp_diff = r_exp - j_exp
        has_req_exp = 1.0 if (j_exp > 0 and r_exp >= j_exp) or (j_exp == 0.0 and r_exp > 0) else 0.0

        # 5. Education Metrics
        j_has_degree_req = 1.0 if any(re.search(p, job_raw.lower()) for p in EDUCATION_PATTERNS) else 0.0
        r_has_degree = 1.0 if any(re.search(p, resume_raw.lower()) for p in EDUCATION_PATTERNS) else 0.0
        edu_match = 1.0 if (not j_has_degree_req or r_has_degree) else 0.0

        # 6. Text & Length Features
        r_words = float(max(r_struct["word_count"], 1))
        j_words = float(max(j_struct["word_count"], 1))
        length_ratio = r_words / j_words
        r_sections = float(r_struct["section_count"])

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


class AdvancedFeaturePipeline(BaseEstimator, TransformerMixin):
    """
    Modular Feature Pipeline implementing:
    - Feature Set A: Optimized TF-IDF (unigram + bigram, sublinear TF)
    - Feature Set B: Directional features (V_diff, V_signed, V_dot, cosine, euclidean, manhattan)
    - Feature Set C: Technical token-preserving tokenizer
    - Feature Set D: Domain alignment features (28 metrics)
    - Feature Set E: Latent Semantic Analysis (TruncatedSVD components)
    Strictly fits vocabulary, SVD, and scalers on training folds only.
    """

    def __init__(
        self,
        max_tfidf_features: int = 2500,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 3,
        use_directional: bool = True,
        use_svd: bool = True,
        svd_components: int = 128,
        use_domain_features: bool = True
    ):
        self.max_tfidf_features = max_tfidf_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.use_directional = use_directional
        self.use_svd = use_svd
        self.svd_components = svd_components
        self.use_domain_features = use_domain_features

        # Custom token pattern to preserve C++, C#, .NET, Node.js, CI/CD, etc.
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_tfidf_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            sublinear_tf=True,
            norm="l2",
            token_pattern=r"(?u)\b[a-zA-Z0-9_\.\#\+\-]+\b"
        )
        self.scaler = RobustScaler()
        self.svd = TruncatedSVD(n_components=self.svd_components, random_state=42) if use_svd else None
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y=None, precomputed_domain_df: Optional[pd.DataFrame] = None):
        resumes = [clean_text(t) for t in X["resume_text"]]
        jobs = [clean_text(t) for t in X["job_description_text"]]

        # Fit TF-IDF on combined training corpus
        corpus = resumes + jobs
        self.vectorizer.fit(corpus)

        # Fit SVD on TF-IDF representation if enabled
        if self.use_svd:
            V_train = self.vectorizer.transform(corpus)
            n_comp = min(self.svd_components, max(1, V_train.shape[1] - 1))
            self.svd = TruncatedSVD(n_components=n_comp, random_state=42)
            if V_train.shape[1] > 1:
                self.svd.fit(V_train)
            else:
                self.use_svd = False

        # Fit Scaler on Domain Features
        if self.use_domain_features:
            if precomputed_domain_df is not None:
                domain_feats = precomputed_domain_df.values
            else:
                extractor = ExperimentalDomainExtractor()
                rows = [extractor.extract_pair_features(r, j) for r, j in zip(X["resume_text"], X["job_description_text"])]
                domain_feats = pd.DataFrame(rows).values
            self.scaler.fit(domain_feats)

        self.is_fitted = True
        return self

    def transform(
        self,
        X: pd.DataFrame,
        precomputed_domain_df: Optional[pd.DataFrame] = None
    ) -> sparse.csr_matrix:
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before transform.")

        resumes = [clean_text(t) for t in X["resume_text"]]
        jobs = [clean_text(t) for t in X["job_description_text"]]

        V_resume = self.vectorizer.transform(resumes)
        V_job = self.vectorizer.transform(jobs)

        parts = []

        # 1. Lexical Difference and Directional Features
        V_diff = abs(V_resume - V_job)
        parts.append(V_diff)

        if self.use_directional:
            # Signed difference: captures whether resume has excess or deficient terms
            V_signed = V_resume - V_job
            # Element-wise interaction: active only where BOTH share the term
            V_dot = V_resume.multiply(V_job)
            parts.extend([V_signed, V_dot])

        # Interaction scalars (cosine, manhattan, euclidean)
        cosine_sim = np.asarray((V_resume.multiply(V_job)).sum(axis=1)).reshape(-1, 1)
        manhattan = np.asarray(V_diff.sum(axis=1)).reshape(-1, 1)
        euclidean = np.sqrt(np.asarray(V_diff.power(2).sum(axis=1))).reshape(-1, 1)
        lexical_interactions = np.hstack([cosine_sim, manhattan, euclidean])
        parts.append(sparse.csr_matrix(lexical_interactions))

        # 2. Latent Semantic Analysis (TruncatedSVD)
        if self.use_svd and self.svd is not None:
            svd_r = self.svd.transform(V_resume)
            svd_j = self.svd.transform(V_job)
            svd_diff = abs(svd_r - svd_j)
            svd_dot = svd_r * svd_j
            # SVD cosine similarity
            norm_r = np.linalg.norm(svd_r, axis=1, keepdims=True) + 1e-9
            norm_j = np.linalg.norm(svd_j, axis=1, keepdims=True) + 1e-9
            svd_cosine = np.sum((svd_r / norm_r) * (svd_j / norm_j), axis=1, keepdims=True)
            svd_feats = np.hstack([svd_diff, svd_dot, svd_cosine])
            parts.append(sparse.csr_matrix(svd_feats))

        # 3. Domain Engineered Features
        if self.use_domain_features:
            if precomputed_domain_df is not None:
                domain_feats = precomputed_domain_df.values
            else:
                extractor = ExperimentalDomainExtractor()
                rows = [extractor.extract_pair_features(r, j) for r, j in zip(X["resume_text"], X["job_description_text"])]
                domain_feats = pd.DataFrame(rows).values
            domain_scaled = self.scaler.transform(domain_feats)
            parts.append(sparse.csr_matrix(domain_scaled))

        return sparse.hstack(parts, format="csr")
