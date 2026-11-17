"""
Deterministic, explainable heuristic evaluator for interview-practice answers.

Measures:
1. Relevance to the question.
2. Technical accuracy where verifiable (marks unverifiable when ground truth is absent).
3. Coverage of required concepts and expected key points.
4. Clarity and structure (framework adherence: STAR, PREP, PAR, CAR, etc.).
5. Specificity and supporting examples (concrete metrics, named tools, project context).
6. Evidence consistency with the candidate's verified resume.

Enforces strict coaching rules:
- Zero fabrication of candidate achievements, metrics, or technologies.
- Distinguishes general answer-quality feedback from resume-supported claims.
- Penalizes keyword stuffing and token repetition.
- Transparent disclaimer that heuristic feedback is for practice, not human interview prediction.
"""
import re
from typing import Dict, List, Any, Optional
from collections import Counter

from .answer_frameworks import get_framework


class HeuristicAnswerEvaluator:
    LABEL = "Heuristic Answer Feedback"
    DISCLAIMER = (
        "This feedback is automated, rule-based, and heuristic. It supports self-guided "
        "practice; it is not an accredited or predictive human interview score."
    )

    _STOPWORDS = {
        "this", "that", "with", "from", "have", "were", "what", "where", "when",
        "using", "your", "overview", "about", "their", "there", "which", "while",
        "into", "they", "them", "then", "than", "will", "would", "could", "should",
        "such", "also", "some", "more", "most", "very", "been", "being", "does",
        "did", "does", "the", "and", "for", "are", "was", "our", "you", "how",
    }

    _TECHNICAL_ENTITIES = (
        "python", "java", "c++", "c#", ".net", "sql", "docker", "pytorch",
        "tensorflow", "scikit-learn", "sklearn", "flask", "fastapi", "kubernetes",
        "aws", "git", "linux", "react", "opencv", "pandas", "numpy", "postgresql",
        "mysql", "redis", "mongodb", "xgboost", "random forest", "logistic regression",
        "linear svc", "tf-idf", "rest api", "pytest", "playwright", "graphql",
        "typescript", "javascript", "node.js", "django", "spring boot", "kafka"
    )

    # Defined validation rules to genuinely verify technical usage beyond mere name-dropping
    _TECH_VALIDATION_RULES = {
        "python": [
            r"\bpython\b.*?\b(?:scripts?|code|functions?|classes|modules?|decorators?|generators?|list\s+comprehensions?|multiprocessing|asyncio|type\s+hints?|virtualenv|pip|gil|pandas|numpy|scipy|flask|fastapi|django|pytest)\b",
            r"\b(?:scripts?|code|functions?|classes|modules?|decorators?|generators?|list\s+comprehensions?|multiprocessing|asyncio|type\s+hints?|virtualenv|pip|gil|pandas|numpy|scipy|flask|fastapi|django|pytest)\b.*?\bpython\b",
            r"\b(?:built|developed|implemented|wrote|created|analyzed)\s+.*?\b(?:using|with|in)\s+python\b",
            r"\bpython\s+(?:backend|service|api|pipeline|script|automation|package|library)\b",
        ],
        "sql": [
            r"\b(?:select|insert|update|delete)\b.*?\bfrom\b",
            r"\bsql\b.*?\b(?:queries|query|joins?|indexing|indexes?|group\s+by|where|schema|transactions?|acid|foreign\s+key|stored\s+procedures?|views?|database|relational)\b",
            r"\b(?:queries|query|joins?|indexing|indexes?|group\s+by|where|schema|transactions?|acid|foreign\s+key|stored\s+procedures?|views?)\b.*?\bsql\b",
            r"\b(?:optimized|wrote|executed|indexed)\s+(?:the\s+)?(?:sql\s+)?queries\b",
        ],
        "docker": [
            r"\bdocker\b.*?\b(?:container|containers|image|images|dockerfile|compose|docker-compose|volumes?|daemon|registry|multi-stage)\b",
            r"\b(?:container|containers|image|images|dockerfile|compose|docker-compose|volumes?|daemon|registry|multi-stage)\b.*?\bdocker\b",
            r"\b(?:containerized|packaged|deployed)\s+.*?\busing\s+docker\b",
        ],
        "react": [
            r"\breact\b.*?\b(?:components?|hooks?|usestate|useeffect|usememo|usecallback|props|state|virtual\s+dom|jsx|tsx|router|context\s+api|lifecycle)\b",
            r"\b(?:components?|hooks?|usestate|useeffect|usememo|usecallback|props|state|virtual\s+dom|jsx|tsx|router|context\s+api|lifecycle)\b.*?\breact\b",
            r"\b(?:built|developed|rendered)\s+.*?\breact\s+components?\b",
        ],
        "pytorch": [
            r"\bpytorch\b.*?\b(?:neural\s+network|architecture|loss|embeddings?|tensors?|model|dense|encoder|training|trained|cuda|dataloader|nn\.module|optimizer|autograd|backward)\b",
            r"\b(?:neural\s+network|architecture|loss|embeddings?|tensors?|model|dense|encoder|training|trained|cuda|dataloader|nn\.module|optimizer|autograd|backward)\b.*?\bpytorch\b",
            r"\b(?:trained|fine-tuned|evaluated)\s+.*?\busing\s+pytorch\b",
        ],
        "flask": [
            r"\bflask\b.*?\b(?:routes?|blueprints?|app\.route|request|jsonify|render_template|wsgi|gunicorn|endpoints?)\b",
            r"\b(?:routes?|blueprints?|app\.route|request|jsonify|render_template|wsgi|gunicorn|endpoints?)\b.*?\bflask\b",
            r"\b(?:built|implemented)\s+.*?\bflask\s+(?:api|backend|service|endpoints?)\b",
        ],
        "fastapi": [
            r"\bfastapi\b.*?\b(?:pydantic|routes?|endpoints?|async|uvicorn|depends|openapi|api)\b",
            r"\b(?:pydantic|routes?|endpoints?|async|uvicorn|depends|openapi|api)\b.*?\bfastapi\b",
        ],
        "git": [
            r"\bgit\b.*?\b(?:commit|commits|branch|branches|merge|rebase|push|pull\s+request|pr|repository|repo|conflict)\b",
            r"\b(?:commit|commits|branch|branches|merge|rebase|push|pull\s+request|pr|repository|repo|conflict)\b.*?\bgit\b",
        ],
        "linux": [
            r"\blinux\b.*?\b(?:shell|bash|kernel|cron|systemd|permissions?|chmod|grep|process|terminal|cli)\b",
            r"\b(?:shell|bash|kernel|cron|systemd|permissions?|chmod|grep|process|terminal|cli)\b.*?\blinux\b",
        ],
        "redis": [
            r"\bredis\b.*?\b(?:cache|caching|in-memory|ttl|key-value|pub/sub|cluster|eviction)\b",
            r"\b(?:cache|caching|in-memory|ttl|key-value|pub/sub|cluster|eviction)\b.*?\bredis\b",
        ],
        "kubernetes": [
            r"\b(?:kubernetes|k8s)\b.*?\b(?:pods?|deployments?|services?|cluster|ingress|replica|configmap)\b",
            r"\b(?:pods?|deployments?|services?|cluster|ingress|replica|configmap)\b.*?\b(?:kubernetes|k8s)\b",
        ],
        "aws": [
            r"\baws\b.*?\b(?:s3|ec2|lambda|rds|dynamodb|iam|cloudwatch|sqs|sns|vpc)\b",
            r"\b(?:s3|ec2|lambda|rds|dynamodb|iam|cloudwatch|sqs|sns|vpc)\b.*?\baws\b",
        ],
        "rest api": [
            r"\brest\s+api\b.*?\b(?:endpoints?|http|get|post|put|delete|json|status\s+codes?|payload|headers?)\b",
            r"\b(?:endpoints?|http|get|post|put|delete|json|status\s+codes?|payload|headers?)\b.*?\brest\s+api\b",
        ],
    }

    def _tokens(self, value: str) -> List[str]:
        return [
            token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", value or "")
            if len(token) > 2 and token.lower() not in self._STOPWORDS
        ]

    def _has_phrase(self, text: str, phrases: List[str]) -> bool:
        return any(re.search(r"(?<![a-z0-9])" + re.escape(p.lower()) + r"(?![a-z0-9])", text)
                   for p in phrases)

    def _framework_sections(self, fw_id: str, steps: List[Dict[str, Any]],
                            text: str, sentences: List[str], word_count: int):
        """Use distinct cues for each section; duplicate PREP points are positional."""
        lower = text.lower()
        addressed, missing = [], []

        if fw_id == "PREP":
            first_sentence = sentences[0].lower() if sentences else ""
            opening = word_count >= 8 and len(first_sentence.split()) >= 5
            reason = self._has_phrase(lower, [
                "because", "since", "the reason", "this matters because",
                "this is important because", "as a result of", "so that",
            ])
            example = self._has_phrase(lower, [
                "for example", "for instance", "in my project", "in the project",
                "such as", "one example", "specifically", "i applied",
            ])
            closing = self._has_phrase(lower, [
                "therefore", "overall", "in conclusion", "ultimately",
                "that is why", "this is why", "to summarize", "which is why",
            ])
            checks = [opening, reason, example, closing]
            labels = ["Point (Opening)", "Reason", "Example", "Point (Conclusion)"]
            for label, found in zip(labels, checks):
                (addressed if found else missing).append(label)
            return addressed, missing

        for step in steps:
            key = step["key"].lower()
            label = step.get("label") or step["key"]
            marker = bool(re.search(r"(?<![a-z])" + re.escape(key) + r"(?![a-z])", lower))
            cues = {
                "situation": ["when i", "during my", "at the time", "in my internship",
                              "in my project", "the project involved", "our team was"],
                "context": ["when i", "during my", "at the time", "in my project"],
                "task": ["my responsibility", "i was responsible", "the goal was",
                         "my task", "i needed to", "the objective was", "i was assigned"],
                "objective": ["the goal was", "my objective", "the objective was",
                              "i aimed to", "the requirement was"],
                "problem": ["the problem was", "we needed to", "the issue was",
                            "the requirement was", "the system needed"],
                "challenge": ["the challenge was", "the main challenge", "i encountered",
                              "the roadblock", "the issue was", "the problem was"],
                "obstacles": ["the obstacle", "the challenge", "we faced", "i faced"],
                "action": ["i implemented", "i built", "i developed", "i analyzed",
                           "i resolved", "i designed", "i tested", "i configured",
                           "i trained", "i evaluated", "i optimized", "i used"],
                "actions": ["i implemented", "i built", "i developed", "i analyzed",
                            "i resolved", "i designed", "i tested", "i configured"],
                "how": ["by using", "i implemented", "the process", "first", "then",
                        "the algorithm", "the implementation"],
                "result": ["resulted in", "as a result", "achieved", "reduced",
                           "improved", "delivered", "the outcome", "successfully",
                           "completed", "validated", "passed"],
                "results": ["resulted in", "as a result", "achieved", "reduced",
                            "improved", "delivered", "the outcome", "successfully",
                            "completed", "validated", "passed"],
                "learning": ["i learned", "i learnt", "my key takeaway",
                             "the lesson", "in the future", "i would now",
                             "this taught me"],
                "why": ["because", "this matters", "the reason", "it is important"],
                "what": ["is a", "refers to", "means", "is defined as"],
                "evidence": ["for example", "for instance", "specifically",
                             "the data", "the benchmark", "i measured"],
                "explanation": ["because", "this allows", "this helps", "due to",
                                "the reason", "which means"],
                "link": ["therefore", "overall", "this supports", "this aligns",
                         "in conclusion", "which connects"],
            }.get(key, ["for example", "because", "specifically"])

            found = marker or self._has_phrase(lower, cues)
            if key in ("action", "actions", "how") and not found:
                found = bool(re.search(
                    r"\bi\s+(?:created|wrote|integrated|compared|selected|deployed|debugged|"
                    r"processed|extracted|normalized|validated|maintained|collaborated)\b", lower
                ))
            (addressed if found else missing).append(label)

        return addressed, missing

    def evaluate_answer(
        self,
        question_data: Dict[str, Any],
        user_answer: str,
        framework_id: Optional[str] = None,
        candidate_evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deterministic, explainable answer evaluation across 6 explicit criteria.
        """
        text = (user_answer or "").strip()
        words = text.split()
        word_count = len(words)
        fw_id = framework_id or question_data.get("recommended_answer_framework", "STAR")
        fw = get_framework(fw_id)
        expected_points = question_data.get("expected_key_points") or question_data.get("expected_answer_evaluation_criteria") or []
        important_concepts = question_data.get("important_concepts") or []
        question_text = question_data.get("question_text", "")
        related_skill = question_data.get("related_skill") or question_data.get("topic") or ""

        # Normalize and check for blank or placeholder submissions
        normalized = re.sub(r"[^a-z0-9+#. ]", " ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        placeholder_only = bool(re.fullmatch(
            r"([a-z]{1,2}|test|testing|answer|n/?a|none|skip|placeholder|lorem ipsum)(?:\s+\1)*",
            normalized
        )) if normalized else True
        meaningful_tokens = self._tokens(text)
        insufficient = word_count < 5 or len(set(meaningful_tokens)) < 3 or placeholder_only

        if not text:
            status = "empty"
        elif insufficient:
            status = "insufficient"
        else:
            status = "evaluated"

        # Suggested improved structure guide (generic, zero-fabrication template)
        suggested_structure = {
            "framework_name": fw.get("name", fw_id),
            "framework_id": fw_id,
            "recommended_steps": [
                {
                    "step": s.get("label", s["key"]),
                    "guidance": s.get("guidance") or f"Address the {s.get('label', s['key'])} phase with specific facts from your background without inventing unverified claims."
                }
                for s in fw.get("steps", [])
            ],
            "safeguard_note": "Do not invent metrics or achievements you did not accomplish. Use placeholders [e.g., Your Metric] for details you have not verified."
        }

        if status != "evaluated":
            missing_sections = [(s.get("label") or s["key"]) for s in fw["steps"]]
            empty_crit_scores = {
                "relevance": {"score": 0.0, "status": "insufficient", "details": "Answer is missing or too brief to assess relevance."},
                "technical_accuracy": {"score": 0.0, "status": "unverifiable", "details": "No substantive technical claims to verify."},
                "concept_coverage": {"score": 0.0, "status": "insufficient", "details": "None of the expected concepts were addressed."},
                "clarity_structure": {"score": 0.0, "status": "insufficient", "details": "No structured framework demonstrated."},
                "specificity_examples": {"score": 0.0, "status": "insufficient", "details": "No concrete examples or metrics provided."},
                "evidence_consistency": {"score": 0.0, "status": "insufficient", "details": "No resume-grounded evidence provided."}
            }
            empty_claims = {
                "resume_supported_claims": [],
                "candidate_self_reported_claims": [],
                "unsupported_claims": [],
                "general_technical_explanations": [],
                "truthful_disclosures": [],
                "verified_technical_entities": [],
                "recognized_technical_entities": [],
                "unverifiable_technical_entities": []
            }
            return {
                "evaluator_label": self.LABEL,
                "disclaimer": self.DISCLAIMER,
                "word_count": word_count,
                "status": status,
                "completeness_level": "No Answer Provided" if not text else "Insufficient Detail",
                "overall_score": 0.0,
                "score": 0.0,
                "individual_criterion_scores": empty_crit_scores,
                "criterion_scores": empty_crit_scores,
                "claims_analysis": empty_claims,
                "framework_adherence": {
                    "framework": fw["name"], "framework_id": fw_id,
                    "sections_addressed": [], "sections_missing": missing_sections,
                    "adherence_pct": 0.0,
                },
                "key_point_coverage": {
                    "covered": [], "missing": expected_points, "coverage_pct": 0.0,
                },
                "important_concepts_coverage": {
                    "covered": [], "missing": important_concepts, "coverage_pct": 0.0,
                },
                "evidence_detected": False,
                "strengths": [],
                "areas_for_improvement": [
                    "This answer is too short to evaluate. Write at least 5 meaningful words; aim for 60-150 words and address the question directly."
                ],
                "missing_concepts": list(expected_points) + list(important_concepts),
                "improvement_suggestions": [
                    "Write a complete response addressing the core question prompt.",
                    f"Follow the {fw['name']} structure: {', '.join(missing_sections)}."
                ],
                "evidence_grounding_warnings": [],
                "evidence_warnings": [],
                "suggested_improved_answer_structure": suggested_structure,
                "actionable_feedback": (
                    "No answer was submitted." if not text else
                    "This looks like a placeholder or an incomplete answer. Add a direct response, a specific explanation, and an example."
                ),
            }

        lower = text.lower()

        # ---------------------------------------------------------------------
        # 1. Relevance Evaluation & Anti-Keyword-Stuffing Check
        # ---------------------------------------------------------------------
        q_tokens = set(self._tokens(question_text))
        answer_tokens = self._tokens(text)
        token_counts = Counter(answer_tokens)
        
        # Keyword stuffing detection: extreme repetition of identical tokens
        max_token_freq = max(token_counts.values()) if token_counts else 1
        is_keyword_stuffed = (
            len(answer_tokens) >= 10 and
            (max_token_freq / max(1, len(answer_tokens)) > 0.35 or
             len(set(answer_tokens)) / max(1, len(answer_tokens)) < 0.25)
        )

        relevant_matches = [t for t in set(answer_tokens) if t in q_tokens]
        if q_tokens:
            base_relevance = min(100.0, (len(relevant_matches) / max(1, min(len(q_tokens), 5))) * 100.0)
        else:
            base_relevance = 80.0

        if is_keyword_stuffed:
            relevance_score = max(10.0, round(base_relevance * 0.3, 1))
            relevance_details = "Warning: Repetitive keywords detected with low semantic variety. Points deducted for keyword stuffing."
        else:
            relevance_score = round(min(100.0, max(20.0, base_relevance)), 1)
            relevance_details = f"Directly addressed question prompt with {len(relevant_matches)} relevant core terms."

        # ---------------------------------------------------------------------
        # 2. Concept & Expected Points Coverage
        # ---------------------------------------------------------------------
        covered_points, missing_points = [], []
        for point in expected_points:
            point_tokens = list(dict.fromkeys(self._tokens(str(point))))
            hits = []
            for t in point_tokens:
                stem = t[:-1] if t.endswith("s") and len(t) > 3 else t
                if re.search(r"(?<![a-z0-9])" + re.escape(stem) + r"(?:s|es|ed|ing)?(?![a-z0-9])", lower):
                    hits.append(t)
            threshold = 1 if len(point_tokens) <= 4 else 2
            if len(hits) >= threshold:
                covered_points.append(str(point))
            else:
                missing_points.append(str(point))
        coverage_pct = round(100.0 * len(covered_points) / max(1, len(expected_points)), 1) if expected_points else 80.0

        covered_concepts, missing_concepts = [], []
        for concept in important_concepts:
            c_tokens = list(dict.fromkeys(self._tokens(str(concept))))
            hits = [t for t in c_tokens if re.search(
                r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", lower
            )]
            if c_tokens and len(hits) >= (1 if len(c_tokens) == 1 else min(2, len(c_tokens))):
                covered_concepts.append(str(concept))
            else:
                missing_concepts.append(str(concept))
        concept_coverage_pct = (
            round(100.0 * len(covered_concepts) / max(1, len(important_concepts)), 1)
            if important_concepts else 80.0
        )

        concept_score = round((coverage_pct * 0.7) + (concept_coverage_pct * 0.3), 1)

        # ---------------------------------------------------------------------
        # 3. Clarity & Structure (Framework Adherence)
        # ---------------------------------------------------------------------
        # Split sentences preserving decimal numbers (e.g. 99.99%, 3.5ms)
        sentences = [s.strip() for s in re.split(r"(?<!\d)[.!?]+(?!\d)\s*", text) if len(s.strip()) > 5]
        sections_addressed, sections_missing = self._framework_sections(
            fw_id, fw["steps"], text, sentences, word_count
        )
        total_steps = max(1, len(fw.get("steps", [])))
        framework_pct = round(100.0 * len(sections_addressed) / total_steps, 1)

        sentence_counts = Counter(s.lower() for s in sentences)
        has_duplicate_sentences = any(count > 1 for count in sentence_counts.values())

        clarity_score = framework_pct
        if has_duplicate_sentences:
            clarity_score = max(10.0, clarity_score - 15.0)

        # ---------------------------------------------------------------------
        # 4. Specificity & Concrete Examples
        # ---------------------------------------------------------------------
        has_metrics = bool(re.search(
            r"\b\d+(?:\.\d+)?\s*(?:%|ms|seconds?|minutes?|users|queries|gb|mb|records|rows|tests)(?![a-zA-Z0-9])",
            lower
        ))
        matched_entities = [entity for entity in self._TECHNICAL_ENTITIES
                            if re.search(r"(?<![a-z0-9])" + re.escape(entity) + r"(?![a-z0-9])", lower)]
        evidence_detected = has_metrics or bool(matched_entities)

        specificity_score = 30.0
        if matched_entities:
            specificity_score += min(40.0, len(matched_entities) * 15.0)
        if has_metrics:
            specificity_score += 30.0
        specificity_score = min(100.0, specificity_score)

        # ---------------------------------------------------------------------
        # 5. Technical Accuracy Where Verifiable
        # ---------------------------------------------------------------------
        # Differentiates verified technical usage from recognized keyword mentions and unverifiable domains
        verified_claims = []
        recognized_claims = []
        unverifiable_claims = []

        for ent in matched_entities:
            rules = self._TECH_VALIDATION_RULES.get(ent)
            if rules:
                if any(re.search(pat, lower) for pat in rules):
                    verified_claims.append(ent)
                else:
                    recognized_claims.append(ent)
            else:
                unverifiable_claims.append(ent)

        if verified_claims:
            tech_accuracy_status = "verified"
            tech_accuracy_score = 85.0
            verified_names = [e.capitalize() for e in verified_claims]
            tech_notes = f"Verified standard technical usage for: {', '.join(verified_names)}."
        elif recognized_claims:
            tech_accuracy_status = "recognized"
            tech_accuracy_score = 70.0
            rec_names = [e.capitalize() for e in recognized_claims]
            tech_notes = f"Recognized technical terms: {', '.join(rec_names)}. Contextual usage was not validated by automated rule verification."
        elif unverifiable_claims:
            tech_accuracy_status = "unverifiable"
            tech_accuracy_score = 65.0
            unv_names = [e.capitalize() for e in unverifiable_claims]
            tech_notes = f"Technical claims contain domain terms outside automated verification bank: {', '.join(unv_names)}; marked as unverifiable."
        else:
            tech_accuracy_status = "unverifiable"
            tech_accuracy_score = 60.0
            tech_notes = "Answer lacks concrete technical entities to verify against standard architectural knowledge."

        # ---------------------------------------------------------------------
        # 6. Evidence Consistency with Candidate Resume & Metric Grounding
        # ---------------------------------------------------------------------
        grounding_warnings = []
        resume_supported_claims = []
        candidate_self_reported_claims = []
        unsupported_claims = []
        general_technical_explanations = []
        truthful_disclosures = []

        resume_corpus = ""
        candidate_skills = set()
        if candidate_evidence:
            candidate_skills = {
                s.lower().strip() for s in (
                    candidate_evidence.get("skills", []) +
                    candidate_evidence.get("matched_skills", []) +
                    candidate_evidence.get("all_skills", [])
                )
            }
            proj_texts = [
                str(p.get("description", "")) + " " + str(p.get("exact_excerpt", "")) + " " + str(p.get("confirmed_details", ""))
                for p in candidate_evidence.get("projects", []) if isinstance(p, dict)
            ]
            intern_texts = [
                str(i.get("description", "")) + " " + str(i.get("exact_excerpt", "")) + " " + str(i.get("confirmed_details", ""))
                for i in candidate_evidence.get("internships", []) if isinstance(i, dict)
            ]
            resume_corpus = (
                " ".join(proj_texts + intern_texts + [
                    str(candidate_evidence.get("experience_summary", "")),
                    str(candidate_evidence.get("education", ""))
                ])
            ).lower()

            # Check unevidenced technologies
            for ent in matched_entities:
                if ent not in candidate_skills and not any(ent in cs for cs in candidate_skills):
                    grounding_warnings.append(
                        f"Technology '{ent.capitalize()}' is mentioned in your answer but was not evidenced in your resume. Be ready to explain how you learned or applied it."
                    )

        # Sentence-level achievement and metric grounding
        metric_pat = re.compile(
            r"\b\d+(?:\.\d+)?\s*(?:%|percent|ms|milliseconds?|seconds?|minutes?|hours?|users|queries|requests|req/s|rps|gb|mb|tb|records|rows|tests)(?![a-zA-Z0-9])",
            re.IGNORECASE
        )
        personal_pat = re.compile(
            r"\b(?:i|my\s+team|we|my\s+project|my\s+code|my\s+pipeline|my\s+implementation)\b.*?\b(?:achieved|improved|reduced|increased|boosted|optimized|scaled|cut|accelerated|delivered|handled|processed|served|decreased)\b",
            re.IGNORECASE
        )
        disclosure_pat = re.compile(
            r"\b(?:i\s+have\s+not\s+(?:yet\s+)?(?:deployed|worked|measured|used)|i\s+did\s+not\s+(?:measure|have|track)|this\s+was\s+(?:a\s+)?(?:coursework|academic|learning|practice|hobby)\s+project|do\s+not\s+have\s+(?:production|real-world)\s+metrics?|currently\s+learning|haven't\s+(?:yet\s+)?used)\b",
            re.IGNORECASE
        )
        general_pat = re.compile(
            r"\b(?:typically|generally|by\s+default|in\s+theory|standard|architecture|defined\s+as|complexity\s+is|runs\s+in|defaults?\s+to)\b",
            re.IGNORECASE
        )

        for s in sentences:
            s_lower = s.lower()
            has_m = bool(metric_pat.search(s_lower))
            is_personal = bool(personal_pat.search(s_lower)) or (
                bool(re.search(r"\b(?:i|my|we)\b", s_lower)) and
                bool(re.search(r"\b(?:achieved|improved|reduced|increased|boosted|optimized|scaled|cut|accelerated|delivered|handled|processed|served|decreased)\b", s_lower))
            )
            is_disclosure = bool(disclosure_pat.search(s_lower))
            is_general = bool(general_pat.search(s_lower))

            if is_disclosure:
                truthful_disclosures.append(s)
            elif is_personal and has_m:
                metric_matches = metric_pat.findall(s_lower)
                metric_in_resume = any(m.lower().strip() in resume_corpus for m in metric_matches) if resume_corpus else False
                if metric_in_resume:
                    resume_supported_claims.append(s)
                elif candidate_evidence and resume_corpus:
                    unsupported_claims.append(s)
                    grounding_warnings.append(
                        f"Achievement claim '{s}' asserts metrics not established by your submitted resume evidence. Avoid citing unverified numbers in interviews."
                    )
                else:
                    candidate_self_reported_claims.append(s)
            elif is_personal:
                candidate_self_reported_claims.append(s)
            elif has_m or is_general:
                general_technical_explanations.append(s)

        # Calculate consistency score
        if candidate_evidence:
            penalties = len(grounding_warnings) * 15.0
            consistency_score = max(40.0, 100.0 - penalties)
            if grounding_warnings:
                consistency_details = f"Caution: {len(grounding_warnings)} claim(s) or technology mention(s) lack grounding in your submitted resume."
                consistency_status = "warning"
            else:
                consistency_score = 95.0
                consistency_details = "Answer claims align cleanly with verified resume technologies and experiences."
                consistency_status = "pass"
        else:
            consistency_score = 85.0
            consistency_details = "Standard question evaluation (candidate resume evidence not attached)."
            consistency_status = "pass"

        # ---------------------------------------------------------------------
        # Overall Composite Score Calculation
        # ---------------------------------------------------------------------
        overall_score = round(
            (relevance_score * 0.20) +
            (tech_accuracy_score * 0.20) +
            (concept_score * 0.20) +
            (clarity_score * 0.15) +
            (specificity_score * 0.15) +
            (consistency_score * 0.10),
            1
        )

        # Format Criterion Scores
        criterion_scores = {
            "relevance": {
                "score": relevance_score,
                "weight_pct": 20,
                "status": "pass" if relevance_score >= 60 else "needs_improvement",
                "details": relevance_details
            },
            "technical_accuracy": {
                "score": tech_accuracy_score,
                "weight_pct": 20,
                "status": tech_accuracy_status,
                "details": tech_notes
            },
            "concept_coverage": {
                "score": concept_score,
                "weight_pct": 20,
                "status": "pass" if concept_score >= 60 else "needs_improvement",
                "details": f"Addressed {len(covered_points)} of {len(expected_points)} expected points ({coverage_pct}%)."
            },
            "clarity_structure": {
                "score": clarity_score,
                "weight_pct": 15,
                "status": "pass" if clarity_score >= 60 else "needs_improvement",
                "details": f"Addressed {len(sections_addressed)} of {total_steps} {fw['name']} sections ({framework_pct}%)."
            },
            "specificity_examples": {
                "score": specificity_score,
                "weight_pct": 15,
                "status": "pass" if specificity_score >= 60 else "needs_improvement",
                "details": "Includes concrete metrics and named tools." if evidence_detected else "Answer is conceptual; lacks quantified results or specific tools."
            },
            "evidence_consistency": {
                "score": consistency_score,
                "weight_pct": 10,
                "status": consistency_status,
                "details": consistency_details
            }
        }

        # ---------------------------------------------------------------------
        # Actionable Strengths and Improvements
        # ---------------------------------------------------------------------
        strengths, improvements = [], []
        if word_count >= 60:
            strengths.append(f"Useful response length ({word_count} words), allowing room for technical detail.")
        elif word_count < 35:
            improvements.append(f"Answer is brief ({word_count} words). Aim for 60-150 words for a detailed engineering response.")

        if expected_points and coverage_pct >= 60:
            strengths.append(
                f"Good question coverage: addressed {len(covered_points)} of {len(expected_points)} expected points ({coverage_pct}%)."
            )
        elif expected_points:
            improvements.append(
                "Address more of the expected points: " +
                (", ".join(missing_points[:3]) if missing_points else "add relevant detail") + "."
            )

        if covered_concepts:
            strengths.append("Included relevant concepts: " + ", ".join(covered_concepts[:4]) + ".")
        if missing_concepts:
            improvements.append("Concepts to explain more clearly: " + ", ".join(missing_concepts[:4]) + ".")

        if sections_missing:
            improvements.append(
                f"Your {fw['name']} structure could be clearer. Add: {', '.join(sections_missing)}."
            )
        else:
            strengths.append(f"Covered all {len(sections_addressed)} parts of the {fw['name']} framework.")

        if truthful_disclosures:
            strengths.append(f"Candid and honest disclosure: '{truthful_disclosures[0]}'. Interviewers value transparency regarding practical constraints.")

        if resume_supported_claims:
            strengths.append(f"Resume-grounded achievement: '{resume_supported_claims[0]}' is substantiated by your submitted project records.")

        if evidence_detected:
            evidence_parts = [e.capitalize() for e in (verified_claims or recognized_claims)[:4]]
            if has_metrics:
                evidence_parts.append("quantified result")
            strengths.append("Included concrete evidence: " + ", ".join(evidence_parts) + ".")
        else:
            improvements.append("Support your answer with a real project example, named tools, or a verified result.")

        if unsupported_claims:
            improvements.append("Avoid asserting unevidenced metrics or performance numbers that cannot be verified in your resume artifacts.")

        if has_duplicate_sentences:
            improvements.append("Avoid repeating the same sentence; make each sentence add new information.")

        if is_keyword_stuffed:
            improvements.append("Avoid repeating the same keywords; explain concepts in natural engineering sentences.")

        if not improvements:
            actionable = f"Strong structured answer. You covered {coverage_pct}% of expected question points and used relevant supporting evidence."
        else:
            actionable = improvements[0]

        completeness = (
            "Thorough" if word_count >= 90 and (not expected_points or coverage_pct >= 60)
            else "Moderate" if word_count >= 40 else "Brief"
        )

        claims_analysis = {
            "resume_supported_claims": resume_supported_claims,
            "candidate_self_reported_claims": candidate_self_reported_claims,
            "unsupported_claims": unsupported_claims,
            "general_technical_explanations": general_technical_explanations,
            "truthful_disclosures": truthful_disclosures,
            "verified_technical_entities": verified_claims,
            "recognized_technical_entities": recognized_claims,
            "unverifiable_technical_entities": unverifiable_claims
        }

        return {
            "evaluator_label": self.LABEL,
            "disclaimer": self.DISCLAIMER,
            "word_count": word_count,
            "status": "evaluated",
            "completeness_level": completeness,
            "overall_score": overall_score,
            "score": overall_score,
            "individual_criterion_scores": criterion_scores,
            "criterion_scores": criterion_scores,
            "claims_analysis": claims_analysis,
            "framework_adherence": {
                "framework": fw["name"], "framework_id": fw_id,
                "sections_addressed": sections_addressed,
                "sections_missing": sections_missing,
                "adherence_pct": framework_pct,
            },
            "key_point_coverage": {
                "covered": covered_points, "missing": missing_points,
                "coverage_pct": coverage_pct,
            },
            "important_concepts_coverage": {
                "covered": covered_concepts, "missing": missing_concepts,
                "coverage_pct": concept_coverage_pct,
            },
            "evidence_detected": evidence_detected,
            "has_repetition": has_duplicate_sentences or is_keyword_stuffed,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "missing_concepts": missing_points + missing_concepts,
            "improvement_suggestions": improvements,
            "evidence_grounding_warnings": grounding_warnings,
            "evidence_warnings": grounding_warnings,
            "suggested_improved_answer_structure": suggested_structure,
            "actionable_feedback": actionable,
        }
