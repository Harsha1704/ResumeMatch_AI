"""
Phase 3 Test Suite: Resume Analyzer Hardening.
Tests:
- PDF/DOCX/TXT extraction reliability
- Scanned PDF detection, password-protected PDF handling, empty & corrupted files
- Page count limits (max 30 pages) and size limits (16 MB)
- Candidate profile extraction (name, email, phone, links, education, certifications)
- Absence of hallucinations / missing field tracking
- Duplicate skill occurrences and conflicting claim detection
- Job description responsibilities, qualifications, and tools extraction
- Technical token preservation (C++, C#, .NET, Node.js, SQL, Python, AWS)
- Disjunctive alternative requirement groups
- Unified evidence-grounded matches table schema and classifications
- Scorecard dimension separation without double-counting
- API endpoint status codes and error payload contracts
"""

import io
import pytest
import pymupdf
import docx
from flask import json

from app import app
from src.analysis.resume_parser import (
    parse_resume,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    MAX_PAGE_COUNT,
    MAX_FILE_SIZE
)
from src.analysis.candidate_profile_extractor import extract_candidate_profile
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.analysis.matching_engine import analyze_resume_and_job, get_matching_engine


# ---------------------------------------------------------------------------
# Helpers to generate synthetic test documents in-memory
# ---------------------------------------------------------------------------
def create_test_pdf(text: str, num_pages: int = 1) -> bytes:
    """Creates a simple searchable PDF in-memory."""
    doc = pymupdf.open()
    for _ in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_test_docx(paragraphs: list) -> bytes:
    """Creates a valid DOCX document in-memory."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


# ---------------------------------------------------------------------------
# 1. Resume Parser & Format Safety Tests
# ---------------------------------------------------------------------------
def test_parse_empty_payload():
    """Empty payload (0 bytes) returns status empty with clear message."""
    res = parse_resume(b"", filename="empty.pdf")
    assert res["status"] == "empty"
    assert "0 bytes" in res["error_message"] or "empty" in res["error_message"]


def test_parse_oversized_file():
    """File exceeding 16 MB limit is rejected safely."""
    oversized = b"A" * (MAX_FILE_SIZE + 1024)
    res = parse_resume(oversized, filename="giant.txt")
    assert res["status"] == "error"
    assert "16 MB" in res["error_message"]


def test_parse_corrupted_docx():
    """Invalid ZIP archive for DOCX returns descriptive error."""
    corrupt = b"PK\x03\x04" + b"garbage_not_a_valid_zip"
    res = parse_resume(corrupt, filename="corrupt.docx")
    assert res["status"] == "error"
    assert "corrupted" in res["error_message"].lower() or "invalid" in res["error_message"].lower()


def test_parse_scanned_pdf():
    """PDF with zero extractable text layer is flagged as scanned_pdf."""
    doc = pymupdf.open()
    doc.new_page()  # Blank page without text layer
    pdf_bytes = doc.tobytes()
    doc.close()

    res = parse_resume(pdf_bytes, filename="scanned.pdf")
    assert res["status"] == "scanned_pdf"
    assert "scanned image" in res["error_message"].lower() or "text layer" in res["error_message"].lower()


def test_parse_password_protected_pdf():
    """Password-protected / encrypted PDF is detected without unhandled crash."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Confidential Resume Data")
    perm = int(
        pymupdf.PDF_PERM_ACCESSIBILITY
        | pymupdf.PDF_PERM_PRINT
        | pymupdf.PDF_PERM_COPY
        | pymupdf.PDF_PERM_ANNOTATE
    )
    # Save with user and owner passwords
    pdf_bytes = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="secret_owner",
        user_pw="secret_user",
        permissions=perm
    )
    doc.close()

    res = parse_resume(pdf_bytes, filename="protected.pdf")
    assert res["status"] == "password_protected"
    assert "password-protected" in res["error_message"].lower() or "encrypted" in res["error_message"].lower()


def test_parse_pdf_page_count_limit():
    """PDF exceeding MAX_PAGE_COUNT (30 pages) is rejected safely."""
    doc = pymupdf.open()
    for _ in range(MAX_PAGE_COUNT + 2):
        p = doc.new_page()
        p.insert_text((50, 72), "Sample page text")
    pdf_bytes = doc.tobytes()
    doc.close()

    res = parse_resume(pdf_bytes, filename="huge_catalog.pdf")
    assert res["status"] == "error"
    assert f"{MAX_PAGE_COUNT} pages" in res["error_message"]


