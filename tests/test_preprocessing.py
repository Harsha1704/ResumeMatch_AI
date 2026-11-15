"""
Comprehensive Unit Tests for Data Preprocessing and Feature Engineering.
Verifies text cleaning, token preservation, skill extraction, alias normalization,
leakage prevention, and scikit-learn feature pipeline compatibility.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from scipy import sparse

from src.preprocessing.text_cleaner import clean_text, extract_explicit_experience_years, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine, TECHNICAL_ALIAS_MAP
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split


@pytest.fixture(scope="module")
def skill_engine():
    return SkillEngine()


def test_empty_and_missing_values(skill_engine):
    """Test handling of None, empty strings, and whitespace."""
    assert clean_text("") == ""
    assert clean_text(None) == ""
    assert clean_text("     \n\t  ") == ""
    assert skill_engine.extract_skills("") == set()
    assert skill_engine.extract_skills(None) == set()
    assert extract_explicit_experience_years("") == 0.0
    assert extract_explicit_experience_years(None) == 0.0


def test_mixed_capitalization_and_html():
    """Verify HTML stripping, Unicode normalization, and case invariance."""
    raw = "<p>Experienced&nbsp;DEVELOPER with <b>Python</b> and &amp; JavaScript skills.</p>"
    cleaned = clean_text(raw)
    assert "<p>" not in cleaned
    assert "&nbsp;" not in cleaned
    assert "&amp;" not in cleaned
    assert "Experienced DEVELOPER with Python and JavaScript skills." in cleaned


def test_preservation_of_technical_skills_with_punctuation(skill_engine):
    """Verify critical technical tokens like C++, C#, .NET, Node.js are strictly preserved."""
    text = "Proficient in C++, C#, .NET Core, Node.js, PL/SQL, TCP/IP, and CI/CD pipelines."
    cleaned = clean_text(text)
    assert "c++" in cleaned.lower()
    assert "c#" in cleaned.lower()
    assert ".net" in cleaned.lower()
    assert "node.js" in cleaned.lower()
    assert "pl/sql" in cleaned.lower()
    assert "ci/cd" in cleaned.lower()

    extracted = skill_engine.extract_skills(text)
    assert "c++" in extracted
    assert "c#" in extracted
    assert ".net" in extracted
    assert "node.js" in extracted
    assert "pl/sql" in extracted
    assert "ci/cd" in extracted


def test_skill_alias_normalization(skill_engine):
    """Verify alias mapping correctly canonicalizes variants without LLMs."""
    alias_test_cases = [
        ("cpp", "c++"),
        ("k8s", "kubernetes"),
        ("golang", "go"),
        ("reactjs", "react"),
        ("react.js", "react"),
        ("postgres", "postgresql"),
        ("aws", "amazon web services"),
        ("sklearn", "scikit-learn"),
        ("tf", "tensorflow"),
        ("torch", "pytorch")
    ]
    for alias, canonical in alias_test_cases:
        res = skill_engine.extract_skills(f"Experienced with {alias} in production.")
        assert canonical in res, f"Failed for alias '{alias}' -> expected '{canonical}'"


def test_unusual_characters_and_long_resumes(skill_engine):
    """Verify pipeline handles weird characters, bullet symbols, and extremely long text."""
    unusual = "• Bullet point with \u2013 en-dash, \xa0 non-breaking space, and emoji 🚀."
    cleaned = clean_text(unusual)
    assert "•" not in cleaned
    assert "Bullet point with" in cleaned

    # Very long resume (10,000 words)
    long_resume = "Software engineer working with Python, Docker, and Kubernetes. " * 1000
    struct = parse_structural_features(long_resume)
    assert struct["word_count"] > 5000
    skills = skill_engine.extract_skills(long_resume)
    assert "python" in skills
    assert "docker" in skills
    assert "kubernetes" in skills


def test_explicit_experience_extraction():
    """Verify years of experience are only extracted when explicitly stated."""
    # Explicit cases
    assert extract_explicit_experience_years("Senior Engineer with 8 years of experience in data systems.") == 8.0
    assert extract_explicit_experience_years("Requires 5+ yrs exp in backend development.") == 5.0
    assert extract_explicit_experience_years("Minimum of 3.5 years professional experience required.") == 3.5

    # Non-experience numbers should NOT be extracted as experience
    assert extract_explicit_experience_years("Graduated in 2020 from University.") == 0.0
    assert extract_explicit_experience_years("Worked on 12 projects across 4 teams.") == 0.0


def test_skill_gap_analysis_engine(skill_engine):
    """Verify matched, missing, Jaccard, and coverage ratios."""
    resume = "Candidate with Python, SQL, Docker, and Machine Learning experience."
    job = "Looking for an engineer with Python, Docker, Kubernetes, AWS, and Machine Learning."

    gap = skill_engine.analyze_skill_gap(resume, job)
    assert set(gap["matched_skills"]) == {"python", "docker", "machine learning"}
    assert set(gap["missing_skills"]) == {"kubernetes", "amazon web services"}
    assert gap["matched_skill_count"] == 3
    assert gap["missing_skill_count"] == 2
    assert gap["job_coverage_ratio"] == 0.6  # 3 / 5
    assert gap["jaccard_similarity"] > 0.4


def test_leakage_safeguards():
    """Verify that split strategies prevent contamination."""
    # 1. Unseen jobs split
    train_sub, _, test_df = get_unseen_jobs_split()
    train_jobs = set(train_sub["job_description_text"])
    test_jobs = set(test_df["job_description_text"])
    assert len(train_jobs.intersection(test_jobs)) == 0, "Leakage: Overlapping jobs between train and held-out test!"

    # 2. Unseen resumes split
    r_train, r_val = get_unseen_resumes_split()
    r_train_set = set(r_train["resume_text"])
    r_val_set = set(r_val["resume_text"])
    assert len(r_train_set.intersection(r_val_set)) == 0, "Leakage: Overlapping resumes between train and val!"


def test_feature_pipeline_sklearn_compatibility():
    """Verify feature pipeline fits, transforms, and produces valid scikit-learn matrix."""
    # Small test sample
    sample_df = pd.DataFrame({
        "resume_text": [
            "Senior Python Developer with 5 years experience in Docker, AWS, and PostgreSQL.",
            "Junior Web Designer with HTML, CSS, Figma, and JavaScript."
        ],
        "job_description_text": [
            "Seeking Senior Python Engineer with 4+ years exp in AWS, Docker, and Kubernetes.",
            "Frontend Designer wanted with HTML5, CSS3, and React experience."
        ],
        "label": ["Good Fit", "Potential Fit"]
    })

    pipe = ResumeJobFeaturePipeline(max_tfidf_features=100, min_df=1)
    X_mat = pipe.fit_transform(sample_df)

    assert isinstance(X_mat, sparse.csr_matrix)
    assert X_mat.shape[0] == 2
    # Verify exact column composition: TF-IDF vocab features + 3 vector interaction features + 15 dense features
    expected_dim = len(pipe.vectorizer.vocabulary_) + 3 + 15
    assert X_mat.shape[1] == expected_dim
    assert not np.isnan(X_mat.data).any()

    # Verify transform on unseen pairs
    unseen_df = pd.DataFrame({
        "resume_text": ["Data Scientist with Python and SQL."],
        "job_description_text": ["Data Analyst needed with SQL and Python."]
    })
    X_unseen = pipe.transform(unseen_df)
    assert X_unseen.shape[0] == 1
    assert X_unseen.shape[1] == X_mat.shape[1]
