"""
Practical Project Recommender Module.
Generates concrete, actionable hands-on mini-projects for technical skill gaps.
Enforces strict rules:
- Projects are recommendations to build demonstrable portfolio evidence,
  NEVER claims that the candidate has already built them.
- Does NOT automatically add projects to the candidate's resume.
- Provides specific architectural guidelines and deliverables.
"""

from typing import Dict, List, Any, Optional

CURATED_PROJECT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "docker": {
        "title": "Multi-Service Containerization Pipeline",
        "description": "Containerize an existing Python Flask/FastAPI backend with a PostgreSQL database using Docker and Docker Compose.",
        "deliverables": [
            "Multi-stage Dockerfile optimizing image layer size and security",
            "docker-compose.yml orchestrating app, database, and volume persistence",
            "Local environment health checks and container networking verification"
        ],
        "estimated_hours": 6,
        "demonstrable_skills": ["Docker", "Containerization", "Docker Compose", "Linux Environment"]
    },
    "kubernetes": {
        "title": "Local Microservice Cluster Deployment",
        "description": "Deploy a stateless REST service onto a local Minikube or Kind Kubernetes cluster with automated replica scaling.",
        "deliverables": [
            "Kubernetes Deployment manifests with CPU/memory resource limits",
            "ClusterIP Service and Ingress routing rules",
            "ConfigMap and Secret resource injection"
        ],
        "estimated_hours": 8,
        "demonstrable_skills": ["Kubernetes", "Microservices", "Cluster Architecture", "DevOps"]
    },
    "sql": {
        "title": "Relational Schema Design & Query Performance Benchmark",
        "description": "Design an indexed PostgreSQL relational schema for an e-commerce or job-matching domain, comparing unindexed vs indexed query plans.",
        "deliverables": [
            "Normalized schema (3NF) with primary keys, foreign keys, and check constraints",
            "Complex aggregation queries with Window Functions and multi-table JOINs",
            "EXPLAIN ANALYZE execution plan benchmarks demonstrating index speedup"
        ],
        "estimated_hours": 6,
        "demonstrable_skills": ["SQL", "PostgreSQL", "Database Indexing", "Query Optimization"]
    },
    "aws": {
        "title": "Cloud-Native Container Deployment with Health Monitoring",
        "description": "Deploy a containerized REST API to AWS using Elastic Container Service (ECS) or Elastic Beanstalk with IAM role security.",
        "deliverables": [
            "IAM role configuration adhering to the principle of least privilege",
            "S3 bucket integration for secure file storage",
            "CloudWatch metric alarms monitoring application latency and uptime"
        ],
        "estimated_hours": 10,
        "demonstrable_skills": ["AWS", "Cloud Computing", "IAM Security", "CloudWatch Monitoring"]
    },
    "ci/cd": {
        "title": "Automated GitHub Actions CI/CD Testing Pipeline",
        "description": "Configure an automated continuous integration pipeline that runs Pytest test suites, flake8 linting, and Docker image builds on every pull request.",
        "deliverables": [
            ".github/workflows/ci.yml with caching for Python dependencies",
            "Automated test coverage reporting and code style enforcement",
            "Container build and push to container registry on main branch merge"
        ],
        "estimated_hours": 5,
        "demonstrable_skills": ["CI/CD", "GitHub Actions", "Automated Testing", "DevOps"]
    },
    "scikit-learn": {
        "title": "End-to-End Supervised ML Pipeline with Leakage-Free CV",
        "description": "Develop a reproducible machine learning pipeline using scikit-learn Pipelines, ColumnTransformer, and GroupKFold cross-validation.",
        "deliverables": [
            "Isolated fold preprocessing with StandardScaler and OneHotEncoder",
            "Macro F1 and Precision-Recall curve evaluation across 3 baseline models",
            "Model serialization with joblib and automated unit tests"
        ],
        "estimated_hours": 8,
        "demonstrable_skills": ["Scikit-learn", "Machine Learning", "Cross-Validation", "Data Preprocessing"]
    },
    "pytorch": {
        "title": "Deep Learning Vision/NLP Classifier with PyTorch Lightning",
        "description": "Build a PyTorch deep learning classifier implementing a custom Dataset, DataLoader batching, and GPU training acceleration.",
        "deliverables": [
            "Custom PyTorch Dataset class with data augmentation transforms",
            "Modular torch.nn.Module architecture with Dropout and BatchNorm layers",
            "Training loop with early stopping, learning rate scheduling, and validation logging"
        ],
        "estimated_hours": 12,
        "demonstrable_skills": ["PyTorch", "Deep Learning", "Neural Networks", "GPU Training"]
    },
    "react": {
        "title": "Interactive Analytics Dashboard SPA",
        "description": "Build a responsive React single-page application connecting to a REST API, featuring interactive charts and state management.",
        "deliverables": [
            "Functional components using React hooks (useState, useEffect, useMemo)",
            "Client-side routing and responsive layout",
            "Chart.js or Plotly integration for real-time metric visualization"
        ],
        "estimated_hours": 8,
        "demonstrable_skills": ["React", "JavaScript", "Front-End", "API Integration"]
    },
    "spark": {
        "title": "Distributed PySpark Batch Transformation Pipeline",
        "description": "Build a standalone PySpark batch processing pipeline that ingests multi-partition datasets, applies Window aggregations and broadcast joins, and writes partitioned Parquet outputs.",
        "deliverables": [
            "Configured SparkSession with optimized driver and executor resource allocations",
            "Columnar transformations, null handling, and rolling Window aggregations",
            "BroadcastHashJoin execution benchmarks and partitioned Parquet storage"
        ],
        "estimated_hours": 8,
        "demonstrable_skills": ["Apache Spark", "PySpark", "Big Data", "Distributed Computing"]
    },
    "communication": {
        "title": "Technical Project Presentation & Architecture Walkthrough",
        "description": "Prepare and deliver a structured 10-minute technical slide presentation and recorded architectural walkthrough explaining project design choices, trade-offs, and failure recovery.",
        "deliverables": [
            "Structured slide deck covering Problem, Architecture, Trade-Offs, and Results",
            "Recorded 5-minute technical presentation delivered using the PREP framework",
            "Executive 1-page project summary written for non-technical stakeholders"
        ],
        "estimated_hours": 4,
        "demonstrable_skills": ["Technical Communication", "Stakeholder Presentation", "PREP Framework", "Documentation"]
    },
    "excel": {
        "title": "Analytical Performance & Financial Modeling Workbook",
        "description": "Construct a structured analytical spreadsheet model featuring dynamic formulas, PivotTables, scenario analysis, and executive KPI summary charts.",
        "deliverables": [
            "Dynamic data model using INDEX/MATCH, XLOOKUP, and nested logical formulas",
            "Interactive PivotTable and PivotChart dashboard with slicers and conditional formatting",
            "Automated summary worksheet evaluating scenario sensitivities and variance"
        ],
        "estimated_hours": 5,
        "demonstrable_skills": ["Microsoft Excel", "Spreadsheet Modeling", "Data Analysis", "PivotTables"]
    },
    "project management": {
        "title": "Agile Sprint Backlog & Delivery Workflow Configuration",
        "description": "Decompose a full-stack product initiative into an Agile sprint backlog with epics, user stories, acceptance criteria, and estimation story points.",
        "deliverables": [
            "Product backlog breakdown containing 10 user stories with Gherkin acceptance criteria",
            "Configured sprint board with WIP limits, estimation points, and definition of done",
            "Sprint retrospective summary analyzing velocity bottlenecks and mitigation steps"
        ],
        "estimated_hours": 4,
        "demonstrable_skills": ["Agile Methodologies", "Jira", "Sprint Planning", "Project Management"]
    },
    "typescript": {
        "title": "Type-Safe REST Client & Domain Model Migration",
        "description": "Migrate an untyped JavaScript API utility module to TypeScript, configuring strict compiler flags, custom generic interfaces, and exhaustive discriminated unions.",
        "deliverables": [
            "Strict tsconfig.json configuration with zeroImplicitAny",
            "Generic API client module with typed request/response models",
            "Automated test suite passing tsc type checks without compiler warnings"
        ],
        "estimated_hours": 6,
        "demonstrable_skills": ["TypeScript", "Static Typing", "Generics", "Type Systems"]
    },
    "visio": {
        "title": "Multi-Tier System Architecture & ER Diagram Portfolio",
        "description": "Author a comprehensive technical documentation pack in Visio featuring a 3-tier C4 system architecture diagram and a normalized database Entity-Relationship schema.",
        "deliverables": [
            "C4 Container diagram illustrating decoupled services, caches, and storage tiers",
            "Normalized database ER diagram in Crow's Foot notation with primary/foreign keys",
            "High-resolution vector SVG export pack embedded in a technical system RFC"
        ],
        "estimated_hours": 4,
        "demonstrable_skills": ["Visio", "Architecture Diagramming", "ER Diagrams", "C4 Model"]
    },
    "focus": {
        "title": "Deliberate Engineering Focus & Sprint Execution Log",
        "description": "Implement a 10-day structured deep work framework tracking time-boxed engineering intervals, interruption sources, and completed feature deliverables.",
        "deliverables": [
            "10-day attention audit logging focus intervals and context-switching mitigations",
            "Decomposed sprint backlog with single-focus atomic task definitions",
            "Reflective summary analyzing focus gains on code quality and sprint velocity"
        ],
        "estimated_hours": 3,
        "demonstrable_skills": ["Focus", "Deep Work", "Time Management", "Execution Discipline"]
    },
    "pc skills": {
        "title": "Developer Environment Automation & Shortcut Toolkit",
        "description": "Configure an optimized developer workstation setup including custom shell aliases, directory structure templates, and automated workspace backup scripts.",
        "deliverables": [
            "Custom shell profile with 10+ developer aliases for rapid file and process navigation",
            "Standardized workspace directory hierarchy template with permissions setup",
            "Automated backup shell script with timestamping and archive integrity verification"
        ],
        "estimated_hours": 3,
        "demonstrable_skills": ["PC Skills", "Command Line", "Operating Systems", "Shell Scripting"]
    },
    "analytical problem-solving": {
        "title": "Technical Root-Cause Analysis & Incident Postmortem",
        "description": "Author a rigorous, blameless postmortem document dissecting a complex technical software failure, identifying root causes, and designing permanent regression test guards.",
        "deliverables": [
            "5 Whys root-cause analysis document tracing symptom to architectural deficiency",
            "Quantitative log analysis and hypothesis validation notes",
            "Defensive remediation plan including automated regression test specifications"
        ],
        "estimated_hours": 4,
        "demonstrable_skills": ["Analytical Problem Solving", "Root Cause Analysis", "Postmortems", "Trade-Off Analysis"]
    },
    "power bi": {
        "title": "Executive Business Intelligence Performance Dashboard",
        "description": "Build an interactive Power BI dashboard modeling key operational metrics, implementing dynamic DAX measures and dimensional data relationships.",
        "deliverables": [
            "Star-schema relational model connecting fact tables and dimension tables",
            "Calculated DAX measures for period-over-period variance and moving averages",
            "Interactive dashboard with visual slicers, drill-through paths, and KPI indicators"
        ],
        "estimated_hours": 6,
        "demonstrable_skills": ["Power BI", "DAX", "Data Modeling", "Business Intelligence"]
    }
}


