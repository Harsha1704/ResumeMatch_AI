"""
End-to-End Real Resume Test Cases covering 10 representative industry scenarios.

Phase 6 Task 4:
1. Strong skill alignment (Candidate matches majority of required technical skills)
2. Partial skill alignment (Candidate has fundamental skills but lacks niche frameworks)
3. Little relevant skill evidence (Candidate from mismatched domain)
4. Missing employment experience (No explicit experience years in resume)
5. Technical skills preservation (C++, C#, .NET, Node.js, Python, SQL, Docker)
6. Empty or corrupted resume (Graceful exception handling and validation)
7. Unsupported file type (.exe, .png, .bin rejected safely)
8. Empty job description (Handled gracefully with clean validation)
9. Long job description (>10,000 characters processed without timeout or memory issues)
10. Scanned PDF without extractable text (Flagged with warning indicating OCR needed)
"""

import io
import pytest
import pymupdf
from src.analysis.matching_engine import analyze_resume_and_job
from src.analysis.resume_parser import parse_resume


# -------------------------------------------------------------------------
# Case 1: Strong Skill Alignment
# -------------------------------------------------------------------------
def test_case_1_strong_skill_alignment():
    resume = """
    Jane Doe - Senior Machine Learning Engineer
    Email: jane.doe@example.com
    Experience: 5 years in machine learning, deep learning, and data pipelines.
    Technical Skills: Python, Scikit-learn, PyTorch, TensorFlow, SQL, Docker, Git, Pandas, NumPy.
    Projects: Designed real-time recommendation systems and predictive pipelines.
    """
    job = """
    We are seeking a Machine Learning Engineer with 3+ years experience.
    Mandatory Requirements:
    - Python, Scikit-learn, SQL, Docker, PyTorch
    - Strong background in machine learning algorithms and predictive modeling.
    """
    result = analyze_resume_and_job(resume, job)

    assert result["status"] == "success"
    assert result["predicted_class"] in ["Good Fit", "Moderate Fit"]
    assert result["model_confidence"] > 0.0
    matched_names = {s.lower() for s in result["matched_skills"]}
    assert "python" in matched_names
    assert "sql" in matched_names
    assert "docker" in matched_names
    assert result["skill_coverage"] >= 50.0
    assert result["experience_analysis"]["meets_experience_requirement"] is True


# -------------------------------------------------------------------------
# Case 2: Partial Skill Alignment
# -------------------------------------------------------------------------
def test_case_2_partial_skill_alignment():
    resume = """
    Junior Developer
    Skills: HTML, CSS, JavaScript, Basic Python, Git.
    Experience: 1 year building front-end web pages and basic utility scripts.
    """
    job = """
    Full Stack Cloud Architect
    Required Skills: Python, AWS, Kubernetes, Terraform, Docker, Microservices, React.
    5+ years experience designing cloud-native distributed backends.
    """
    result = analyze_resume_and_job(resume, job)

    assert result["status"] == "success"
    matched_names = {s.lower() for s in result["matched_skills"]}
    missing_names = {s.lower() for s in result["missing_skills"]}

    assert "python" in matched_names or "javascript" in matched_names
    assert "aws" in missing_names or "kubernetes" in missing_names or "terraform" in missing_names
    assert result["experience_analysis"]["meets_experience_requirement"] is False
    assert len(result["recommendations"]) > 0


# -------------------------------------------------------------------------
# Case 3: Little Relevant Skill Evidence
# -------------------------------------------------------------------------
def test_case_3_little_relevant_skill_evidence():
    resume = """
    Chef & Culinary Specialist
    10 years experience managing kitchen staff, food inventory, knife handling,
    recipe formulation, restaurant operations, and HACCP food safety standards.
    """
    job = """
    Principal Embedded Systems Firmware Engineer
    Requirements:
    - C++, C, RTOS, ARM Cortex, Firmware, Microcontrollers, SPI, I2C, CAN bus
    - 7+ years of embedded firmware development
    """
    result = analyze_resume_and_job(resume, job)

    assert result["status"] == "success"
    assert result["predicted_class"] in ["Low Fit", "No Fit"] or result["skill_coverage"] < 35.0
    assert len(result["missing_skills"]) > 0
    # System prioritizes missing skills in recommendations
    assert any("skill" in rec["category"].lower() or "critical" in rec["category"].lower() for rec in result["recommendations"])


# -------------------------------------------------------------------------
# Case 4: Missing Employment Experience
# -------------------------------------------------------------------------
def test_case_4_missing_employment_experience():
    resume = """
    Recent Computer Science Graduate
    Skills: Python, Java, Data Structures, Algorithms, Git, Linux.
    Coursework: Operating Systems, Database Systems, Computer Networks.
    """
    job = """
    Senior Software Engineer
    Requirements:
    - 6+ years of experience in software engineering.
    - Python, Java, Linux.
    """
    result = analyze_resume_and_job(resume, job)

    assert result["status"] == "success"
    assert result["experience_analysis"]["resume_years_exp"] == 0.0
    assert result["experience_analysis"]["job_required_years"] == 6.0
    assert result["experience_analysis"]["experience_gap_years"] == -6.0
    assert result["experience_analysis"]["meets_experience_requirement"] is False
    # Recommendations should include experience guidance
    assert any("experience" in r["category"].lower() for r in result["recommendations"])