def test_valid_pdf_and_docx_parsing():
    """Valid PDF and DOCX parse text and preserve technical punctuation."""
    resume_text = "Jane Doe\njane@example.org\nSkills: C++, C#, .NET, Node.js, SQL\nExperience in AWS and Python."
    pdf_bytes = create_test_pdf(resume_text)
    docx_bytes = create_test_docx(resume_text.splitlines())

    pdf_res = parse_resume(pdf_bytes, filename="jane.pdf")
    docx_res = parse_resume(docx_bytes, filename="jane.docx")

    assert pdf_res["status"] == "success"
    assert docx_res["status"] == "success"
    assert "C++" in pdf_res["raw_text"] or "c++" in pdf_res["raw_text"].lower()
    assert "Node.js" in docx_res["raw_text"] or "node.js" in docx_res["raw_text"].lower()


# ---------------------------------------------------------------------------
# 2. Candidate Profile Extractor Tests
# ---------------------------------------------------------------------------
def test_candidate_profile_contact_and_education():
    """Candidate profile extracts contact info, links, and education accurately without hallucination."""
    text = """
    Alice Johnson
    alice.johnson@techcorp.io
    +1 (555) 234-5678
    https://linkedin.com/in/alicejohnson
    https://github.com/alicej
    https://alicejohnson.dev

    Education
    Bachelor of Technology in Computer Science
    National Institute of Technology 2022
    CGPA: 8.9 / 10

    Certifications
    AWS Certified Solutions Architect (2023)
    TensorFlow Developer Certificate

    Technical Skills
    Python, Docker, Kubernetes, SQL, PyTorch
    """
    profile = extract_candidate_profile(text)

    # Name
    assert profile["name"]["preferred_name"] == "Alice"
    assert profile["name"]["full_name"] == "Alice Johnson"

    # Contact Info
    assert profile["contact_info"]["primary_email"] == "alice.johnson@techcorp.io"
    assert profile["contact_info"]["primary_phone"] == "+1 (555) 234-5678"
    assert "linkedin.com/in/alicejohnson" in profile["contact_info"]["links"]["linkedin"]
    assert "github.com/alicej" in profile["contact_info"]["links"]["github"]

    # Education
    assert len(profile["education"]) >= 1
    edu = profile["education"][0]
    assert edu["degree_level"] == "Bachelor's"
    assert "Computer Science" in edu["field_of_study"] or "Computer Science" in edu["degree_name"]
    assert edu["graduation_year"] == 2022

    # Certifications
    assert len(profile["certifications"]) >= 1
    cert = profile["certifications"][0]
    assert "AWS" in cert["title"] or "Solutions Architect" in cert["title"]
    assert cert["issuer"] in ("AWS", "AMAZON", "Not specified")


def test_candidate_profile_missing_fields_no_hallucination():
    """Missing fields are flagged as 'Not provided' and tracked in missing_fields without hallucination."""
    minimal_text = "Software engineering enthusiast looking for new opportunities."
    profile = extract_candidate_profile(minimal_text)

    assert profile["contact_info"]["primary_email"] == "Not provided"
    assert profile["contact_info"]["primary_phone"] == "Not provided"
    assert profile["contact_info"]["links"]["linkedin"] == "Not provided"
    assert profile["contact_info"]["links"]["github"] == "Not provided"
    assert len(profile["education"]) == 0
    assert len(profile["certifications"]) == 0
    assert "email" in profile["missing_fields"]
    assert "phone" in profile["missing_fields"]
    assert "education" in profile["missing_fields"]


