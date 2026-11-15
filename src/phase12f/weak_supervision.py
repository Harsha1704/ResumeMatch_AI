"""
src/phase12f/weak_supervision.py
Modular Weak-Supervision System for Resume-Job Compatibility Matching.
Implements programmatic Labeling Functions (LFs), measures coverage and conflict rates,
and aggregates noisy signals via a generative consensus label model.
STRICT ISOLATION GUARANTEE: Weak labels are never treated as ground truth.
"""

from typing import Dict, List, Optional, Tuple, Callable
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text, parse_structural_features

# Label encoding: 0 = No Fit, 1 = Potential Fit, 2 = Good Fit, -1 = Abstain
NO_FIT = 0
POTENTIAL_FIT = 1
GOOD_FIT = 2
ABSTAIN = -1

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
INT_TO_LABEL = {0: "No Fit", 1: "Potential Fit", 2: "Good Fit", -1: "Abstain"}


class WeakLabelingSystem:
    """
    Manages labeling functions, evaluates consensus, and produces aggregated weak labels.
    """

    def __init__(self):
        self.skill_engine = SkillEngine()
        self.labeling_functions: List[Tuple[str, Callable]] = [
            ("lf_mandatory_skill_coverage", self.lf_mandatory_skill_coverage),
            ("lf_experience_gap", self.lf_experience_gap),
            ("lf_veto_disqualification", self.lf_veto_disqualification),
            ("lf_transferable_skills", self.lf_transferable_skills),
            ("lf_jaccard_similarity", self.lf_jaccard_similarity)
        ]
        self.weights: Optional[np.ndarray] = None

    def lf_mandatory_skill_coverage(self, r_text: str, j_text: str, **kwargs) -> int:
        """LF 1: Evaluates proportion of JD skills present in resume."""
        r_skills = set(self.skill_engine.extract_skills(clean_text(r_text)))
        j_skills = set(self.skill_engine.extract_skills(clean_text(j_text)))

        if not j_skills:
            return ABSTAIN

        overlap = len(r_skills.intersection(j_skills))
        coverage = overlap / len(j_skills)

        if coverage >= 0.35 and overlap >= 2:
            return GOOD_FIT
        elif coverage == 0.0 and len(j_skills) >= 2:
            return NO_FIT
        elif 0.15 <= coverage < 0.35:
            return POTENTIAL_FIT
        return ABSTAIN

    def lf_experience_gap(self, r_text: str, j_text: str, **kwargs) -> int:
        """LF 2: Evaluates stated years of experience gap. Repaired in Phase 12F.2."""
        r_struct = parse_structural_features(r_text)
        j_struct = parse_structural_features(j_text)

        r_exp = r_struct.get("explicit_years_exp", r_struct.get("years_experience", 0.0))
        j_exp = j_struct.get("explicit_years_exp", j_struct.get("years_experience", 0.0))

        if j_exp == 0.0:
            return ABSTAIN

        gap = r_exp - j_exp
        if gap <= -2.5:
            return NO_FIT
        elif gap >= 0.0 and r_exp >= 1.0:
            return GOOD_FIT
        elif -2.0 <= gap < 0.0:
            return POTENTIAL_FIT
        return ABSTAIN

    def lf_veto_disqualification(self, r_text: str, j_text: str, **kwargs) -> int:
        """LF 3: Fires NO_FIT if hard requirement is explicitly missing."""
        r_clean = clean_text(r_text).lower()
        j_clean = clean_text(j_text).lower()

        # Check for specialized high-barrier keywords in JD
        specializations = ["kubernetes", "machine learning", "salesforce", "android", "ios", "devops"]
        for spec in specializations:
            if spec in j_clean and spec not in r_clean:
                # If JD mentions it >= 3 times as primary tech, candidate having 0 is a veto
                if j_clean.count(spec) >= 3:
                    return NO_FIT
        return ABSTAIN

    def lf_transferable_skills(self, r_text: str, j_text: str, **kwargs) -> int:
        """LF 4: Fires POTENTIAL_FIT if adjacent tech stack exists."""
        r_skills = set(self.skill_engine.extract_skills(clean_text(r_text)))
        j_skills = set(self.skill_engine.extract_skills(clean_text(j_text)))

        # Defined transferable clusters
        transfer_clusters = [
            {"react", "vue", "angular", "svelte"},
            {"aws", "gcp", "azure"},
            {"django", "flask", "fastapi", "spring", "express"},
            {"postgresql", "mysql", "sql", "sqlite", "oracle"},
            {"pytorch", "tensorflow", "keras"},
            {"java", "kotlin", "scala"},
            {"docker", "kubernetes", "openshift"}
        ]
        for cluster in transfer_clusters:
            # If JD requires something in cluster, and resume has another in cluster but not exact
            jd_in_cluster = cluster.intersection(j_skills)
            res_in_cluster = cluster.intersection(r_skills)
            if jd_in_cluster and res_in_cluster and not jd_in_cluster.intersection(res_in_cluster):
                return POTENTIAL_FIT
        return ABSTAIN

    def lf_jaccard_similarity(self, r_text: str, j_text: str, **kwargs) -> int:
        """LF 5: Lexical Jaccard skill similarity."""
        r_skills = set(self.skill_engine.extract_skills(clean_text(r_text)))
        j_skills = set(self.skill_engine.extract_skills(clean_text(j_text)))
        if not r_skills or not j_skills:
            return ABSTAIN

        union = len(r_skills.union(j_skills))
        jaccard = len(r_skills.intersection(j_skills)) / union if union > 0 else 0.0

        if jaccard >= 0.22:
            return GOOD_FIT
        elif jaccard <= 0.05 and len(j_skills) >= 3:
            return NO_FIT
        elif 0.08 <= jaccard < 0.22:
            return POTENTIAL_FIT
        return ABSTAIN

    def apply_lfs(self, resumes: List[str], jobs: List[str]) -> np.ndarray:
        """
        Applies all labeling functions to a batch of resume-job pairs.
        Returns: matrix L of shape (N, num_LFs) with entries in {-1, 0, 1, 2}.
        """
        N = len(resumes)
        M = len(self.labeling_functions)
        L = np.full((N, M), ABSTAIN, dtype=int)

        for j, (name, lf_func) in enumerate(self.labeling_functions):
            for i in range(N):
                L[i, j] = lf_func(resumes[i], jobs[i])
        return L

    def compute_lf_statistics(self, L: np.ndarray) -> Dict:
        """
        Computes coverage, overlap, and conflict rates across LFs.
        """
        N, M = L.shape
        coverage = np.mean(L != ABSTAIN, axis=0)
        overall_coverage = np.mean(np.any(L != ABSTAIN, axis=1))

        # Conflicts: instances where at least two LFs vote with different non-abstain labels
        conflicts = 0
        overlaps = 0
        for i in range(N):
            votes = [L[i, j] for j in range(M) if L[i, j] != ABSTAIN]
            if len(votes) >= 2:
                overlaps += 1
                if len(set(votes)) > 1:
                    conflicts += 1

        overlap_rate = overlaps / N if N > 0 else 0.0
        conflict_rate = conflicts / N if N > 0 else 0.0

        return {
            "num_lfs": M,
            "overall_coverage": round(float(overall_coverage), 4),
            "overlap_rate": round(float(overlap_rate), 4),
            "conflict_rate": round(float(conflict_rate), 4),
            "per_lf_coverage": {name: round(float(cov), 4) for (name, _), cov in zip(self.labeling_functions, coverage)}
        }

    def aggregate_weak_labels(self, L: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Aggregates LF votes using a weighted consensus model.
        Returns:
            aggregated_labels: array of shape (N,) with integer labels (or -1 if all abstained)
            confidence_scores: array of shape (N,) with confidence in [0.0, 1.0]
        """
        N, M = L.shape
        aggregated_labels = np.full(N, -1, dtype=int)
        confidence_scores = np.zeros(N, dtype=np.float32)

        # Base LF accuracy prior weights
        lf_weights = np.array([1.2, 1.1, 1.4, 0.9, 1.0])

        for i in range(N):
            row_votes = L[i]
            active_mask = (row_votes != ABSTAIN)
            if not np.any(active_mask):
                continue

            active_lfs = np.where(active_mask)[0]
            class_scores = np.zeros(3, dtype=np.float32)

            for lf_idx in active_lfs:
                vote = row_votes[lf_idx]
                w = lf_weights[lf_idx]
                class_scores[vote] += w

            total_weight = class_scores.sum()
            if total_weight > 0:
                probs = class_scores / total_weight
                best_class = int(np.argmax(probs))
                confidence = float(probs[best_class])

                aggregated_labels[i] = best_class
                confidence_scores[i] = confidence

        return aggregated_labels, confidence_scores
