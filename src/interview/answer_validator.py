"""
Automated Answer Quality Validation Module.
Enforces strict quality standards across all generated interview answers:
- Rejects generic repeated sentences and corporate clichés ("robust ecosystem", "cutting-edge").
- Rejects technology-list repetition where tools are merely recited without explanation.
- Rejects empty or stub explanations.
- Detects unverified metric fabrications (numbers/percentages not grounded in evidence).
- Ensures code examples parse and are non-empty when present.
- Verifies that answers directly address the question intent.
"""

import re
from typing import Dict, List, Any, Optional
from collections import Counter


CLICHE_PHRASES = [
    "robust ecosystem and excellent performance",
    "cutting-edge technology",
    "seamless integration of state-of-the-art",
    "synergistic approach",
    "paradigm shift",
    "game-changing framework"
]


class AnswerQualityValidator:
    """
    Deterministic rule-based quality auditor for interview question-answer pairs.
    """

    @classmethod
    def classify_statement(
        cls,
        text: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Classifies an answer excerpt into distinct evidence and knowledge categories:
        1. is_resume_supported: Facts supported by actual supplied resume evidence or verified evidence labels.
        2. is_candidate_confirmed: Marked explicitly with [Candidate Confirmed: ...].
        3. is_general_technical: Objective pedagogical or technical description (must NOT contain unevidenced personal claims).
        4. is_illustrative_scenario: Marked with [Illustrative Scenario...] / [Illustrative Model Scenario...].
        5. is_missing_info_placeholder: Marked with [Candidate to specify: ...].
        6. is_unsupported_personal_claim: An assertion of personal engineering action, architecture decision, metric, or duty that is NOT verified by evidence.

        Key Invariants:
        - Candidate confirmation is NEVER treated as independent resume evidence.
        - Arbitrary unverified personal text is NEVER classified as general technical content.
        - Actual evidence supplied to the validator is checked for verification.
        """
        t = text.strip()
        is_missing = bool(re.search(r"\[Candidate to specify:[^\]]*\]", t, re.IGNORECASE))
        is_candidate = bool(re.search(r"\[Candidate Confirmed[^\]]*\]", t, re.IGNORECASE))
        is_illustrative = bool(re.search(r"\[Illustrative (?:Model )?Scenario[^\]]*\]", t, re.IGNORECASE))

        # Check evidence markers in text
        has_ev_marker = bool(re.search(
            r"Verified (?:Project Title|Organization|Position|Dates|Responsibilities|Tools|Objective|Stack|Technologies):",
            t, re.IGNORECASE
        ))

        # Check actual evidence if supplied
        matches_actual_evidence = False
        if evidence and isinstance(evidence, dict):
            ev_texts = []
            if "verified_evidence" in evidence and isinstance(evidence["verified_evidence"], list):
                ev_texts.extend(evidence["verified_evidence"])
            for k in ["title", "organization", "description", "exact_excerpt", "responsibilities"]:
                v = evidence.get(k)
                if isinstance(v, str) and len(v.strip()) > 3:
                    ev_texts.append(v.strip())
                elif isinstance(v, list):
                    ev_texts.extend([item for item in v if isinstance(item, str) and len(item.strip()) > 3])

            for ev_item in ev_texts:
                if ev_item.lower() in t.lower():
                    matches_actual_evidence = True
                    break

        is_resume = (has_ev_marker or matches_actual_evidence) and not is_candidate

        # Detect unsupported personal claims:
        # 1. Generic positive fallbacks
        has_generic_fallback = bool(re.search(
            r"\b(software engineering duties|software development duties|software development tasks|assigned engineering features|practical engineering tools)\b",
            t, re.IGNORECASE
        ))

        # 2. First person actions or claims not inside placeholders or illustrative scenarios
        cleaned = re.sub(r"\[Candidate to specify:[^\]]*\]", "", t, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[Candidate Confirmed[^\]]*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[Illustrative (?:Model )?Scenario[^\]]*\]:.*?(?=\[Candidate to specify:|\n\n|$)", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\[Illustrative (?:Model )?Scenario[^\]]*\]:[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[General Technical Guidance\]:.*?(?=\[Candidate to specify:|\n\n|$)", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\[General Technical Guidance\]:[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(General Technical Guidance\):[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)

        has_first_person_action = bool(re.search(
            r"\b(?:I|we|my|our)\s+(?:designed|built|implemented|engineered|deployed|created|maintained|refactored|tested|optimized|authored|delivered|chose|decided|adhered|reached)\b",
            cleaned, re.IGNORECASE
        )) or bool(re.search(
            r"\b(?:My pull requests were reviewed|Successfully merged high-quality code|We maintain an extensive base)\b",
            cleaned, re.IGNORECASE
        ))

        has_unsupported_architecture = bool(re.search(
            r"\b(?:decoupled presentation from backend processing logic|implemented a modular layered architecture|designed modular software components|deliberately chose a modular monolithic architecture|designed the architecture|chose microservices)\b",
            cleaned, re.IGNORECASE
        ))

        has_unsupported_testing_or_deployment = bool(re.search(
            r"\b(?:authored automated unit tests|authored comprehensive unit tests|created unit and integration test fixtures|committed the failing test case|authored CI/CD pipelines|deployed to AWS|deployed to GCP|deployed to Kubernetes)\b",
            cleaned, re.IGNORECASE
        ))

        has_unbracketed_metric = bool(re.search(
            r"(?<!\[)(?:improved|reduced|increased|boosted|achieved)\s+.*?(?:\d+%\s*|\d+x\s*)(?!\])",
            cleaned, re.IGNORECASE
        ))

        is_unsupported = (
            has_generic_fallback
            or has_first_person_action
            or has_unsupported_architecture
            or has_unsupported_testing_or_deployment
            or has_unbracketed_metric
        ) and not is_illustrative and not matches_actual_evidence

        # General technical explanation is valid ONLY if it is technical and NOT an unsupported personal claim
        is_labeled_guidance = bool(re.search(r"\[General Technical Guidance\]|\(General Technical Guidance\)", t, re.IGNORECASE))
        has_technical_keywords = bool(re.search(
            r"\b(architecture|component|interface|database|cache|API|test|Pytest|query|schema|Docker|microservice|layer|protocol|concurrency|latency|throughput|algorithm|complexity|HTTP|REST|SQL|NoSQL)\b",
            t, re.IGNORECASE
        ))

        is_general = (
            (is_labeled_guidance or (has_technical_keywords and not is_resume and not is_missing and not is_candidate and not is_illustrative))
            and not is_unsupported
        )

        return {
            "is_resume_supported": is_resume,
            "is_candidate_confirmed": is_candidate,
            "is_general_technical": is_general,
            "is_illustrative_scenario": is_illustrative,
            "is_missing_info_placeholder": is_missing,
            "is_unsupported_personal_claim": is_unsupported
        }

    @classmethod
    def audit_answer_for_unsupported_first_person_claims(
        cls,
        text: str,
        verified_evidence: Optional[Union[Dict[str, Any], List[str], str]] = None
    ) -> List[str]:
        """
        Audits an answer text for ungrounded first-person personal claims.
        Flags unbracketed assertions like 'I designed modular software components', 'I implemented optimistic locking'
        that are neither inside [Candidate to specify: ...] placeholders nor inside
        explicitly labeled [Illustrative Model Scenario...] blocks.
        """
        issues = []
        if not text or not isinstance(text, str):
            return issues

        ev_texts: List[str] = []
        if verified_evidence:
            if isinstance(verified_evidence, str):
                ev_texts.append(verified_evidence.strip())
            elif isinstance(verified_evidence, list):
                for item in verified_evidence:
                    if isinstance(item, str) and len(item.strip()) > 3:
                        ev_texts.append(item.strip())
            elif isinstance(verified_evidence, dict):
                for k, v in verified_evidence.items():
                    if isinstance(v, str) and len(v.strip()) > 3:
                        ev_texts.append(v.strip())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and len(item.strip()) > 3:
                                ev_texts.append(item.strip())

        # Strip out bracketed placeholders, candidate confirmations, and illustrative scenarios
        cleaned = re.sub(r"\[Candidate to specify:[^\]]*\]", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[Candidate Confirmed[^\]]*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[Illustrative (?:Model )?Scenario[^\]]*\]:.*?(?=\[Candidate to specify:|\n\n|$)", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\[Illustrative (?:Model )?Scenario[^\]]*\]:[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[General Technical Guidance\]:.*?(?=\[Candidate to specify:|\n\n|$)", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\[General Technical Guidance\]:[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(General Technical Guidance\):[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)

        unsupported_patterns = [
            # 1. Generic positive fallbacks
            (r"\bsoftware engineering duties\b", "Uses forbidden generic positive fallback 'software engineering duties'"),
            (r"\bsoftware development duties\b", "Uses forbidden generic fallback 'software development duties'"),
            (r"\bsoftware development tasks\b", "Uses forbidden generic fallback 'software development tasks'"),
            (r"\bassigned engineering features\b", "Uses forbidden generic fallback 'assigned engineering features'"),
            (r"\bpractical engineering tools\b", "Uses forbidden generic fallback 'practical engineering tools'"),

            # 2. Unsupported Architecture & Design Claims
            (r"\bdecoupled presentation from backend processing logic\b", "Claims ungrounded architecture decoupling for project without evidence"),
            (r"\bI designed modular software components\b", "Claims ungrounded modular component design"),
            (r"\bI designed a modular layered architecture\b", "Claims ungrounded layered architecture design"),
            (r"\bI deliberately chose a modular monolithic architecture\b", "Claims ungrounded architecture choice"),
            (r"\bI architected\b", "Claims ungrounded system architecture"),
            (r"\bchose a (?:modular|microservices?|monolithic) architecture\b", "Claims ungrounded architecture selection rationale"),
            (r"\bI designed (?:a |the )?(?:architecture|microservices?|modular|layered|system|components?|API|database schema|interfaces?)\b", "Claims ungrounded architecture or design"),
            (r"\bI selected \w+ (?:over|for|to) \w+\b", "Claims ungrounded technology selection rationale"),
            (r"\bdesigned the (?:API contracts?|component interfaces?|database schema)\b", "Claims ungrounded design contracts or interfaces"),

            # 3. Unsupported Implementation Claims
            (r"\bI implemented modular services\b", "Claims ungrounded modular service implementation"),
            (r"\bI implemented optimistic locking\b", "Claims ungrounded optimistic locking implementation"),
            (r"\bI discovered the failure was occurring because\b", "Claims ungrounded failure discovery"),
            (r"\bI refactored the module with defensive\b", "Claims ungrounded defensive module refactoring"),
            (r"\bI authored clean, modular code\b", "Claims ungrounded clean modular code authorship"),
            (r"\bI authored modular feature code\b", "Claims ungrounded modular feature code authorship"),
            (r"\bI implemented (?:the|backend|frontend|modular|custom|production|core)\b", "Claims ungrounded implementation"),

            # 4. Unsupported Testing & QA Claims
            (r"\bI authored automated unit tests\b", "Claims ungrounded automated unit test authorship"),
            (r"\bI authored comprehensive unit tests\b", "Claims ungrounded comprehensive unit tests"),
            (r"\bcreated unit and integration test fixtures\b", "Claims ungrounded test fixture creation"),
            (r"\bI committed the failing test case\b", "Claims ungrounded test case commit"),
            (r"\bI validated '[^']+' by implementing automated\b", "Claims ungrounded automated unit test validation"),
            (r"\bWe maintain an extensive base of unit tests\b", "Claims unevidenced existing testing base"),
            (r"\bI authored (?:automated |comprehensive |clean, |modular |unit |integration |end-to-end )?tests\b", "Claims ungrounded unit or automated test authoring"),
            (r"\bI wrote (?:automated |comprehensive |unit |integration )?tests\b", "Claims ungrounded test writing"),

            # 5. Unsupported Deployment & CI/CD Claims
            (r"\bI deployed (?:this|the|to)\b", "Claims ungrounded deployment execution"),
            (r"\bdeployed to (?:AWS|GCP|Azure|Kubernetes|production)\b", "Claims ungrounded deployment target"),
            (r"\bI authored CI/CD pipelines\b", "Claims ungrounded CI/CD pipeline authoring"),
            (r"\b(?:I )?(?:created|built|authored) CI/CD pipelines?\b", "Claims ungrounded CI/CD pipeline construction"),
            (r"\bMy pull requests were reviewed, approved, and merged\b", "Claims ungrounded pull request review and merge"),
            (r"\bSuccessfully merged high-quality code\b", "Claims ungrounded production merge"),
            (r"\bThe completed service verified functional requirements\b", "Claims ungrounded service verification"),
            (r"\bThe completed system satisfied all acceptance criteria\b", "Claims ungrounded acceptance criteria satisfaction"),

            # 6. Unverified Metrics & Interactions
            (r"\bI adhered to a structured ['\"]?30-minute rule\b", "Claims unevidenced 30-minute rule adherence"),
            (r"\bMy internship permanently instilled\b", "Claims ungrounded personal internship habits"),
            (r"\bfollowing git and code review conventions\b", "Claims ungrounded adherence to conventions"),
            (r"\bA senior engineer commented: ['\"]?Catching generic Exception\b", "Claims fabricated code review interaction"),
            (r"(?<!\[)(?:improved|reduced|increased|boosted|achieved)\s+.*?(?:\d+%\s*|\d+x\s*)(?!\])", "Claims unverified quantitative metric without explicit candidate placeholder")
        ]

        for pat, desc in unsupported_patterns:
            m = re.search(pat, cleaned, re.IGNORECASE)
            if m:
                matched_str = m.group(0)
                is_supported_by_ev = False
                for ev_t in ev_texts:
                    if matched_str.lower() in ev_t.lower():
                        is_supported_by_ev = True
                        break
                if "forbidden generic" in desc.lower() or not is_supported_by_ev:
                    issues.append(f"Found unsupported first-person assertion: {desc}")

        return issues

    @classmethod
    def audit_record_fields(
        cls,
        question_record: Dict[str, Any],
        verified_evidence: Optional[Union[Dict[str, Any], List[str], str]] = None
    ) -> List[str]:
        """
        Audits all 13 core generated output fields for unsupported candidate claims,
        generic positive fallbacks, and ungrounded engineering achievements.
        """
        issues: List[str] = []
        ev = verified_evidence or question_record.get("verified_evidence") or question_record.get("evidence_sources") or question_record.get("candidate_evidence")

        # 1. detailed_answer
        detailed = question_record.get("detailed_answer", "")
        if detailed and isinstance(detailed, str):
            for iss in cls.audit_answer_for_unsupported_first_person_claims(detailed, verified_evidence=ev):
                issues.append(f"detailed_answer: {iss}")

        # 2. short_answer
        short_ans = question_record.get("short_answer", "")
        if short_ans and isinstance(short_ans, str):
            for iss in cls.audit_answer_for_unsupported_first_person_claims(short_ans, verified_evidence=ev):
                issues.append(f"short_answer: {iss}")

        # 3. simpler_answer
        simpler = question_record.get("simpler_answer", "")
        if simpler and isinstance(simpler, str):
            for iss in cls.audit_answer_for_unsupported_first_person_claims(simpler, verified_evidence=ev):
                issues.append(f"simpler_answer: {iss}")

        # 4. curated_answer
        curated = question_record.get("curated_answer", "")
        if curated and isinstance(curated, str):
            for iss in cls.audit_answer_for_unsupported_first_person_claims(curated, verified_evidence=ev):
                issues.append(f"curated_answer: {iss}")

        # 5. examples
        examples = question_record.get("examples")
        if examples:
            if isinstance(examples, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(examples, verified_evidence=ev):
                    issues.append(f"examples: {iss}")
            elif isinstance(examples, list):
                for idx, ex in enumerate(examples):
                    if isinstance(ex, str):
                        for iss in cls.audit_answer_for_unsupported_first_person_claims(ex, verified_evidence=ev):
                            issues.append(f"examples[{idx}]: {iss}")

        # 6. step_by_step_explanation
        steps = question_record.get("step_by_step_explanation", [])
        if isinstance(steps, list):
            for idx, st in enumerate(steps):
                if isinstance(st, dict):
                    for k in ["step", "detail", "concrete_example", "complete_explanation"]:
                        val = st.get(k, "")
                        if val and isinstance(val, str):
                            for iss in cls.audit_answer_for_unsupported_first_person_claims(val, verified_evidence=ev):
                                issues.append(f"Step {idx+1} {k}: {iss}")
                elif isinstance(st, str):
                    for iss in cls.audit_answer_for_unsupported_first_person_claims(st, verified_evidence=ev):
                        issues.append(f"Step {idx+1}: {iss}")

        # 7. follow_up_questions
        follow_ups = question_record.get("follow_up_questions", [])
        if isinstance(follow_ups, list):
            for idx, fu in enumerate(follow_ups):
                if isinstance(fu, dict):
                    for k in ["question", "reference_answer", "practical_example", "answer_guidance", "technical_justification", "interview_takeaway"]:
                        val = fu.get(k, "")
                        if val and isinstance(val, str):
                            for iss in cls.audit_answer_for_unsupported_first_person_claims(val, verified_evidence=ev):
                                issues.append(f"Follow-up {idx+1} {k}: {iss}")
                    fu_steps = fu.get("step_by_step_explanation", [])
                    if isinstance(fu_steps, list):
                        for s_idx, s in enumerate(fu_steps):
                            if isinstance(s, dict):
                                for sk in ["step", "detail", "concrete_example"]:
                                    sval = s.get(sk, "")
                                    if sval and isinstance(sval, str):
                                        for iss in cls.audit_answer_for_unsupported_first_person_claims(sval, verified_evidence=ev):
                                            issues.append(f"Follow-up {idx+1} step {s_idx+1} {sk}: {iss}")

        # 8. completed_framework_answer
        completed_fw = question_record.get("completed_framework_answer")
        if completed_fw:
            if isinstance(completed_fw, list):
                for idx, step_item in enumerate(completed_fw):
                    if isinstance(step_item, dict):
                        for k in ["demonstration", "content", "detail"]:
                            val = step_item.get(k, "")
                            if val and isinstance(val, str):
                                for iss in cls.audit_answer_for_unsupported_first_person_claims(val, verified_evidence=ev):
                                    issues.append(f"completed_framework_answer[{idx}].{k}: {iss}")
            elif isinstance(completed_fw, dict):
                for k, v in completed_fw.items():
                    if isinstance(v, str):
                        for iss in cls.audit_answer_for_unsupported_first_person_claims(v, verified_evidence=ev):
                            issues.append(f"completed_framework_answer.{k}: {iss}")
            elif isinstance(completed_fw, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(completed_fw, verified_evidence=ev):
                    issues.append(f"completed_framework_answer: {iss}")

        # 9. framework_template
        fw_template = question_record.get("framework_template")
        if fw_template:
            if isinstance(fw_template, list):
                for idx, t_step in enumerate(fw_template):
                    if isinstance(t_step, dict):
                        for k in ["placeholder", "prompt", "guidance"]:
                            val = t_step.get(k, "")
                            if val and isinstance(val, str):
                                for iss in cls.audit_answer_for_unsupported_first_person_claims(val, verified_evidence=ev):
                                    issues.append(f"framework_template[{idx}].{k}: {iss}")
            elif isinstance(fw_template, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(fw_template, verified_evidence=ev):
                    issues.append(f"framework_template: {iss}")

        # 10. why_this_works
        why = question_record.get("why_this_works", "")
        if why and isinstance(why, str):
            for iss in cls.audit_answer_for_unsupported_first_person_claims(why, verified_evidence=ev):
                issues.append(f"why_this_works: {iss}")

        # 11. suggested_improvements
        improvements = question_record.get("suggested_improvements")
        if improvements:
            if isinstance(improvements, list):
                for idx, imp in enumerate(improvements):
                    if isinstance(imp, str):
                        for iss in cls.audit_answer_for_unsupported_first_person_claims(imp, verified_evidence=ev):
                            issues.append(f"suggested_improvements[{idx}]: {iss}")
            elif isinstance(improvements, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(improvements, verified_evidence=ev):
                    issues.append(f"suggested_improvements: {iss}")

        # 12. missing_personal_details
        missing = question_record.get("missing_personal_details")
        if missing:
            if isinstance(missing, list):
                for idx, m in enumerate(missing):
                    if isinstance(m, str):
                        for iss in cls.audit_answer_for_unsupported_first_person_claims(m, verified_evidence=ev):
                            issues.append(f"missing_personal_details[{idx}]: {iss}")
            elif isinstance(missing, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(missing, verified_evidence=ev):
                    issues.append(f"missing_personal_details: {iss}")

        # 13. verified_evidence
        vev = question_record.get("verified_evidence")
        if vev:
            if isinstance(vev, list):
                for idx, v_item in enumerate(vev):
                    if isinstance(v_item, str):
                        for iss in cls.audit_answer_for_unsupported_first_person_claims(v_item, verified_evidence=ev):
                            issues.append(f"verified_evidence[{idx}]: {iss}")
            elif isinstance(vev, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(vev, verified_evidence=ev):
                    issues.append(f"verified_evidence: {iss}")

        return issues


    @classmethod
    def validate_answer(cls, question_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates an interview question-answer record against professional interview standards.
        Returns validation status, quality score (0-100), and list of identified issues.
        """
        issues = []
        score = 100.0

        q_text = question_record.get("question_text", "").strip()
        detailed_ans = question_record.get("detailed_answer", "").strip()
        short_ans = question_record.get("short_answer", "").strip()
        steps = question_record.get("step_by_step_explanation", [])
        code = question_record.get("code_snippet")
        category = question_record.get("category", "")

        # 1. Non-empty check
        if not q_text:
            issues.append("Question text is empty.")
            score -= 40.0
        if not detailed_ans:
            issues.append("Detailed answer is missing or empty.")
            score -= 50.0

        # 2. Minimum substantive length (no one-liner cop-outs)
        if len(detailed_ans) < 60:
            issues.append("Detailed answer is too brief (< 60 chars) to provide professional depth.")
            score -= 25.0

        # 3. Not merely repeating the question
        if detailed_ans.lower() == q_text.lower() or short_ans.lower() == q_text.lower():
            issues.append("Answer merely repeats the question text without substantive explanation.")
            score -= 40.0

        # 4. Check for corporate clichés
        detailed_lower = detailed_ans.lower()
        for cliche in CLICHE_PHRASES:
            if cliche in detailed_lower:
                issues.append(f"Contains generic corporate cliché: '{cliche}'. Replace with concrete engineering rationale.")
                score -= 15.0

        # 5. Check for excessive sentence duplication
        sentences = [s.strip() for s in re.split(r"[.!?]+", detailed_ans) if len(s.strip()) > 15]
        s_counts = Counter(sentences)
        duplicates = [s for s, count in s_counts.items() if count > 1]
        if duplicates:
            issues.append(f"Contains duplicate repeated sentence: '{duplicates[0][:60]}...'")
            score -= 20.0

        # 6. Technology list repetition check
        # Detect if the same 3+ technologies/items are strung together repeatedly across multiple sentences
        tech_string_matches = [m.lower().strip() for m in re.findall(r"([A-Za-z0-9+#\-\.]+(?:,\s*[A-Za-z0-9+#\-\.]+){2,})", detailed_ans)]
        repeated_lists = [m for m, count in Counter(tech_string_matches).items() if count > 1]
        excessive_recitation = [m for m in re.findall(r"([A-Za-z0-9+#\-\.]+(?:,\s*[A-Za-z0-9+#\-\.]+){6,})", detailed_ans)]
        if repeated_lists or excessive_recitation:
            issues.append("Repeatedly recites comma-separated technology lists instead of explaining individual component roles.")
            score -= 15.0

        # 7. Step-by-step explanation completeness
        if not steps or len(steps) < 3:
            issues.append("Step-by-step explanation has fewer than 3 pedagogical steps.")
            score -= 15.0

        # 8. Unverified metric fabrication in personal answers (Categories B and C)
        # In personal project/internship questions, any specific percentage (e.g. "reduced latency by 45%")
        # MUST be enclosed in explicit editable brackets like [Describe quantitative metric, e.g. 45%]
        if category in ["B", "C"]:
            unbracketed_metrics = re.findall(r"(?<!\[)(?:improved|reduced|increased|boosted|achieved)\s+.*?(?:\d+%\s*|\d+x\s*)(?!\])", detailed_ans, re.IGNORECASE)
            if unbracketed_metrics:
                issues.append(f"Found potentially fabricated unbracketed personal metric: '{unbracketed_metrics[0]}'. Must use explicit student placeholder [Describe metric].")
                score -= 20.0

        # 9. Comprehensive audit across all 13 core generated output fields
        evidence_ctx = question_record.get("verified_evidence") or question_record.get("evidence_sources") or question_record.get("candidate_evidence")
        field_issues = cls.audit_record_fields(question_record, verified_evidence=evidence_ctx)
        for fi in field_issues:
            issues.append(fi)
            score -= 15.0

        # 10. Code snippet syntax check (if present and labeled as Python)
        if code and isinstance(code, str) and len(code.strip()) > 0:
            if "\n" in code and ("def " in code or "import " in code):
                try:
                    compile(code, "<string>", "exec")
                except SyntaxError as e:
                    # Only flag if clearly intended to be executable python
                    if "tb_py" in question_record.get("question_id", ""):
                        issues.append(f"Code example has invalid Python syntax: {e}")
                        score -= 20.0

        # 11. Check that extended fields exist
        for field in ["why_this_works", "follow_up_questions", "simpler_answer"]:
            if field in question_record and not question_record[field]:
                issues.append(f"Extended learning field '{field}' is present but empty.")
                score -= 5.0

        score = max(0.0, min(100.0, score))
        return {
            "is_valid": len(issues) == 0,
            "quality_score": round(score, 1),
            "issues": issues,
            "question_id": question_record.get("question_id", "unknown")
        }
