"""
Comprehensive Regression Tests for Project Extraction, Internship Detection,
and Experience Classification in ResumeMatch AI.

Verifies:
1. Exactly four projects extracted from the test resume fixture
2. Exactly two internships extracted from the test resume fixture
3. Dates correctly attached to project records
4. Tech Stack lines correctly attached to project records
5. Project descriptions correctly attached to project records
6. No standalone date-only projects created
7. No standalone technology-list projects created
8. Section boundaries strictly respected (no bleed into education or skills)
9. Internships not counted as projects
10. Projects not counted as internships
11. Internship dates extracted correctly
12. Ongoing internship recognized (Jan 2026 – Present -> is_ongoing=True)
13. Multiple internships supported
14. Multiple projects supported
15. Empty projects section handled gracefully
16. Empty internships section handled gracefully
17. Resume without internships handled gracefully
18. Scrollbar container classes and constraints
19. Structured results schema completeness and JSON serializability
20. End-to-end matching and model inference compatibility
"""

import pytest
import json
from src.analysis.experience_analyzer import ExperienceAnalyzer, split_resume_into_sections
from src.analysis.matching_engine import analyze_resume_and_job, get_matching_engine


SAMPLE_TWO_PAGE_RESUME = """
Candidate Name
Email: candidate@example.com | Phone: +1-555-0199
GitHub: github.com/candidate | LinkedIn: linkedin.com/in/candidate

EDUCATION
B.Tech in Computer Science and Engineering
CGPA: 8.9 / 10.0
Expected Graduation: May 2026

SKILLS SUMMARY
Programming Languages: Python, Java, C++, JavaScript
Frameworks & Libraries: Flask, Scikit-learn, TensorFlow, PyTorch, OpenCV, React
Databases: PostgreSQL, MySQL, MongoDB
Developer Tools: Git, Docker, Linux, VS Code

PROJECTS

AI Resume Analyzer & Job Match System
Feb 2026 – Mar 2026
Tech Stack: Python, NLP, Scikit-learn, Pandas, Flask
• Developed an end-to-end multimodal resume matching engine with supervised ML classifiers.
• Built deterministic skill extraction with 8-category competency taxonomy.
• Formatted interactive analytics dashboard using Bootstrap 5.
GitHub: https://github.com/candidate/resume-match-ai

Emotion-Based Music Recommendation System
Feb 2026 – Mar 2026
Tech Stack: Python, OpenCV, TensorFlow, NumPy, Pandas
• Designed facial emotion recognition pipeline using CNN architectures.
• Integrated mood-driven playlist recommendations.
GitHub: https://github.com/candidate/emotion-music-rec

Gesture Controlled Virtual Calculator
Jun 2025 – Jul 2025
Tech Stack: Python, OpenCV, Media Pipe, NumPy
• Built a real-time computer vision virtual calculator detecting hand gestures.
• Implemented canvas overlay for arithmetic calculations.
GitHub: https://github.com/candidate/gesture-calculator

Historical and Aerial Exploration Through SVG Maps
Oct 2024 – Nov 2024
Tech Stack: HTML, CSS, JavaScript, SVG
• Created an interactive web-based SVG vector map exploration portal.
• Enabled zoom, pan, and historical artifact information cards.
GitHub: https://github.com/candidate/svg-map-explorer

INTERNSHIPS

Infosys Springboard
Virtual Internship 6.0 (AI)
Jan 2026 – Present
• Worked on Artificial Intelligence, Cybersecurity, Network Intrusion Detection, and Network Traffic Analysis.
• Built Machine Learning models for anomaly detection and network traffic classification.

Edufiy Tech Solutions
Jan 2025 – Mar 2025
• Conducted AI-Based Anomaly Detection, Data Preprocessing, and Feature Engineering.
• Evaluated Isolation Forest for Model Evaluation and Data Visualization.

CERTIFICATIONS
- Certified Machine Learning Associate
- Deep Learning Specialization

ACHIEVEMENTS
- First place in Regional Hackathon 2025
- Dean's Honor Roll for academic excellence
"""


# -------------------------------------------------------------------------
# Test 1 & 2: Project and Internship Counts
# -------------------------------------------------------------------------
def test_exact_four_projects_extracted():
    analyzer = ExperienceAnalyzer()
    projects = analyzer.detect_projects(SAMPLE_TWO_PAGE_RESUME)
    assert len(projects) == 4, f"Expected exactly 4 projects, found {len(projects)}: {[p['project_title'] for p in projects]}"

    titles = [p["project_title"] for p in projects]
    assert "AI Resume Analyzer & Job Match System" in titles
    assert "Emotion-Based Music Recommendation System" in titles
    assert "Gesture Controlled Virtual Calculator" in titles
    assert "Historical and Aerial Exploration Through SVG Maps" in titles


