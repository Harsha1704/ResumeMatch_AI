"""
Skill Extraction Evaluation Test Suite (Requirement 6.1).
Evaluates SkillEngine on a representative benchmark dataset of 30 real-world
resume snippets and job description excerpts.
Measures Precision, Recall, and F1-score with detailed false positive / false negative reporting.
"""

import pytest
from typing import Dict, List, Set, Tuple
from src.preprocessing.skill_extractor import (
    SkillEngine,
    get_canonical_skill_name,
    get_canonical_taxonomy_category,
    build_skill_evidence_record,
    FILTERED_GENERIC_SKILLS
)


# Benchmark evaluation dataset with 30 diverse test samples
EVALUATION_SAMPLES: List[Dict] = [
    # 1-5: Programming Languages & Core Stacks
    {
        "id": "sample_01",
        "domain": "Backend Python",
        "text": "Senior Python developer with extensive experience building REST APIs with Flask and PostgreSQL databases. Proficient in automated testing with pytest and Git version control.",
        "expected_skills": {"python", "flask", "postgresql", "pytest", "git", "rest api"}
    },
    {
        "id": "sample_02",
        "domain": "Systems & C++",
        "text": "Systems programmer experienced with C++ and C programming, Linux kernel debugging, multithreading, and network protocols using TCP/IP.",
        "expected_skills": {"c++", "c", "linux", "tcp/ip"}
    },
    {
        "id": "sample_03",
        "domain": "Full-Stack JavaScript/TypeScript",
        "text": "Full-stack engineer proficient in TypeScript, JavaScript, React, Node.js, and Express.js with MongoDB persistence.",
        "expected_skills": {"typescript", "javascript", "react", "node.js", "express.js", "mongodb"}
    },
    {
        "id": "sample_04",
        "domain": "Java Enterprise",
        "text": "Backend Java engineer with 4 years building microservices using Spring Boot, MySQL, and Docker containers.",
        "expected_skills": {"java", "spring boot", "mysql", "docker", "microservices"}
    },
    {
        "id": "sample_05",
        "domain": "Golang & Cloud",
        "text": "Cloud software developer implementing high-concurrency microservices in Go with Kubernetes and Redis caching.",
        "expected_skills": {"go", "kubernetes", "redis", "microservices"}
    },

    # 6-10: Machine Learning & Computer Vision
    {
        "id": "sample_06",
        "domain": "Machine Learning Core",
        "text": "Machine learning engineer experienced in Scikit-Learn, PyTorch, Pandas, and NumPy for predictive modeling and cross-validation.",
        "expected_skills": {"machine learning", "scikit-learn", "pytorch", "pandas", "numpy"}
    },
    {
        "id": "sample_07",
        "domain": "Computer Vision",
        "text": "Developed computer vision pipelines using OpenCV and MediaPipe for real-time facial landmark tracking and image processing.",
        "expected_skills": {"computer vision", "opencv", "mediapipe"}
    },
    {
        "id": "sample_08",
        "domain": "Deep Learning & NLP",
        "text": "Deep learning practitioner with TensorFlow and natural language processing experience building text classification models.",
        "expected_skills": {"deep learning", "tensorflow", "natural language processing"}
    },
    {
        "id": "sample_09",
        "domain": "Data Analytics & SQL",
        "text": "Data analyst skilled in SQL, Excel, and Tableau designing analytical dashboards and running aggregation queries.",
        "expected_skills": {"sql", "excel", "tableau"}
    },
    {
        "id": "sample_10",
        "domain": "Big Data Engineering",
        "text": "Data engineer building distributed ETL pipelines using Apache Spark, Hadoop, and Apache Kafka for event streaming.",
        "expected_skills": {"apache spark", "hadoop", "kafka"}
    },

    # 11-15: Cloud & DevOps
    {
        "id": "sample_11",
        "domain": "Cloud Infrastructure",
        "text": "Cloud architect managing AWS infrastructure, EC2 instances, S3 buckets, and Terraform infrastructure as code.",
        "expected_skills": {"amazon web services", "terraform"}
    },
    {
        "id": "sample_12",
        "domain": "CI/CD & DevOps",
        "text": "DevOps engineer configuring automated CI/CD pipelines, Docker container images, and Jenkins builds for automated deployments.",
        "expected_skills": {"ci/cd", "docker", "jenkins"}
    },
    {
        "id": "sample_13",
        "domain": "Container Orchestration",
        "text": "Site reliability engineer deploying microservices to Kubernetes clusters with Prometheus monitoring and Grafana visualization.",
        "expected_skills": {"kubernetes", "microservices"}
    },
    {
        "id": "sample_14",
        "domain": "Azure Cloud",
        "text": "Administering Microsoft Azure cloud environments, virtual networks, and CI/CD deployment gates.",
        "expected_skills": {"microsoft azure", "ci/cd"}
    },
    {
        "id": "sample_15",
        "domain": "Linux Systems",
        "text": "Linux system administrator managing Bash shell scripting, systemd services, and Nginx reverse proxy configuration.",
        "expected_skills": {"linux", "bash", "nginx"}
    },

    # 16-20: Modern Frontend & APIs
    {
        "id": "sample_16",
        "domain": "Frontend UI",
        "text": "Frontend developer skilled in React, HTML, CSS, and Tailwind CSS designing responsive web layouts.",
        "expected_skills": {"react", "html", "css", "tailwind css"}
    },
    {
        "id": "sample_17",
        "domain": "API Development",
        "text": "Developed high-throughput REST APIs using FastAPI and Python, integrating with PostgreSQL and Redis.",
        "expected_skills": {"rest api", "fastapi", "python", "postgresql", "redis"}
    },
    {
        "id": "sample_18",
        "domain": "Vue Frontend",
        "text": "Built client web applications using Vue.js, JavaScript, and Bootstrap styling connected to backend APIs.",
        "expected_skills": {"vue.js", "javascript", "bootstrap"}
    },
    {
        "id": "sample_19",
        "domain": "Angular Enterprise",
        "text": "Developed modular single-page applications using Angular and TypeScript adhering to clean architecture.",
        "expected_skills": {"angular", "typescript"}
    },
    {
        "id": "sample_20",
        "domain": "C# .NET Backend",
        "text": "Software engineer developing enterprise services with C# and .NET Core utilizing SQL Server database.",
        "expected_skills": {"c#", ".net", "sql server"}
    },

    # 21-25: Professional, Methodologies & Aliases
    {
        "id": "sample_21",
        "domain": "Agile & Testing",
        "text": "Collaborated in Agile Scrum sprints, performing peer code reviews and authoring unit testing suites.",
        "expected_skills": {"agile", "scrum", "code review", "unit testing"}
    },
    {
        "id": "sample_22",
        "domain": "Aliases: Sklearn & K8s",
        "text": "Model training using sklearn and deployment to k8s clusters running in production cloud environments.",
        "expected_skills": {"scikit-learn", "kubernetes"}
    },
    {
        "id": "sample_23",
        "domain": "Aliases: Postgres & Mongo",
        "text": "Backend service persisting relational entities in Postgres and unstructured document logs in Mongo.",
        "expected_skills": {"postgresql", "mongodb"}
    },
    {
        "id": "sample_24",
        "domain": "Database SQL & PL/SQL",
        "text": "Database engineer writing advanced SQL queries, stored procedures in PL/SQL, and optimizing execution plans.",
        "expected_skills": {"sql", "pl/sql"}
    },
    {
        "id": "sample_25",
        "domain": "Collaboration & Soft Skills",
        "text": "Demonstrated excellent written communication skills, problem solving, and effective teamwork across cross-functional groups.",
        "expected_skills": {"communication", "problem solving", "teamwork"}
    },

    # 26-30: Negative Controls & Noise Suppression (MUST NOT EXTRACT FALSE POSITIVES)
    {
        "id": "sample_26",
        "domain": "Negative Control: Travel & Logistics",
        "text": "Willing to travel up to 25% for client site visits. Coordinate international travel and flight scheduling for executive team.",
        "expected_skills": set()  # "travel" must not be extracted
    },
    {
        "id": "sample_27",
        "domain": "Negative Control: Video Calls & Social",
        "text": "Conduct regular meetings on Zoom and communicate company updates via LinkedIn posts and internal newsletters.",
        "expected_skills": set()  # "zoom", "linkedin" must not be extracted
    },
    {
        "id": "sample_28",
        "domain": "Negative Control: Corporate Jargon",
        "text": "Responsible for candidate screening, corporate innovation initiatives, employee training programs, and delivering learning solutions across organizations.",
        "expected_skills": set()  # "screening", "innovation", "training", "learning solutions" must NOT be extracted
    },
    {
        "id": "sample_29",
        "domain": "Negative Control: Generic English Verbs",
        "text": "Must go above and beyond to provide customer satisfaction. We will go through the requirements with the team.",
        "expected_skills": set()  # verb "go" must not be extracted
    },
    {
        "id": "sample_30",
        "domain": "Negative Control: Common English C & R",
        "text": "Section c of the agreement requires research and reporting. See copyright section c for details.",
        "expected_skills": set()  # letter "c" or standalone "research" must NOT be extracted
    }
]


