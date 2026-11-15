"""
Thirty Comprehensive Real-World Candidate & Job Description Fixtures for Phase 10 Quality Audit.
Enforces realistic diversity across technical domains, career levels, edge cases, and requirement nuances:
1. Student with ML projects
2. Backend developer
3. Frontend developer
4. Data analyst
5. Data engineer
6. Candidate with internships only (0 full-time roles)
7. Experienced professional (5 years)
8. Candidate with limited project evidence
9. Resume with missing education details
10. JD with ambiguous / buzzword requirements
11. Machine Learning NLP Engineer
12. Cloud DevOps / SRE Engineer
13. Full-Stack JavaScript/TypeScript Developer
14. Mobile App Developer (Flutter / Android)
15. Cyber Security / InfoSec Analyst
16. Embedded Systems / IoT Engineer
17. Computer Vision Research Engineer
18. QA Automation Engineer / SDET
19. Database Administrator (DBA)
20. Mechanical Engineer Career Switcher to Data Science
21. Sales Executive Career Switcher to Business Analyst
22. Academic Student (0 internships, 0 work experience, coursework only)
23. Senior Principal Architect (12+ years experience)
24. Sparse / Incomplete Resume (minimal text)
25. Compound Requirements ("Docker, Kubernetes, CI/CD, AWS are required")
26. Alternative Skill Requirement ("Power BI or Tableau required" - Candidate has Power BI)
27. Alternative Skill Requirement ("PostgreSQL or MySQL required" - Candidate has MySQL)
28. Alternative Skill Requirement ("PyTorch or TensorFlow required" - Candidate has PyTorch)
29. Unstructured / Jargon-Dense Startup JD
30. Multi-Project Diversity Candidate (3 distinct domain projects)
"""

from typing import Dict, Any
from .candidate_scenarios import CANDIDATE_SCENARIOS as BASE_TEN

THIRTY_AUDIT_SCENARIOS: Dict[str, Dict[str, Any]] = dict(BASE_TEN)

