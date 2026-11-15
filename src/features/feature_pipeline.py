"""
Feature Engineering Pipeline for Supervised Resume-Job Matching.
Combines TF-IDF n-grams, cosine similarity, lexical differences, and domain-engineered skill/experience features.
Strictly fits learned transformations on training data only to prevent data leakage.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine


class ResumeJobFeaturePipeline(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible feature engineering transformer for (resume, job) pairs.
    """

    def __init__(
        self,
        max_tfidf_features: int = 2500,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 3
    ):
        self.max_tfidf_features = max_tfidf_features
        self.ngram_range = ngram_range
        self.min_df = min_df

        self.skill_engine = SkillEngine()
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_tfidf_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            sublinear_tf=True,
            norm="l2"
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names: List[str] = []

    def _extract_dense_features(
        self,
        resumes: List[str],
        jobs: List[str]
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Extracts numerical domain features:
        - Skill overlap, coverage, Jaccard similarity
        - Explicit experience years and experience gap
        - Word counts, character lengths, section counts
        - Cosine similarity and vector distances
        """
        feature_rows: List[List[float]] = []
        feature_names = [
            "skill_jaccard_similarity",
            "job_coverage_ratio",
            "resume_relevance_ratio",
            "matched_skill_count",
            "missing_skill_count",
            "resume_skill_count",
            "job_skill_count",
            "resume_years_exp",
            "job_years_exp",
            "exp_difference",
            "has_required_exp",
            "resume_word_count",
            "job_word_count",
            "length_ratio",
            "resume_section_count"
        ]

        for r_raw, j_raw in zip(resumes, jobs):
            # 1. Clean texts
            r_clean = clean_text(r_raw)
            j_clean = clean_text(j_raw)

            # 2. Skill gap metrics
            gap = self.skill_engine.analyze_skill_gap(r_clean, j_clean)

            # 3. Structural metrics
            r_struct = parse_structural_features(r_raw)
            j_struct = parse_structural_features(j_raw)

            r_exp = r_struct["explicit_years_exp"]
            j_exp = j_struct["explicit_years_exp"]
            exp_diff = r_exp - j_exp
            has_req_exp = 1.0 if (j_exp > 0 and r_exp >= j_exp) or (j_exp == 0.0 and r_exp > 0) else 0.0

            r_words = max(r_struct["word_count"], 1.0)
            j_words = max(j_struct["word_count"], 1.0)
            length_ratio = r_words / j_words

            row = [
                float(gap["jaccard_similarity"]),
                float(gap["job_coverage_ratio"]),
                float(gap["resume_relevance_ratio"]),
                float(gap["matched_skill_count"]),
                float(gap["missing_skill_count"]),
                float(gap["resume_skill_count"]),
                float(gap["job_skill_count"]),
                float(r_exp),
                float(j_exp),
                float(exp_diff),
                float(has_req_exp),
                float(r_words),
                float(j_words),
                float(length_ratio),
                float(r_struct["section_count"])
            ]
            feature_rows.append(row)

        dense_matrix = np.array(feature_rows, dtype=np.float32)
        return dense_matrix, feature_names

    def fit(self, X: Union[pd.DataFrame, Tuple[List[str], List[str]]], y=None):
        """
        Fits vectorizer and scaler strictly on training data.
        X can be a DataFrame with ['resume_text', 'job_description_text'] or a tuple of (resumes, jobs).
        """
        if isinstance(X, pd.DataFrame):
            resumes = X["resume_text"].tolist()
            jobs = X["job_description_text"].tolist()
        else:
            resumes, jobs = X

        # Fit TF-IDF on combined cleaned corpus of resumes and job descriptions
        cleaned_resumes = [clean_text(t) for t in resumes]
        cleaned_jobs = [clean_text(t) for t in jobs]
        corpus = cleaned_resumes + cleaned_jobs
        self.vectorizer.fit(corpus)

        # Extract and fit scaler on dense features
        dense_feats, dense_names = self._extract_dense_features(resumes, jobs)
        self.scaler.fit(dense_feats)

        # Build feature names
        tfidf_vocab_names = [f"tfidf_diff_{name}" for name in self.vectorizer.get_feature_names_out()]
        interaction_names = ["tfidf_cosine_similarity", "tfidf_manhattan_dist", "tfidf_euclidean_dist"]
        self.feature_names = tfidf_vocab_names + interaction_names + dense_names

        self.is_fitted = True
        return self

    def transform(self, X: Union[pd.DataFrame, Tuple[List[str], List[str]]]) -> sparse.csr_matrix:
        """
        Transforms resume-job pairs into a unified sparse feature matrix.
        """
        if not self.is_fitted:
            raise ValueError("ResumeJobFeaturePipeline must be fitted before transform.")

        if isinstance(X, pd.DataFrame):
            resumes = X["resume_text"].tolist()
            jobs = X["job_description_text"].tolist()
        else:
            resumes, jobs = X

        cleaned_resumes = [clean_text(t) for t in resumes]
        cleaned_jobs = [clean_text(t) for t in jobs]

        # 1. TF-IDF representations
        V_resume = self.vectorizer.transform(cleaned_resumes)
        V_job = self.vectorizer.transform(cleaned_jobs)

        # 2. Vector distance and interaction features
        # Absolute difference
        V_diff = abs(V_resume - V_job)

        # Cosine similarity (since V_resume and V_job are L2-normalized)
        cosine_sim = np.asarray((V_resume.multiply(V_job)).sum(axis=1)).reshape(-1, 1)

        # Manhattan distance on TF-IDF space
        manhattan = np.asarray(V_diff.sum(axis=1)).reshape(-1, 1)

        # Euclidean distance
        euclidean = np.sqrt(np.asarray(V_diff.power(2).sum(axis=1))).reshape(-1, 1)

        tfidf_interactions = np.hstack([cosine_sim, manhattan, euclidean])

        # 3. Dense engineered features
        dense_feats, _ = self._extract_dense_features(resumes, jobs)
        dense_scaled = self.scaler.transform(dense_feats)

        # Combine all features into CSR sparse matrix
        combined = sparse.hstack([
            V_diff,
            sparse.csr_matrix(tfidf_interactions),
            sparse.csr_matrix(dense_scaled)
        ], format="csr")

        return combined

    def fit_transform(self, X, y=None) -> sparse.csr_matrix:
        """Fits on training data and transforms."""
        return self.fit(X, y).transform(X)

    def save(self, filepath: Union[str, Path]) -> None:
        """Serializes the fitted pipeline with joblib."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "ResumeJobFeaturePipeline":
        """Loads a serialized pipeline."""
        return joblib.load(filepath)