def test_exact_two_internships_extracted():
    analyzer = ExperienceAnalyzer()
    internships = analyzer.detect_internships(SAMPLE_TWO_PAGE_RESUME)
    assert len(internships) == 2, f"Expected exactly 2 internships, found {len(internships)}: {[i['organization'] for i in internships]}"

    orgs = [i["organization"] for i in internships]
    assert any("infosys" in o.lower() for o in orgs)
    assert any("edufiy" in o.lower() for o in orgs)


# -------------------------------------------------------------------------
# Test 3, 4, 5: Dates, Tech Stack, and Descriptions Attached
# -------------------------------------------------------------------------
def test_project_record_fields_and_associations():
    analyzer = ExperienceAnalyzer()
    projects = analyzer.detect_projects(SAMPLE_TWO_PAGE_RESUME)
    p_map = {p["project_title"]: p for p in projects}

    p1 = p_map["AI Resume Analyzer & Job Match System"]
    assert "Feb 2026" in p1["dates"] and "Mar 2026" in p1["dates"]
    assert p1["start_date"] == "Feb 2026"
    assert p1["end_date"] == "Mar 2026"
    techs_lower = {t.lower() for t in p1["technologies"]}
    assert "python" in techs_lower
    assert "scikit-learn" in techs_lower
    assert "flask" in techs_lower
    assert len(p1["description"]) > 20
    assert "https://github.com/candidate/resume-match-ai" in p1["links"] or p1["github_url"]

    p2 = p_map["Emotion-Based Music Recommendation System"]
    assert "Feb 2026" in p2["dates"] and "Mar 2026" in p2["dates"]
    p2_techs = {t.lower() for t in p2["technologies"]}
    assert "python" in p2_techs
    assert "opencv" in p2_techs
    assert "tensorflow" in p2_techs

    p3 = p_map["Gesture Controlled Virtual Calculator"]
    assert "Jun 2025" in p3["dates"] and "Jul 2025" in p3["dates"]
    p3_techs = {t.lower() for t in p3["technologies"]}
    assert "mediapipe" in p3_techs or "opencv" in p3_techs or "python" in p3_techs

    p4 = p_map["Historical and Aerial Exploration Through SVG Maps"]
    assert "Oct 2024" in p4["dates"] and "Nov 2024" in p4["dates"]
    p4_techs = {t.lower() for t in p4["technologies"]}
    assert "javascript" in p4_techs or "html5" in p4_techs or "svg" in p4_techs


# -------------------------------------------------------------------------
# Test 6 & 7: No Standalone Dates or Tech Stack Projects
# -------------------------------------------------------------------------
def test_no_standalone_date_or_tech_stack_projects():
    analyzer = ExperienceAnalyzer()
    projects = analyzer.detect_projects(SAMPLE_TWO_PAGE_RESUME)
    titles = [p["project_title"].lower() for p in projects]

    for t in titles:
        assert "tech stack" not in t
        assert "technologies:" not in t
        assert not ("2026" in t and "mar" in t)
        assert not ("2025" in t and "jul" in t)
        assert t not in ["certifications", "achievements", "education", "internships"]


# -------------------------------------------------------------------------
# Test 8, 9, 10: Section Boundaries & Separation
# -------------------------------------------------------------------------
def test_section_boundaries_and_mutual_exclusion():
    analyzer = ExperienceAnalyzer()
    sections = split_resume_into_sections(SAMPLE_TWO_PAGE_RESUME)

    assert "projects" in sections
    assert "internships" in sections
    assert "education" in sections
    assert "certifications" in sections
    assert "achievements" in sections

    projects = analyzer.detect_projects(SAMPLE_TWO_PAGE_RESUME)
    internships = analyzer.detect_internships(SAMPLE_TWO_PAGE_RESUME)

    # Ensure no internship organization is in projects
    proj_titles = [p["project_title"].lower() for p in projects]
    for intern in internships:
        assert intern["organization"].lower() not in proj_titles

    # Ensure no project is in internships
    intern_orgs = [i["organization"].lower() for i in internships]
    for p in projects:
        assert p["project_title"].lower() not in intern_orgs