def test_candidate_profile_conflict_and_duplicate_detection():
    """Detects inverted date ranges, future graduation vs tenure anomalies, and cross-section duplicate skills."""
    text = """
    Bob Smith
    bob@domain.org
    
    Education
    Bachelor of Science in Information Technology
    State University 2028
    
    Experience
    Senior Lead Architect | 2024 - 2021
    Over 6 years of experience designing enterprise systems with Python, SQL, and Docker.
    
    Projects
    Scalable Cloud Gateway
    Engineered distributed microservices using Docker, Python, and SQL.
    
    Skills
    Python, SQL, Docker, Kubernetes
    """
    profile = extract_candidate_profile(text)

    # Inverted date range (2024 - 2021) or future graduation (2028 vs 6 yrs exp)
    assert len(profile["conflicts"]) >= 1
    conflict_types = [c["conflict_type"] for c in profile["conflicts"]]
    assert any(t in ("chronological_anomaly", "inverted_date_range") for t in conflict_types)

    # Duplicate skills across sections (Python, SQL, Docker appear in Skills, Projects, Experience)
    dup_skills = [d["skill"] for d in profile["duplicate_skills"]]
    assert any(s in ("python", "sql", "docker") for s in dup_skills)


# ---------------------------------------------------------------------------
# 3. Job Description Analyzer Tests
# ---------------------------------------------------------------------------
def test_job_analyzer_responsibilities_qualifications_tools():
    """Job analyzer separates responsibilities, qualifications, and developer tools cleanly."""
    jd_text = """
    Role: Senior Machine Learning Infrastructure Engineer

    About Us:
    Innovative AI startup creating real-time visual perception models.

    Responsibilities:
    - Design and maintain distributed inference pipelines in Python and C++.
    - Optimize GPU cluster utilization across multiple cloud providers.
    - Implement continuous integration and automated model testing.

    Required Qualifications:
    - 4+ years of professional backend engineering experience.
    - Deep hands-on proficiency with Docker, Kubernetes, AWS, and PyTorch.
    - Solid understanding of SQL and database indexing.

    Preferred Qualifications:
    - Experience with Terraform, Redis, or Apache Kafka.
    - Bachelor's degree in Computer Science or related STEM field.
    """
    ja = JobDescriptionAnalyzer()
    res = ja.analyze(jd_text)

    assert res["status"] == "success"
    assert "Senior Machine Learning Infrastructure Engineer" in res["job_title"]
    assert len(res["responsibilities"]) >= 2
    assert any("inference pipelines" in r for r in res["responsibilities"])

    assert len(res["qualifications"]) >= 2
    assert any("4+ years" in q for q in res["qualifications"])

    # Developer Tools
    assert len(res["tools_and_technologies"]) >= 2
    assert any(t in ("docker", "kubernetes", "amazon web services", "redis", "terraform", "sql") for t in res["tools_and_technologies"])

    # Experience requirements
    assert res["experience_requirements"]["is_explicit"] is True
    assert res["experience_requirements"]["min_years"] == 4.0


def test_job_analyzer_exact_tokens_and_alternatives():
    """Exact tokens (.NET, C++, Node.js, C#) and alternative groups ('Go or Rust') are preserved."""
    jd_text = """
    Full Stack Cloud Engineer
    Requirements:
    - Must have hands-on experience in C++, C#, .NET, and Node.js.
    - Proficiency in either Go or Rust for high-concurrency background services.
    - Experience with Power BI or Tableau for metrics dashboards.
    """
    ja = JobDescriptionAnalyzer()
    res = ja.analyze(jd_text)

    req_skills_lower = [s.lower() for s in res["required_skills"]]
    assert any(s in req_skills_lower for s in ("c++", "c#", ".net", "node.js"))

    # Alternative groups
    assert len(res["alternative_groups"]) >= 1
    group_skills = [set(g["canonical_skills"]) for g in res["alternative_groups"]]
    # Either (Go, Rust) or (Power BI, Tableau) identified
    assert any(
        {"Go", "Rust"}.issubset(gs) or {"Power BI", "Tableau"}.issubset(gs)
        for gs in group_skills
    )


