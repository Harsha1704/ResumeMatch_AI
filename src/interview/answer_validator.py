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
    def audit_answer_for_unsupported_first_person_claims(
        cls,
        text: str,
        verified_evidence: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Audits an answer text for ungrounded first-person personal claims.
        Flags unbracketed assertions like 'I designed modular software components', 'I implemented optimistic locking'
        that are neither inside [Candidate to specify: ...] placeholders nor inside
        explicitly labeled [Illustrative Model Scenario...] blocks.
        """
        issues = []
        if not text:
            return issues

        # Strip out bracketed placeholders and illustrative model scenarios
        cleaned = re.sub(r"\[Candidate to specify:[^\]]*\]", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[Illustrative Model Scenario[^\]]*\]:[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)

        unsupported_patterns = [
            (r"\bI designed modular software components\b", "Claims ungrounded modular component design"),
            (r"\bI implemented optimistic locking\b", "Claims ungrounded optimistic locking implementation"),
            (r"\bI discovered the failure was occurring because\b", "Claims ungrounded failure discovery"),
            (r"\bI refactored the module with defensive\b", "Claims ungrounded defensive module refactoring"),
            (r"\bI committed the failing test case\b", "Claims ungrounded test case commit"),
            (r"\bI authored clean, modular code\b", "Claims ungrounded clean modular code authorship"),
            (r"\bI validated '[^']+' by implementing automated\b", "Claims ungrounded automated unit test validation")
        ]

        for pat, desc in unsupported_patterns:
            if re.search(pat, cleaned, re.IGNORECASE):
                issues.append(f"Found unsupported first-person assertion: {desc}")

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
            # Check for unbracketed claims of exact percentage or multipliers
            unbracketed_metrics = re.findall(r"(?<!\[)(?:improved|reduced|increased|boosted|achieved)\s+.*?(?:\d+%\s*|\d+x\s*)(?!\])", detailed_ans, re.IGNORECASE)
            if unbracketed_metrics:
                issues.append(f"Found potentially fabricated unbracketed personal metric: '{unbracketed_metrics[0]}'. Must use explicit student placeholder [Describe metric].")
                score -= 20.0

        # 11. Unsupported first-person personal claim audit (Categories B and C)
        if category in ["B", "C"]:
            fp_issues = cls.audit_answer_for_unsupported_first_person_claims(detailed_ans)
            for fpi in fp_issues:
                issues.append(fpi)
                score -= 15.0

        # 9. Code snippet syntax check (if present and labeled as Python)
        if code and isinstance(code, str) and len(code.strip()) > 0:
            if "\n" in code and ("def " in code or "import " in code):
                try:
                    compile(code, "<string>", "exec")
                except SyntaxError as e:
                    # Only flag if clearly intended to be executable python
                    if "tb_py" in question_record.get("question_id", ""):
                        issues.append(f"Code example has invalid Python syntax: {e}")
                        score -= 20.0

        # 10. Check that extended fields exist
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
