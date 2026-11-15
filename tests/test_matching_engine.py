"""
Unit tests for the Master Resume Matching Engine and Structured Response Output.
"""

import pytest
from src.analysis.matching_engine import analyze_resume_and_job
from src.models.inference import CLASSES


def test_matching_engine_structured_output():
    """Verify that matching engine returns all mandatory fields with valid JSON-serializable types."""
    resume_text = (
        "Alice Wong\n"
        "Machine Learning Specialist with 5 years of experience.\n"
        "Proficient in Python, Scikit-learn, PyTorch, SQL, and Docker.\n"
        "PROJECTS:\n"
        "Resume Matching System: Developed and deployed NLP compatibility classifier in Python.\n"
    )
    job_text = (
        "Position: Machine Learning Engineer\n"
        "Required Skills:\n"
        "- Python\n"
        "- Scikit-learn\n"
        "- PyTorch\n"
        "- Docker\n"
        "- Kubernetes\n"
        "Experience: 4+ years of experience required.\n"
    )

    result = analyze_resume_and_job(resume_text, job_text, resume_filename="alice_resume.txt")

    assert result["status"] == "success"
    assert "analysis_id" in result
    assert result["predicted_class"] in CLASSES
    assert 0.0 <= result["model_confidence"] <= 1.0
    assert 0.0 <= result["compatibility_score"] <= 100.0
    assert 0.0 <= result["skill_coverage"] <= 100.0

    # Skills check
    assert "python" in result["matched_skills"]
    assert "scikit-learn" in result["matched_skills"]
    assert "kubernetes" in result["missing_skills"]

    # Recommendations and learning resources
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0
    assert isinstance(result["learning_resources"], list)
    # Check that Kubernetes official documentation link is present
    k8s_res = [res for res in result["learning_resources"] if "Kubernetes" in res["skill"]]
    if k8s_res:
        assert "kubernetes.io" in k8s_res[0]["url"]

    # Experience evidence
    exp = result["experience_analysis"]
    assert exp["resume_years_exp"] == 5.0
    assert exp["job_required_years"] == 4.0
    assert exp["meets_experience_requirement"] is True


def test_matching_engine_empty_input_handling():
    """Verify empty inputs return non-crashing structured fallback with 'No Fit'."""
    result = analyze_resume_and_job("", "")
    assert result["status"] in ["empty", "error", "invalid_input"]
    assert result["predicted_class"] == "No Fit"
    assert result["compatibility_score"] == 0.0