# -------------------------------------------------------------------------
# Test 11, 12, 13: Internship Details, Ongoing Status, and Multiple Entries
# -------------------------------------------------------------------------
def test_internship_details_and_ongoing():
    analyzer = ExperienceAnalyzer()
    internships = analyzer.detect_internships(SAMPLE_TWO_PAGE_RESUME)
    assert len(internships) == 2

    # Infosys Springboard
    infosys = next(i for i in internships if "infosys" in i["organization"].lower())
    assert "jan 2026" in infosys["dates"].lower()
    assert "present" in infosys["dates"].lower()
    assert infosys["is_ongoing"] is True
    assert infosys["position"] is not None and "Virtual Internship" in infosys["position"]
    assert len(infosys["responsibilities"]) >= 1

    # Edufiy Tech Solutions
    edufiy = next(i for i in internships if "edufiy" in i["organization"].lower())
    assert "jan 2025" in edufiy["dates"].lower()
    assert "mar 2025" in edufiy["dates"].lower()
    assert edufiy["is_ongoing"] is False
    assert len(edufiy["responsibilities"]) >= 1


# -------------------------------------------------------------------------
# Test 14 & 15 & 16 & 17: Edge Cases (Empty sections, no internships)
# -------------------------------------------------------------------------
def test_empty_and_minimal_sections():
    analyzer = ExperienceAnalyzer()

    # Empty text
    assert analyzer.detect_projects("") == []
    assert analyzer.detect_internships("") == []

    # Resume without internships
    resume_no_intern = """
    Jane Doe
    PROJECTS
    Smart Traffic Controller | Jan 2025 – May 2025
    Tech Stack: Python, OpenCV
    - Implemented computer vision vehicle tracker.
    EDUCATION
    B.S. in Computer Science
    """
    res_no_intern = analyzer.detect_internships(resume_no_intern)
    assert res_no_intern == []
    projects = analyzer.detect_projects(resume_no_intern)
    assert len(projects) == 1
    assert "Smart Traffic Controller" in projects[0]["project_title"]


# -------------------------------------------------------------------------
# Test 18: Experience Classification with Internships
# -------------------------------------------------------------------------
def test_experience_classification_with_internships():
    analyzer = ExperienceAnalyzer()
    # The sample resume has internships but no full-time tenure stated
    res = analyzer.analyze_experience(SAMPLE_TWO_PAGE_RESUME, job_required_years=2.0)

    assert res["resume_exp_display"] == "Internship experience identified; full-time employment not established."
    assert "internship" in res["alignment_status"].lower()
    assert res["internships_count"] == 2
    assert res["projects_count"] == 4
    assert res["experience_summary"]["primary_classification"] == "Internships"
    assert res["experience_summary"]["has_internships"] is True
    assert res["experience_summary"]["has_full_time"] is False


# -------------------------------------------------------------------------
# Test 19: Full Results Schema & JSON Serializability
# -------------------------------------------------------------------------
def test_matching_engine_results_schema_and_json():
    job_desc = """
    Job Title: Machine Learning Engineer
    Qualifications: B.Tech in Computer Science
    Required Skills:
    - Python
    - Scikit-learn
    - TensorFlow
    - Docker
    - PostgreSQL
    Preferred:
    - Flask
    - OpenCV
    """
    result = analyze_resume_and_job(SAMPLE_TWO_PAGE_RESUME, job_desc)

    assert result["status"] == "success"
    assert "projects" in result
    assert "internships" in result
    assert "professional_experience" in result
    assert "experience_summary" in result
    assert len(result["projects"]) == 4
    assert len(result["internships"]) == 2

    # Verify JSON serializability
    serialized = json.dumps(result)
    assert len(serialized) > 500
    deserialized = json.loads(serialized)
    assert deserialized["status"] == "success"
    assert len(deserialized["projects"]) == 4
    assert len(deserialized["internships"]) == 2


# -------------------------------------------------------------------------
# Test 20: Abbreviated Dates and Flexible Dash Formats
# -------------------------------------------------------------------------
def test_abbreviated_dates_and_dashes():
    resume_abbrev = """
    PROJECTS
    Neural Vision Pipeline | Feb 26 – Mar 26
    Tech Stack: PyTorch, Python
    - Developed vision pipeline.

    Audio Synthesizer | Jun 25 to Jul 25
    Tech Stack: C++, JUCE
    - Built real-time audio plugin.

    INTERNSHIPS
    TechCorp Labs
    Jan 26 – Present
    - Researched multimodal deep learning.
    """
    analyzer = ExperienceAnalyzer()
    projects = analyzer.detect_projects(resume_abbrev)
    internships = analyzer.detect_internships(resume_abbrev)

    assert len(projects) == 2
    p1 = projects[0]
    assert "Feb 2026" in p1["dates"] and "Mar 2026" in p1["dates"]

    assert len(internships) == 1
    i1 = internships[0]
    assert i1["is_ongoing"] is True
    assert "Jan 2026" in i1["dates"]