# Scenarios 11 through 30
THIRTY_AUDIT_SCENARIOS.update({
    # 11. Machine Learning NLP Engineer
    "scenario_11_nlp_engineer": {
        "candidate_id": "cand_11_nlp_engineer",
        "description": "NLP engineer with HuggingFace, Transformers, and PyTorch fine-tuning experience",
        "raw_text": (
            "Tanvi Deshmukh\n"
            "Machine Learning NLP Engineer\n"
            "Education: Master of Technology in Artificial Intelligence, 2023\n"
            "Skills: Python, PyTorch, Transformers, HuggingFace, NLTK, spaCy, BERT, Git, Docker\n"
            "Projects:\n"
            "ClinicalEntityExtractor: Fine-tuned BioBERT on 40,000 biomedical abstracts for Named Entity Recognition using PyTorch and HuggingFace.\n"
            "Evaluated micro-F1 scores and deployed containerized REST inference endpoints."
        ),
        "job_description": (
            "Job Title: Senior NLP Engineer\n"
            "Requirements: Strong proficiency in Python, PyTorch, and Transformer architectures is required. "
            "Experience with LangChain, Vector Databases, and MLflow model tracking is required. "
            "Preferred: AWS SageMaker deployment and CI/CD pipelines. Strong collaboration skills essential."
        ),
        "expected_role": "Senior NLP Engineer",
        "key_verified_skills": ["Python", "PyTorch", "Transformers", "BERT", "Git", "Docker"]
    },

    # 12. Cloud DevOps / SRE Engineer
    "scenario_12_cloud_sre": {
        "candidate_id": "cand_12_cloud_sre",
        "description": "Site Reliability Engineer with Kubernetes, Terraform, and Prometheus observability background",
        "raw_text": (
            "Rohan Mehta\n"
            "DevOps & Site Reliability Engineer\n"
            "Education: B.E. in Computer Science\n"
            "Skills: Linux, Bash, Kubernetes, Docker, Terraform, Prometheus, Grafana, Git, CI/CD, Python\n"
            "Experience:\n"
            "SRE at ScaleCloud: Configured Kubernetes cluster autoscalers and Prometheus alerting rules for 50+ microservices.\n"
            "Authored Terraform modules for infrastructure provisioning and reduced cluster MTTR by 35%."
        ),
        "job_description": (
            "Job Title: Cloud Infrastructure Engineer\n"
            "Requirements: Deep expertise with Linux, Kubernetes, Docker, and Terraform is required. "
            "Must have experience with AWS cloud architecture and ArgoCD GitOps pipelines. "
            "Preferred: Helm charting and Ansible automation. Strong incident response and on-call communication skills."
        ),
        "expected_role": "Cloud Infrastructure Engineer",
        "key_verified_skills": ["Linux", "Kubernetes", "Docker", "Terraform", "Prometheus", "Git", "Python"]
    },

    # 13. Full-Stack JavaScript/TypeScript Developer
    "scenario_13_fullstack_ts": {
        "candidate_id": "cand_13_fullstack_ts",
        "description": "Full-stack developer building React/Node applications looking to step into Next.js & GraphQL",
        "raw_text": (
            "Ishaan Sen\n"
            "Full-Stack Web Developer\n"
            "Education: Bachelor of Computer Applications (BCA), 2022\n"
            "Skills: JavaScript, TypeScript, React, Node.js, Express, MongoDB, Git, HTML, CSS, Tailwind CSS\n"
            "Projects:\n"
            "DevHub Platform: Engineered full-stack developer social network with React, Node.js, Express, and MongoDB.\n"
            "Implemented JWT authentication, WebSocket real-time chat, and responsive Tailwind styling."
        ),
        "job_description": (
            "Job Title: Senior Full-Stack Engineer\n"
            "Requirements: Mastery of TypeScript, React, and Node.js is required. "
            "Experience with Next.js and PostgreSQL database design is required. "
            "Preferred: GraphQL APIs and Docker containerization. Agile sprint participation required."
        ),
        "expected_role": "Senior Full-Stack Engineer",
        "key_verified_skills": ["JavaScript", "TypeScript", "React", "Node.js", "Express", "MongoDB", "Git"]
    },

    # 14. Mobile App Developer (Flutter / Android)
    "scenario_14_mobile_dev": {
        "candidate_id": "cand_14_mobile_dev",
        "description": "Mobile engineer specializing in cross-platform Flutter and Dart app development",
        "raw_text": (
            "Kavya Nair\n"
            "Cross-Platform Mobile Engineer\n"
            "Education: B.Tech in Information Technology\n"
            "Skills: Flutter, Dart, Android, SQLite, REST APIs, Git, Firebase, State Management\n"
            "Projects:\n"
            "FitPulse Mobile: Developed cross-platform health tracking app in Flutter and Dart with SQLite local storage.\n"
            "Integrated background step-counting sensors and cloud synchronization via REST endpoints."
        ),
        "job_description": (
            "Job Title: Senior Mobile Engineer\n"
            "Requirements: Strong experience with Flutter and Dart is required. "
            "Native Android (Kotlin) or iOS (Swift) integration knowledge is required. "
            "Preferred: CI/CD mobile build automation (Fastlane) and automated UI testing."
        ),
        "expected_role": "Senior Mobile Engineer",
        "key_verified_skills": ["Flutter", "Dart", "Android", "SQLite", "Git", "Firebase"]
    },

    # 15. Cyber Security / InfoSec Analyst
    "scenario_15_cybersecurity": {
        "candidate_id": "cand_15_cybersecurity",
        "description": "Security analyst with vulnerability scanning, Wireshark packet inspection, and network defense",
        "raw_text": (
            "Aditya Menon\n"
            "Information Security Analyst\n"
            "Education: B.Tech in Cyber Security\n"
            "Skills: Linux, Python, Wireshark, Nmap, Vulnerability Assessment, Network Security, Bash, Git\n"
            "Experience:\n"
            "Security Associate at SecureShield: Conducted automated network vulnerability scans with Nmap and Nessus.\n"
            "Analyzed pcap network traffic logs with Wireshark to investigate anomalous intrusion attempts."
        ),
        "job_description": (
            "Job Title: SOC Security Analyst\n"
            "Requirements: Strong knowledge of Linux, Network Security, and Wireshark is required. "
            "Experience with SIEM tools (Splunk) and Incident Response triage is mandatory. "
            "Preferred: Python scripting for security automation and ISO 27001 familiarity."
        ),
        "expected_role": "SOC Security Analyst",
        "key_verified_skills": ["Linux", "Python", "Wireshark", "Network Security", "Git"]
    },

    # 16. Embedded Systems / IoT Engineer
    "scenario_16_embedded_iot": {
        "candidate_id": "cand_16_embedded_iot",
        "description": "Hardware and firmware engineer with C, C++, and RTOS microcontroller programming",
        "raw_text": (
            "Pranav Hegde\n"
            "Embedded Firmware Engineer\n"
            "Education: B.E. in Electronics and Communication Engineering\n"
            "Skills: C, C++, Embedded Systems, FreeRTOS, Microcontrollers, I2C, SPI, UART, Git, Linux\n"
            "Projects:\n"
            "SmartSensor Node: Engineered low-power telemetry firmware on STM32 microcontrollers in C using FreeRTOS.\n"
            "Interfaced environmental sensors via I2C and transmitted data packets over UART with CRC verification."
        ),
        "job_description": (
            "Job Title: Embedded Software Engineer\n"
            "Requirements: Proficiency in C, C++, and Embedded Systems is required. "
            "Experience with Embedded Linux Kernel development and device drivers is required. "
            "Preferred: Bluetooth Low Energy (BLE) protocols and oscilloscope debugging."
        ),
        "expected_role": "Embedded Software Engineer",
        "key_verified_skills": ["C", "C++", "Embedded Systems", "Linux", "Git"]
    },

    # 17. Computer Vision Research Engineer
    "scenario_17_cv_engineer": {
        "candidate_id": "cand_17_cv_engineer",
        "description": "Computer vision engineer specialized in real-time object detection and OpenCV processing",
        "raw_text": (
            "Swati Choudhury\n"
            "Computer Vision Engineer\n"
            "Education: M.S. in Computer Science (Vision & Robotics)\n"
            "Skills: Python, OpenCV, PyTorch, C++, NumPy, CNN, Git, Linux, Docker\n"
            "Projects:\n"
            "VisionTraffic: Built real-time vehicle counting and speed estimation pipeline using OpenCV and PyTorch YOLOv8.\n"
            "Processed 1080p 30fps video streams with bounding box tracking and Kalman filters."
        ),
        "job_description": (
            "Job Title: Real-Time Computer Vision Specialist\n"
            "Requirements: Strong proficiency in Python, OpenCV, and PyTorch is required. "
            "Experience with TensorRT optimization and CUDA acceleration is mandatory. "
            "Preferred: C++ production deployment and ONNX runtime integration."
        ),
        "expected_role": "Real-Time Computer Vision Specialist",
        "key_verified_skills": ["Python", "OpenCV", "PyTorch", "C++", "NumPy", "Git", "Linux"]
    },

    # 18. QA Automation Engineer / SDET
    "scenario_18_sdet": {
        "candidate_id": "cand_18_sdet",
        "description": "Software Development Engineer in Test (SDET) with Java, Selenium, and CI automation",
        "raw_text": (
            "Gaurav Bhat\n"
            "QA Automation Lead\n"
            "Education: B.Tech in Information Technology\n"
            "Skills: Java, Selenium, TestNG, Jenkins, Git, SQL, Postman, REST API Testing\n"
            "Experience:\n"
            "QA Engineer at FinServe: Engineered end-to-end automated UI regression test suites with Java, Selenium, and TestNG.\n"
            "Integrated test execution into Jenkins CI pipelines, reducing manual release testing from 18 hours to 45 minutes."
        ),
        "job_description": (
            "Job Title: Senior SDET (Automation)\n"
            "Requirements: Strong programming skills in Java or Python and test automation with Selenium are required. "
            "Experience with Cypress or Playwright modern test frameworks is mandatory. "
            "Preferred: Dockerized grid test execution and performance testing with JMeter."
        ),
        "expected_role": "Senior SDET (Automation)",
        "key_verified_skills": ["Java", "Selenium", "Git", "SQL", "Jenkins"]
    },

    # 19. Database Administrator (DBA)
    "scenario_19_dba": {
        "candidate_id": "cand_19_dba",
        "description": "Database administrator with high-availability PostgreSQL and MySQL clustering experience",
        "raw_text": (
            "Manoj Pillai\n"
            "Database Administrator\n"
            "Education: B.Sc. in Computer Science\n"
            "Skills: PostgreSQL, MySQL, SQL, Linux, Bash, Performance Tuning, Backup & Recovery, Git\n"
            "Experience:\n"
            "DBA at DataBank Systems: Administered 40+ PostgreSQL production database instances with streaming replication.\n"
            "Tuned slow queries by re-indexing tables, reducing p95 query latency by 42% across transaction tables."
        ),
        "job_description": (
            "Job Title: Senior Infrastructure DBA\n"
            "Requirements: Deep expertise in PostgreSQL, SQL, and Linux systems is required. "
            "Hands-on experience with MongoDB or Cassandra distributed databases is required. "
            "Preferred: Terraform infrastructure-as-code and cloud database management (AWS RDS/Aurora)."
        ),
        "expected_role": "Senior Infrastructure DBA",
        "key_verified_skills": ["PostgreSQL", "MySQL", "SQL", "Linux", "Git"]
    },

    # 20. Mechanical Engineer Career Switcher to Data Science
    "scenario_20_career_switcher_mech": {
        "candidate_id": "cand_20_career_switcher_mech",
        "description": "Mechanical engineer transitioning into data science with self-taught Python and Pandas",
        "raw_text": (
            "Harish Kulkarni\n"
            "Aspiring Data Scientist (Mechanical Engineer Transition)\n"
            "Education: Bachelor of Engineering in Mechanical Engineering, 2021\n"
            "Skills: Python, Pandas, NumPy, Matplotlib, SQL, Excel, Git, Statistical Analysis\n"
            "Projects:\n"
            "VibrationDataAnalytics: Analyzed rotating machinery vibration datasets using Python, Pandas, and NumPy.\n"
            "Computed statistical features (kurtosis, RMS, FFT spectrum) to identify bearing wear anomalies."
        ),
        "job_description": (
            "Job Title: Junior Data Scientist\n"
            "Requirements: Proficiency in Python, Pandas, and SQL is required. "
            "Must have hands-on experience with Scikit-learn machine learning algorithms and model validation. "
            "Preferred: Tableau data visualization and Docker containerization. Strong mathematical reasoning essential."
        ),
        "expected_role": "Junior Data Scientist",
        "key_verified_skills": ["Python", "Pandas", "NumPy", "SQL", "Excel", "Git"]
    },

    # 21. Sales Executive Career Switcher to Business Analyst
    "scenario_21_career_switcher_sales": {
        "candidate_id": "cand_21_career_switcher_sales",
        "description": "Sales manager transitioning to tech business analysis with Excel and stakeholder expertise",
        "raw_text": (
            "Pooja Saxena\n"
            "Aspiring Tech Business Analyst\n"
            "Education: Master of Business Administration (MBA) in Marketing\n"
            "Skills: Excel, Advanced Excel, Stakeholder Management, Requirement Gathering, Communication, PowerPoint\n"
            "Experience:\n"
            "Senior Sales Executive at TradeCorp (3 years): Gathered client requirements, created quarterly revenue forecasts in Excel, "
            "and presented executive roadmaps to leadership."
        ),
        "job_description": (
            "Job Title: IT Business Analyst\n"
            "Requirements: Strong requirement gathering, communication, and Excel modeling skills are required. "
            "Experience with SQL database querying and Jira agile project management is mandatory. "
            "Preferred: User story mapping and Visio process flow diagrams."
        ),
        "expected_role": "IT Business Analyst",
        "key_verified_skills": ["Excel", "Communication", "Project Management"]
    },

    # 22. Academic Student (0 internships, 0 work experience, coursework only)
    "scenario_22_student_coursework": {
        "candidate_id": "cand_22_student_coursework",
        "description": "Fresh computer science student with university coursework and algorithms only",
        "raw_text": (
            "Nikhil Varma\n"
            "Computer Science Undergraduate, Class of 2025\n"
            "Education: B.Tech in Computer Science and Engineering (In Progress)\n"
            "Relevant Coursework: Data Structures, Algorithms, Object-Oriented Programming, Database Systems\n"
            "Skills: C, Java, Python, SQL, Git, Linux\n"
            "Projects:\n"
            "LibraryManagementCLI: Course project built in Java with MySQL database backend managing book checkout transactions."
        ),
        "job_description": (
            "Job Title: Junior Software Developer Intern\n"
            "Requirements: Core understanding of Java or Python and basic SQL is required. "
            "Must understand Git version control and fundamental data structures. "
            "Preferred: Spring Boot framework basics and unit testing. Eagerness to learn and teamwork essential."
        ),
        "expected_role": "Junior Software Developer Intern",
        "key_verified_skills": ["Java", "Python", "SQL", "C", "Git", "Linux"]
    },

    # 23. Senior Principal Architect (12+ years experience)
    "scenario_23_senior_principal_architect": {
        "candidate_id": "cand_23_senior_principal_architect",
        "description": "Principal systems architect with 12+ years designing distributed microservices and cloud topologies",
        "raw_text": (
            "Rajeshwari Sundaram\n"
            "Principal Distributed Systems Architect\n"
            "Education: M.Tech in Computer Science, 2012\n"
            "Skills: Java, Spring Boot, Microservices, Apache Kafka, Kubernetes, AWS, PostgreSQL, Redis, System Design, Mentorship\n"
            "Experience:\n"
            "Staff Architect at FinPlatform (6 years): Architected multi-region event-driven payment processing engine handling 12,000 TPS.\n"
            "Senior Systems Engineer at Enterprise Corp (6 years): Led decomposition of legacy monolithic ERP into 30+ Spring Boot microservices."
        ),
        "job_description": (
            "Job Title: Distinguished Systems Architect\n"
            "Requirements: Deep expertise in Distributed Systems, Kubernetes, AWS, and Apache Kafka is required. "
            "Proven track record of architectural leadership, system design, and engineering mentorship is mandatory. "
            "Preferred: Golang high-performance concurrency and multi-cloud resilience (GCP/Azure)."
        ),
        "expected_role": "Distinguished Systems Architect",
        "key_verified_skills": ["Java", "Spring Boot", "Kubernetes", "AWS", "PostgreSQL", "Redis", "System Design", "Mentorship"]
    },

    # 24. Sparse / Incomplete Resume (minimal text)
    "scenario_24_sparse_resume": {
        "candidate_id": "cand_24_sparse_resume",
        "description": "Ultra-short resume with only contact info, degree, and 4 skills listed without descriptions",
        "raw_text": (
            "Sunil Rawat\n"
            "sunil.rawat@example.com\n"
            "B.Tech Computer Science 2023\n"
            "Skills: Python, SQL, C++, HTML"
        ),
        "job_description": (
            "Job Title: Junior Software Trainee\n"
            "Requirements: Basic programming knowledge in Python or C++ and SQL fundamentals are required. "
            "Familiarity with Git and web development basics is required. "
            "Preferred: Clear communication and eager attitude."
        ),
        "expected_role": "Junior Software Trainee",
        "key_verified_skills": ["Python", "SQL", "C++", "HTML"]
    },

    # 25. Compound Requirements ("Docker, Kubernetes, CI/CD, AWS are required")
    "scenario_25_compound_clause": {
        "candidate_id": "cand_25_compound_clause",
        "description": "Candidate evaluated against a JD with compound multi-skill sentence clauses",
        "raw_text": (
            "Divya Nair\n"
            "Cloud Platform Engineer\n"
            "Education: B.E. in Information Science\n"
            "Skills: Python, Docker, CI/CD, Git, Linux, Flask\n"
            "Projects:\n"
            "ContainerPipeline: Built automated GitHub Actions CI/CD workflows building multi-stage Docker containers for Flask services."
        ),
        "job_description": (
            "Job Title: Cloud DevOps Specialist\n"
            "Requirements: Python programming and Linux proficiency are required. "
            "Docker, Kubernetes, CI/CD, AWS are required for managing production clusters. "
            "Preferred: Terraform and Prometheus monitoring."
        ),
        "expected_role": "Cloud DevOps Specialist",
        "key_verified_skills": ["Python", "Docker", "CI/CD", "Git", "Linux", "Flask"]
    },

    # 26. Alternative Skill Requirement ("Power BI or Tableau required" - Candidate has Power BI)
    "scenario_26_alt_powerbi_tableau": {
        "candidate_id": "cand_26_alt_powerbi_tableau",
        "description": "Candidate with Power BI evaluated against a JD requiring 'Power BI or Tableau'",
        "raw_text": (
            "Sneha Bansal\n"
            "Business Intelligence Analyst\n"
            "Education: Bachelor of Commerce & Data Analytics\n"
            "Skills: Power BI, SQL, Advanced Excel, DAX, Data Modeling, Git\n"
            "Projects:\n"
            "ExecutiveKPIReport: Developed interactive Power BI dashboards with DAX measures and SQL star-schema views."
        ),
        "job_description": (
            "Job Title: BI Report Developer\n"
            "Requirements: SQL and Excel proficiency are required. "
            "Experience with Power BI or Tableau is mandatory. "
            "Preferred: Python data manipulation and cloud analytics."
        ),
        "expected_role": "BI Report Developer",
        "key_verified_skills": ["Power BI", "SQL", "Excel"]
    },

    # 27. Alternative Skill Requirement ("PostgreSQL or MySQL required" - Candidate has MySQL)
    "scenario_27_alt_postgres_mysql": {
        "candidate_id": "cand_27_alt_postgres_mysql",
        "description": "Candidate with MySQL evaluated against a JD requiring 'PostgreSQL or MySQL'",
        "raw_text": (
            "Alok Gupta\n"
            "Database Developer\n"
            "Education: B.Tech in Computer Science\n"
            "Skills: MySQL, SQL, Python, Flask, Git, Linux\n"
            "Projects:\n"
            "InventoryDB: Architected normalized MySQL database schemas with B-Tree indexing and stored procedures in Python."
        ),
        "job_description": (
            "Job Title: Backend Database Programmer\n"
            "Requirements: Python programming is required. "
            "Hands-on database development in PostgreSQL or MySQL is required. "
            "Preferred: Redis caching and Docker containerization."
        ),
        "expected_role": "Backend Database Programmer",
        "key_verified_skills": ["MySQL", "SQL", "Python", "Flask", "Git"]
    },

    # 28. Alternative Skill Requirement ("PyTorch or TensorFlow required" - Candidate has PyTorch)
    "scenario_28_alt_pytorch_tensorflow": {
        "candidate_id": "cand_28_alt_pytorch_tensorflow",
        "description": "Candidate with PyTorch evaluated against a JD requiring 'PyTorch or TensorFlow'",
        "raw_text": (
            "Kiran Rao\n"
            "Deep Learning Researcher\n"
            "Education: M.Tech in Data Science\n"
            "Skills: PyTorch, Python, NumPy, Scikit-learn, Git, Linux, Deep Learning\n"
            "Projects:\n"
            "NeuralClassifier: Designed deep convolutional networks in PyTorch for image classification with custom data loaders."
        ),
        "job_description": (
            "Job Title: Deep Learning Engineer\n"
            "Requirements: Strong Python and linear algebra fundamentals are required. "
            "Production modeling in PyTorch or TensorFlow is required. "
            "Preferred: ONNX model export and TensorRT inference."
        ),
        "expected_role": "Deep Learning Engineer",
        "key_verified_skills": ["PyTorch", "Python", "NumPy", "Scikit-learn", "Git"]
    },

    # 29. Unstructured / Jargon-Dense Startup JD
    "scenario_29_jargon_dense_jd": {
        "candidate_id": "cand_29_jargon_dense_jd",
        "description": "Standard developer evaluated against a chaotic, buzzword-heavy startup job posting",
        "raw_text": (
            "Abhishek Mishra\n"
            "Software Developer\n"
            "Education: B.Tech in Computer Science\n"
            "Skills: Python, Django, SQL, PostgreSQL, Git, JavaScript, Linux\n"
            "Projects:\n"
            "MarketPlaceHub: Built Django multi-vendor marketplace with PostgreSQL backend and payment gateway integration."
        ),
        "job_description": (
            "Wanted: 10x Rockstar Ninja Hacker to conquer the future! "
            "We are a hyper-growth stealth startup disrupting human paradigm shifts with synergy and AI magic. "
            "You must live and breathe Python and PostgreSQL day and night. "
            "Must be able to wear 15 hats at once, run at lightspeed, and build bulletproof scalable code. "
            "Docker and Redis knowledge would be awesome sauce. College degree optional if you are a true wizard."
        ),
        "expected_role": "Target role not specified",
        "key_verified_skills": ["Python", "Django", "SQL", "PostgreSQL", "Git", "Linux"]
    },

    # 30. Multi-Project Diversity Candidate (3 distinct domain projects)
    "scenario_30_multi_project_diversity": {
        "candidate_id": "cand_30_multi_project_diversity",
        "description": "Candidate with 3 verified projects across Web, ML, and Data Engineering domains",
        "raw_text": (
            "Harsha Vardhan\n"
            "Full-Stack & ML Systems Engineer\n"
            "Education: Bachelor of Technology in Computer Science and Engineering\n"
            "Skills: Python, Flask, React, PostgreSQL, Docker, PyTorch, Scikit-Learn, Git, SQL, Linux\n"
            "Projects:\n"
            "Project Alpha - Multimodal Resume Matcher:\n"
            "Engineered end-to-end dual-unseen document matching pipeline using Python, Flask, and Scikit-Learn.\n"
            "Project Beta - Distributed Event Streamer:\n"
            "Built containerized asynchronous streaming engine using Docker, Python, and PostgreSQL.\n"
            "Project Gamma - Computer Vision Defect Detector:\n"
            "Designed real-time convolutional inspection pipeline using PyTorch, OpenCV, and Flask."
        ),
        "job_description": (
            "Job Title: Senior Systems Engineer (AI & Cloud)\n"
            "Requirements: Python, Flask, and PostgreSQL are required. "
            "Docker containerization and PyTorch machine learning are mandatory. "
            "Preferred: Kubernetes and AWS deployment. Must demonstrate strong architectural communication."
        ),
        "expected_role": "Senior Systems Engineer (AI & Cloud)",
        "key_verified_skills": ["Python", "Flask", "PostgreSQL", "Docker", "PyTorch", "Scikit-Learn", "Git", "SQL"]
    }
})