def test_01_skill_extraction_benchmark_evaluation():
    """
    Runs full benchmark evaluation across 30 real-world samples.
    Asserts Precision >= 85%, Recall >= 80%, and Macro F1 >= 80%.
    """
    engine = SkillEngine()

    total_tp = 0
    total_fp = 0
    total_fn = 0

    all_fp_details = []
    all_fn_details = []

    for sample in EVALUATION_SAMPLES:
        extracted = engine.extract_skills(sample["text"])
        expected = sample["expected_skills"]

        tp = len(extracted.intersection(expected))
        fp = len(extracted - expected)
        fn = len(expected - extracted)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        if fp > 0:
            all_fp_details.append((sample["id"], sample["domain"], extracted - expected))
        if fn > 0:
            all_fn_details.append((sample["id"], sample["domain"], expected - extracted))

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("\n" + "=" * 60)
    print("SKILL EXTRACTION EVALUATION REPORT (30 Real-World Benchmark Cases)")
    print("=" * 60)
    print(f"True Positives:  {total_tp}")
    print(f"False Positives: {total_fp}")
    print(f"False Negatives: {total_fn}")
    print(f"Precision:       {precision * 100:.2f}%")
    print(f"Recall:          {recall * 100:.2f}%")
    print(f"Macro F1 Score:  {f1 * 100:.2f}%")
    print("=" * 60)

    if all_fp_details:
        print("False Positives Breakdown:")
        for sid, dom, fps in all_fp_details:
            print(f"  [{sid}] {dom}: {fps}")

    if all_fn_details:
        print("False Negatives Breakdown:")
        for sid, dom, fns in all_fn_details:
            print(f"  [{sid}] {dom}: {fns}")

    assert precision >= 0.85, f"Skill extraction precision {precision:.3f} below 0.85 threshold"
    assert recall >= 0.80, f"Skill extraction recall {recall:.3f} below 0.80 threshold"
    assert f1 >= 0.80, f"Skill extraction F1 score {f1:.3f} below 0.80 threshold"