# -------------------------------------------------------------------------
# Case 5: Technical Skills Preservation
# -------------------------------------------------------------------------
def test_case_5_technical_skills_preservation():
    resume = """
    Full-Stack .NET & Systems Engineer
    Proficient in C++, C#, .NET, Node.js, Python, SQL, and Docker.
    Built enterprise microservices using ASP.NET Core and Node.js with SQL Server.
    """
    job = """
    Looking for a developer skilled in:
    - C++
    - C#
    - .NET
    - Node.js
    - Python
    - SQL
    - Docker
    """
    result = analyze_resume_and_job(resume, job)

    assert result["status"] == "success"
    matched = {s.lower() for s in result["matched_skills"]}
    for expected in ["c++", "c#", ".net", "node.js", "python", "sql", "docker"]:
        assert expected in matched, f"Expected '{expected}' to be preserved and matched"


# -------------------------------------------------------------------------
# Case 6: Empty or Corrupted Resume
# -------------------------------------------------------------------------
def test_case_6_empty_or_corrupted_resume():
    # 6a. Empty text
    res_empty = analyze_resume_and_job("", "Looking for a Python developer with 2 years experience.")
    assert res_empty["status"] == "empty"
    assert "empty" in res_empty["error_message"].lower()

    # Whitespace only
    res_whitespace = analyze_resume_and_job("   \n\t   ", "Looking for a Python developer.")
    assert res_whitespace["status"] == "empty"

    # 6b. Corrupted PDF byte stream
    corrupt_bytes = b"NOT_A_REAL_PDF_HEADER_JUST_GARBAGE_BYTES_12345"
    parsed_corrupt = parse_resume(corrupt_bytes, filename="broken.pdf")
    assert parsed_corrupt["status"] in ["empty", "error"]


# -------------------------------------------------------------------------
# Case 7: Unsupported File Type
# -------------------------------------------------------------------------
def test_case_7_unsupported_file_type():
    unsupported_data = b"BINARY_DATA"
    parsed_exe = parse_resume(unsupported_data, filename="resume.exe")
    assert parsed_exe["status"] == "error"
    assert "Unsupported file format" in parsed_exe["error_message"]

    parsed_png = parse_resume(unsupported_data, filename="portfolio.png")
    assert parsed_png["status"] == "error"
    assert "Unsupported file format" in parsed_png["error_message"]


# -------------------------------------------------------------------------
# Case 8: Empty Job Description
# -------------------------------------------------------------------------
def test_case_8_empty_job_description():
    res_empty_job = analyze_resume_and_job(
        "Experienced Python and SQL developer with 4 years experience.",
        ""
    )
    assert res_empty_job["status"] == "error"
    assert "empty" in res_empty_job["error_message"].lower()

    res_whitespace_job = analyze_resume_and_job(
        "Experienced Python developer.",
        "   \n\t  "
    )
    assert res_whitespace_job["status"] == "error"


# -------------------------------------------------------------------------
# Case 9: Long Job Description (>10,000 characters)
# -------------------------------------------------------------------------
def test_case_9_long_job_description():
    resume = "Senior Python engineer with 5 years experience in machine learning, PyTorch, Docker, and SQL."

    # Construct a massive 15,000 character job description
    long_job = (
        "Enterprise Machine Learning Platform Engineer Job Opening\n"
        "About the Company: " + ("We are a global enterprise innovating modern technology solutions. " * 150) +
        "\nDetailed Role and Responsibilities:\n"
        "Requirements:\n"
        "- 4+ years of professional experience in Python, PyTorch, Docker, SQL, Kubernetes, and AWS.\n"
        "Benefits: " + ("Comprehensive healthcare, dental, retirement savings 401k match, professional development. " * 80)
    )
    assert len(long_job) > 10000

    # System must process without crash, memory error, or excessive latency
    result = analyze_resume_and_job(resume, long_job)
    assert result["status"] == "success"
    assert "predicted_class" in result
    assert result["experience_analysis"]["job_required_years"] == 4.0
    matched_names = {s.lower() for s in result["matched_skills"]}
    assert "python" in matched_names


# -------------------------------------------------------------------------
# Case 10: Scanned PDF Without Extractable Text
# -------------------------------------------------------------------------
def test_case_10_scanned_pdf_without_extractable_text():
    # Generate an in-memory PDF that contains no text layer
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)  # Standard Letter page
    page.draw_rect(pymupdf.Rect(50, 50, 550, 700), color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = parse_resume(pdf_bytes, filename="scanned_resume.pdf")
    assert parsed["status"] == "scanned_pdf"
    assert "scanned" in parsed["error_message"].lower()
    assert parsed["metadata"]["is_scanned"] is True