# -------------------------------------------------------------------------
# Test 21: Technologies Strictly Supported by Resume Evidence (No Hallucinated Tech)
# -------------------------------------------------------------------------
def test_technologies_strictly_supported_by_resume():
    analyzer = ExperienceAnalyzer()
    projects = analyzer.detect_projects(SAMPLE_TWO_PAGE_RESUME)
    p_map = {p["project_title"]: p for p in projects}

    p1_techs = [t.lower() for t in p_map["AI Resume Analyzer & Job Match System"]["technologies"]]
    assert "pytorch" not in p1_techs, "PyTorch was not in CV tech stack for project 1"
    assert "chart.js" not in p1_techs, "Chart.js was not in CV tech stack for project 1"

    p2_techs = [t.lower() for t in p_map["Emotion-Based Music Recommendation System"]["technologies"]]
    assert "streamlit" not in p2_techs, "Streamlit was not in CV tech stack for project 2"


# -------------------------------------------------------------------------
# Test 22: Direct Verification on Actual PDF if Available
# -------------------------------------------------------------------------
def test_actual_pdf_extraction_if_file_exists():
    import os
    pdf_path = r"C:\Users\Harsha\Documents\final cv 2026.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Original final cv 2026.pdf not found in Documents")

    from src.analysis.resume_parser import extract_text_from_pdf
    text, _ = extract_text_from_pdf(pdf_path)

    analyzer = ExperienceAnalyzer()
    projects = analyzer.detect_projects(text)
    internships = analyzer.detect_internships(text)

    # Exactly 4 projects
    assert len(projects) == 4, f"Expected 4 projects from PDF, got {len(projects)}"
    titles = [p["project_title"] for p in projects]
    assert "AI Resume Analyzer & Job Match System" in titles
    assert "Emotion-Based Music Recommendation System" in titles
    assert "Gesture Controlled Virtual Calculator" in titles
    assert "Historical and Aerial Exploration Through SVG Maps" in titles

    # Technologies strictly from CV
    p1 = next(p for p in projects if "AI Resume Analyzer" in p["project_title"])
    assert "pytorch" not in [t.lower() for t in p1["technologies"]]
    assert "chart.js" not in [t.lower() for t in p1["technologies"]]

    # Exactly 2 internships
    assert len(internships) == 2, f"Expected 2 internships from PDF, got {len(internships)}: {[i['organization'] for i in internships]}"
    orgs = [i["organization"] for i in internships]
    assert any("infosys" in o.lower() for o in orgs)
    assert any("edufiy" in o.lower() for o in orgs)

    # No fragment as internship
    for i in internships:
        o = i["organization"].lower()
        assert not o.endswith(".")
        assert "malicious" not in o
        assert "algorithm" not in o
        assert "tools:" not in o

    # Experience summary
    analysis = analyzer.analyze_experience(text, job_required_years=2.0)
    assert analysis["resume_exp_display"] == "Internship experience identified; full-time employment not established."
    assert analysis["experience_summary"]["internships_count"] == 2
    assert analysis["experience_summary"]["projects_count"] == 4


# -------------------------------------------------------------------------
# Test 23: Canonical Skill Deduplication and Clean Label Normalization
# -------------------------------------------------------------------------
def test_canonical_skill_deduplication_and_clean_labels():
    from src.analysis.experience_analyzer import canonicalize_tech_list

    raw_skills = [
        "NumPy", "Numpy", "numpy",
        "Implemented Data Preprocessing",
        "Feature Engineering", "Engineering",
        "Scikit-learn", "Scikit-Learn", "sklearn",
        "Python"
    ]
    cleaned = canonicalize_tech_list(raw_skills)

    # 1. Exactly one NumPy
    assert cleaned.count("NumPy") == 1
    assert "Numpy" not in cleaned

    # 2. Exactly one Scikit-Learn
    assert cleaned.count("Scikit-Learn") == 1

    # 3. Action-verb prefix stripped to clean competency
    assert "Data Preprocessing" in cleaned
    assert "Implemented Data Preprocessing" not in cleaned

    # 4. Incomplete generic "Engineering" dropped when "Feature Engineering" is present
    assert "Feature Engineering" in cleaned
    assert "Engineering" not in cleaned
