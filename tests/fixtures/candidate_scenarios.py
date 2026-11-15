"""
Ten Realistic Candidate & Job Description Test Fixtures for ResumeMatch AI Quality Evaluation.
Covers:
1. Student with ML projects
2. Backend developer
3. Frontend developer
4. Data analyst
5. Data engineer
6. Candidate with internships but no full-time employment
7. Experienced professional
8. Candidate with limited project evidence
9. Resume with missing education details
10. JD with ambiguous requirements
"""

from typing import Dict, Any

CANDIDATE_SCENARIOS: Dict[str, Dict[str, Any]] = {
    # 1. Student with ML projects
    "scenario_1_ml_student": {
        "candidate_id": "cand_01_ml_student",
        "description": "Student with machine learning coursework and sentiment analysis project",
        "raw_text": (
            "Aarav Sharma\n"
            "Email: aarav.sharma@example.com\n"
            "Education: B.Tech in Computer Science and Engineering, 2024\n"
            "Technical Skills: Python, Scikit-learn, Pandas, NumPy, NLTK, Git, Matplotlib\n"
            "Projects:\n"
            "SentimentScope: Built an NLP sentiment classification service in Python using NLTK and Scikit-learn Logistic Regression.\n"
            "Trained models on 25,000 product reviews with TF-IDF vectorization and 86% accuracy."
        ),
        "job_description": (
            "Job Title: Junior Machine Learning Engineer\n"
            "We are seeking a Junior ML Engineer. Requirements: Strong Python proficiency and experience with Scikit-learn are required. "
            "Experience with Docker containerization and PyTorch is required. "
            "Preferred: Familiarity with AWS deployment and CI/CD pipelines. Must have strong analytical problem-solving skills."
        ),
        "expected_role": "Junior Machine Learning Engineer",
        "key_verified_skills": ["Python", "Scikit-learn", "Pandas", "NumPy", "NLTK", "Git"]
    },

    # 2. Backend developer
    "scenario_2_backend_dev": {
        "candidate_id": "cand_02_backend_dev",
        "description": "Backend engineer with strong REST API, Flask, and relational database experience",
        "raw_text": (
            "Rohit Verma\n"
            "Backend Software Engineer\n"
            "Education: Bachelor of Engineering in Information Technology\n"
            "Skills: Python, Flask, FastAPI, PostgreSQL, SQL, Redis, Git, Linux, Pytest\n"
            "Experience:\n"
            "Software Engineer at CloudNative Labs: Developed RESTful microservices using Flask and PostgreSQL. "
            "Optimized SQL query performance using B-Tree indexes and connection pooling. Implemented automated pytest suites."
        ),
        "job_description": (
            "Job Title: Senior Backend Engineer\n"
            "Requirements: Experience with Python, REST APIs, and PostgreSQL is required. "
            "Must have experience with Docker, Kubernetes, and AWS cloud infrastructure. "
            "Preferred: Experience with Apache Kafka and CI/CD automation."
        ),
        "expected_role": "Senior Backend Engineer",
        "key_verified_skills": ["Python", "Flask", "FastAPI", "PostgreSQL", "SQL", "Git", "Linux"]
    },

    # 3. Frontend developer
    "scenario_3_frontend_dev": {
        "candidate_id": "cand_03_frontend_dev",
        "description": "Frontend web developer specialized in JavaScript, HTML5, CSS3, and UI styling",
        "raw_text": (
            "Priya Patel\n"
            "Frontend Web Developer\n"
            "Education: Bachelor of Science in Computer Science\n"
            "Skills: JavaScript, HTML, CSS, Bootstrap, Tailwind CSS, Git, Responsive Design, Webpack\n"
            "Projects:\n"
            "EcoStore Web App: Built a responsive e-commerce web interface with JavaScript and CSS Grid. "
            "Implemented accessible navigation components and dynamic product filtering."
        ),
        "job_description": (
            "Job Title: React Frontend Engineer\n"
            "Requirements: Proficiency in JavaScript, HTML, and CSS is required. "
            "Experience with React and TypeScript is mandatory. "
            "Preferred: Jest unit testing and Jira agile workflow experience. Strong communication skills required."
        ),
        "expected_role": "React Frontend Engineer",
        "key_verified_skills": ["JavaScript", "HTML", "CSS", "Git"]
    },

    # 4. Data analyst
    "scenario_4_data_analyst": {
        "candidate_id": "cand_04_data_analyst",
        "description": "Data analyst proficient in Excel modeling, SQL reporting, and dashboard visualization",
        "raw_text": (
            "Ananya Iyer\n"
            "Business Data Analyst\n"
            "Education: B.Com & Diploma in Data Analytics\n"
            "Skills: Excel, Advanced Excel, SQL, MySQL, PivotTables, VLOOKUP, Data Cleaning\n"
            "Experience:\n"
            "Junior Analyst at RetailMetrics: Constructed monthly financial forecasting models in Excel with PivotTables. "
            "Queried transactional records in MySQL for executive KPI reports."
        ),
        "job_description": (
            "Job Title: BI & Analytics Specialist\n"
            "Requirements: Advanced Excel and SQL proficiency are required. "
            "Experience with Power BI or Tableau is mandatory. "
            "Preferred: Python scripting for data automation. Strong analytical problem-solving and communication required."
        ),
        "expected_role": "BI & Analytics Specialist",
        "key_verified_skills": ["Excel", "SQL", "MySQL"]
    },

    # 5. Data engineer
    "scenario_5_data_engineer": {
        "candidate_id": "cand_05_data_engineer",
        "description": "Data engineer with Python, SQL, and database ETL background looking to transition to distributed Big Data",
        "raw_text": (
            "Vikram Singh\n"
            "Data Pipeline Engineer\n"
            "Education: B.Tech in Computer Science\n"
            "Skills: Python, SQL, PostgreSQL, Pandas, Linux, Bash, Git, ETL\n"
            "Projects:\n"
            "Batch Ingestion Pipeline: Built an automated Python ETL script extracting CSV records, cleaning null fields with Pandas, "
            "and loading partitioned data into PostgreSQL."
        ),
        "job_description": (
            "Job Title: Big Data Engineer\n"
            "Requirements: Proficiency in Python, SQL, and Linux is required. "
            "Hands-on experience with Apache Spark (PySpark) and distributed storage (Hadoop) is required. "
            "Preferred: Apache Kafka streaming and Docker containerization. Must have strong analytical problem-solving skills."
        ),
        "expected_role": "Big Data Engineer",
        "key_verified_skills": ["Python", "SQL", "PostgreSQL", "Pandas", "Linux", "Git"]
    },

    # 6. Candidate with internships but no full-time employment
    "scenario_6_internship_only": {
        "candidate_id": "cand_06_internship_only",
        "description": "Recent graduate who completed two internships without formal full-time software engineering roles",
        "raw_text": (
            "Neha Kulkarni\n"
            "Software Engineering Graduate\n"
            "Education: Bachelor of Technology in Information Science, 2024\n"
            "Skills: Java, Python, Git, HTML, CSS, SQL\n"
            "Internships:\n"
            "Software Intern at FinTech Labs (6 months): Assisted in developing backend Java services and writing JUnit unit tests.\n"
            "Web Development Intern at MediaWorks (3 months): Maintained client websites using HTML, CSS, and basic JavaScript."
        ),
        "job_description": (
            "Job Title: Associate Software Engineer\n"
            "Requirements: Core programming in Java or Python and basic SQL knowledge are required. "
            "Must be familiar with Git and unit testing principles. "
            "Preferred: Docker containerization and CI/CD pipelines. Strong communication and teamwork required."
        ),
        "expected_role": "Associate Software Engineer",
        "key_verified_skills": ["Java", "Python", "Git", "HTML", "CSS", "SQL"]
    },

    # 7. Experienced professional
    "scenario_7_experienced_pro": {
        "candidate_id": "cand_07_experienced_pro",
        "description": "Senior engineer with 5 years experience in enterprise systems architecture and DevOps",
        "raw_text": (
            "Karthik Nair\n"
            "Lead Systems Architect\n"
            "Education: Master of Science in Computer Science\n"
            "Skills: Python, Go, Docker, Kubernetes, AWS, PostgreSQL, Terraform, CI/CD, Linux, Git, Agile, Project Management\n"
            "Experience:\n"
            "Senior Infrastructure Engineer at Global Cloud Tech (5 years): Architected multi-region AWS infrastructure using Terraform. "
            "Led migration of 20+ microservices to Kubernetes clusters with zero downtime. Mentored team of 6 engineers."
        ),
        "job_description": (
            "Job Title: Principal DevOps Architect\n"
            "Requirements: Deep expertise in Kubernetes, Docker, AWS, and CI/CD automation is required. "
            "Must have experience leading Agile project management and architectural roadmaps. "
            "Preferred: Go programming and security compliance certifications. Mentorship and communication required."
        ),
        "expected_role": "Principal DevOps Architect",
        "key_verified_skills": ["Python", "Docker", "Kubernetes", "AWS", "PostgreSQL", "CI/CD", "Linux", "Git", "Project Management"]
    },

    # 8. Candidate with limited project evidence
    "scenario_8_limited_projects": {
        "candidate_id": "cand_08_limited_projects",
        "description": "Career switcher with self-study skills listed but minimal documented projects",
        "raw_text": (
            "Deepak Joshi\n"
            "Aspiring Web Developer\n"
            "Education: Bachelor of Arts, 2021\n"
            "Skills: Python, HTML, CSS, JavaScript\n"
            "Summary: Self-taught programmer passionate about building modern web applications and expanding coding skills."
        ),
        "job_description": (
            "Job Title: Junior Web Developer\n"
            "Requirements: Foundational Python and JavaScript skills are required. "
            "Must have practical experience with Flask or Django web frameworks. "
            "Preferred: Git version control and SQL database basics. Eagerness to learn and communication essential."
        ),
        "expected_role": "Junior Web Developer",
        "key_verified_skills": ["Python", "HTML", "CSS", "JavaScript"]
    },

    # 9. Resume with missing education details
    "scenario_9_missing_education": {
        "candidate_id": "cand_09_missing_education",
        "description": "Freelancer resume with extensive technical skills and client projects but omitted formal degree section",
        "raw_text": (
            "Siddharth Rao\n"
            "Independent Full-Stack Developer\n"
            "Skills: React, Node.js, TypeScript, PostgreSQL, Docker, Git, Express\n"
            "Projects:\n"
            "TaskFlow App: Full-stack productivity application built with React, TypeScript, and Node.js.\n"
            "Deployed with Docker containers and managed state using React Hooks."
        ),
        "job_description": (
            "Job Title: Full-Stack Developer\n"
            "Requirements: Experience with React, TypeScript, and PostgreSQL is required. "
            "Bachelor's degree in Computer Science or related technical field is required. "
            "Preferred: Docker containerization and automated testing. Strong teamwork required."
        ),
        "expected_role": "Full-Stack Developer",
        "key_verified_skills": ["React", "TypeScript", "PostgreSQL", "Docker", "Git"]
    },

    # 10. JD with ambiguous requirements
    "scenario_10_ambiguous_jd": {
        "candidate_id": "cand_10_ambiguous_jd",
        "description": "Candidate evaluated against an unformatted JD mixing buzzwords and varied requirement strengths",
        "raw_text": (
            "Meera Nambiar\n"
            "Software Developer\n"
            "Education: B.Tech Computer Science\n"
            "Skills: Python, SQL, Git, Linux, Flask\n"
            "Projects:\n"
            "DataSync Tool: Developed Python CLI utility with SQL integration for synchronizing inventory databases."
        ),
        "job_description": (
            "About the job: Rock-star technologist wanted. Good vibes, fast-paced startup. "
            "We do lots of Python and SQL every single day. Nice to know Docker or Kubernetes. "
            "You should have strong communication skills and basic PC skills. "
            "Visio, Jira, and Excel knowledge would be advantageous. College degree preferred."
        ),
        "expected_role": "Target role not specified",
        "key_verified_skills": ["Python", "SQL", "Git", "Linux", "Flask"]
    }
}