def test_02_negative_controls_zero_false_positives():
    """
    Verifies that negative control prose containing 'travel', 'zoom', 'linkedin',
    'training', 'innovation', 'screening', 'learning solutions', 'go', 'c' produce zero false skills.
    """
    engine = SkillEngine()
    negative_samples = EVALUATION_SAMPLES[25:30]
    for s in negative_samples:
        extracted = engine.extract_skills(s["text"])
        assert len(extracted) == 0, f"Negative sample '{s['id']}' extracted false positive: {extracted}"


def test_03_evidence_traceability_structure():
    """
    Verifies that build_skill_evidence_record populates all 6 required fields:
    canonical_skill_name, taxonomy_category, evidence_source, supporting_sentence,
    evidence_strength, detection_method.
    """
    projects = [
        {
            "title": "Brain Tumor Classification",
            "technologies": ["Python", "TensorFlow", "OpenCV"],
            "description": "Implemented convolutional neural network achieving reliable image classification."
        }
    ]
    resume = "Candidate proficient in Python and SQL. Built machine learning models."

    rec_proj = build_skill_evidence_record("tensorflow", resume_text=resume, projects=projects)
    assert rec_proj["canonical_skill_name"] == "TensorFlow"
    assert rec_proj["taxonomy_category"] == "Machine Learning & AI"
    assert "Brain Tumor Classification" in rec_proj["evidence_source"]
    assert rec_proj["evidence_strength"] == "Demonstrated in project"
    assert rec_proj["detection_method"] == "project_entity_extraction"

    rec_gap = build_skill_evidence_record("docker", is_gap=True)
    assert rec_gap["canonical_skill_name"] == "Docker"
    assert rec_gap["taxonomy_category"] == "Cloud & DevOps"
    assert rec_gap["evidence_strength"] == "Not evidenced in resume"
    assert rec_gap["evidence_source"] == "Target Job Description"



def test_resume_analyzer_suppresses_generic_business_jargon():
    """Only explicit technical competencies should survive generic resume prose."""
    engine = SkillEngine()
    text = (
        "Responsible for customer satisfaction, team management, reporting, scheduling, "
        "operations, support, quality delivery, learning solutions, travel, Zoom, LinkedIn, "
        "and cloud environments. Demonstrated Python and SQL query optimization."
    )
    extracted = engine.extract_skills(text)
    assert {"python", "sql"}.issubset(extracted)
    for generic in {
        "customer satisfaction", "team", "management", "reporting", "scheduling",
        "operations", "support", "quality", "learning solutions", "travel",
        "zoom", "linkedin", "cloud environments"
    }:
        assert generic not in extracted