def recommend_project_for_skill(skill_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a curated project recommendation for a given skill gap.
    Returns None if no specific project is mapped.
    """
    if not skill_name or not isinstance(skill_name, str):
        return None

    norm = skill_name.lower().strip()
    if norm in CURATED_PROJECT_TEMPLATES:
        return dict(CURATED_PROJECT_TEMPLATES[norm])

    for key, template in CURATED_PROJECT_TEMPLATES.items():
        if key in norm or norm in key:
            return dict(template)

    # Common aliases
    if "database" in norm or "postgres" in norm or "mysql" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["sql"])
    if "k8s" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["kubernetes"])
    if "container" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["docker"])
    if "cloud" in norm or "azure" in norm or "gcp" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["aws"])
    if "pyspark" in norm or "spark" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["spark"])
    if "presentation" in norm or "speech" in norm or "speaking" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["communication"])
    if "spreadsheet" in norm or "sheets" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["excel"])
    if "agile" in norm or "scrum" in norm or "jira" in norm or "trello" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["project management"])
    if "ts" == norm or "typescript" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["typescript"])
    if "visio" in norm or "diagram" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["visio"])
    if "focus" in norm or "attention to detail" in norm or "discipline" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["focus"])
    if "pc skills" in norm or "computer skills" in norm or "digital literacy" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["pc skills"])
    if "analytical" in norm or "problem solving" in norm or "problem-solving" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["analytical problem-solving"])
    if "power bi" in norm or "powerbi" in norm or "pbi" in norm or "tableau" in norm:
        return dict(CURATED_PROJECT_TEMPLATES["power bi"])

    return None