# ---------------------------------------------------------------------------
# 4. Evidence-Grounded Matching & Scorecard Tests
# ---------------------------------------------------------------------------
def test_evidence_grounded_matches_table_schema():
    """Matching engine generates a unified evidence_grounded_matches table with complete schemas."""
    resume = """
    Sarah Connor
    sarah@tech.io
    +1 555-019-2834
    
    Technical Skills: Python, SQL
    
    Projects:
    Autonomous Telemetry Engine
    Engineered real-time data ingestion service in Python with Docker containers.
    """
    jd = """
    Software Engineer
    Required Qualifications:
    - Python
    - Docker
    - Kubernetes
    """
    res = analyze_resume_and_job(resume, jd)
    assert res["status"] == "success"

    matches = res["evidence_grounded_matches"]
    assert len(matches) == 3

    # Check required fields in each match entry
    for m in matches:
        assert "skill" in m
        assert "tier" in m
        assert "job_requirement_sentence" in m
        assert "candidate_evidence" in m
        assert "evidence_source" in m
        assert "match_classification" in m
        assert "confidence" in m
        assert "explanation" in m
        assert m["match_classification"] in (
            "fully_supported", "partially_supported", "explicitly_mentioned", "missing_evidence", "conflicting_evidence"
        )

    # Python should be fully supported via project context
    py_match = next(m for m in matches if m["skill"].lower() == "python")
    assert py_match["match_classification"] == "fully_supported"
    assert py_match["confidence"] >= 0.85
    assert "Autonomous Telemetry" in py_match["candidate_evidence"] or "real-time data" in py_match["candidate_evidence"]

    # Kubernetes should be missing evidence
    k8s_match = next(m for m in matches if m["skill"].lower() == "kubernetes")
    assert k8s_match["match_classification"] == "missing_evidence"
    assert k8s_match["confidence"] == 0.0
    assert "No direct evidence" in k8s_match["candidate_evidence"]


def test_scorecard_dimension_separation():
    """Scorecard clearly separates ML compatibility, skill coverage, experience, and education without conflation."""
    resume = """
    David Miller
    david@domain.org
    
    Education
    Bachelor of Science in Software Engineering
    University of California 2021
    
    Experience
    Full Stack Developer | 2021 - Present
    3 years of professional experience developing responsive web applications with TypeScript and React.
    
    Skills
    React, TypeScript, Node.js
    """
    jd = """
    Frontend Developer
    Requirements:
    - React, TypeScript, GraphQL
    - 2+ years of experience
    - Bachelor's degree in Computer Science or related field
    """
    res = analyze_resume_and_job(resume, jd)
    assert res["status"] == "success"

    sc = res["scorecard"]
    assert "ml_compatibility" in sc
    assert "skill_coverage" in sc
    assert "experience_coverage" in sc
    assert "qualification_coverage" in sc

    # Check that dimensions are cleanly separated
    assert "predicted_class" in sc["ml_compatibility"]
    assert "compatibility_score" in sc["ml_compatibility"]

    assert "full_coverage_pct" in sc["skill_coverage"]
    assert "any_coverage_pct" in sc["skill_coverage"]
    assert "total_required_count" in sc["skill_coverage"]

    assert sc["experience_coverage"]["job_required_years"] == 2.0
    assert sc["experience_coverage"]["meets_experience_requirement"] is True

    assert sc["qualification_coverage"]["education_verified"] is True
    assert len(sc["qualification_coverage"]["candidate_degrees"]) >= 1


# ---------------------------------------------------------------------------
# 5. API Endpoint Contract & Security Tests
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_api_match_success(client):
    """POST /api/match returns complete Phase 3 grounded schema."""
    payload = {
        "resume_text": "Alice Smith\nalice@test.com\nSkills: Python, SQL, Docker\nExperience:\nBuilt microservices in Python.",
        "job_description": "Backend Engineer\nRequirements:\n- Python, Docker, Kubernetes\n- 2+ years experience.",
        "target_role": "Backend Engineer"
    }
    resp = client.post("/api/match", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "candidate_profile" in data
    assert "evidence_grounded_matches" in data
    assert "scorecard" in data
    assert "responsibilities" in data
    assert "qualifications" in data


def test_api_match_empty_resume_rejected(client):
    """POST /api/match with too-short input is rejected with HTTP 400."""
    payload = {
        "resume_text": "",
        "job_description": "Valid job description requiring Python and Docker."
    }
    resp = client.post("/api/match", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"


def test_api_analyze_password_protected_upload(client):
    """POST /api/analyze with an encrypted PDF returns HTTP 400 with descriptive error."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Locked candidate file")
    pdf_bytes = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="locked_owner",
        user_pw="locked_user"
    )
    doc.close()

    data = {
        "job_description": "Software Engineer\nRequirements: Python, SQL",
        "resume_file": (io.BytesIO(pdf_bytes), "locked.pdf")
    }
    resp = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    res_json = resp.get_json()
    assert res_json["status"] == "error"
    assert "password-protected" in res_json["error_message"].lower() or "encrypted" in res_json["error_message"].lower()
