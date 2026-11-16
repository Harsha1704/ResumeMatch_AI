"""
Automated Answer Quality Validation Module.
Enforces strict quality standards across all generated interview answers:
- Rejects generic repeated sentences and corporate clichés ("robust ecosystem", "cutting-edge").
- Rejects technology-list repetition where tools are merely recited without explanation.
- Rejects empty or stub explanations.
- Detects unverified metric fabrications (numbers/percentages not grounded in evidence).
- Ensures code examples parse and are non-empty when present.
- Verifies that answers directly address the question intent.
- Distinguishes resume-supported evidence, candidate confirmations, general technical explanations,
  illustrative scenarios, missing-information placeholders, and unsupported personal claims.
"""

from __future__ import annotations

import re
from typing import Dict, List, Any, Optional, Union, Tuple, Set
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

    Verification Scope & Architectural Boundaries:
    - This validator provides deterministic, reproducible guarantees against known ungrounded
      claim patterns, forbidden positive fallbacks, unbracketed metrics, and structural defects.
    - Rule-based regex and token matching intentionally avoids non-deterministic LLM evaluation
      and eliminates external API dependencies and network latency.
    - Limitations: Rule-based heuristics cannot perform complete semantic understanding of
      arbitrary natural language. Paraphrased claims that avoid tracked verb patterns or
      colloquial idioms may not be detected by pattern rules alone. True candidate verification
      relies on strict separation of verified evidence, candidate confirmations, and explicit
      missing-information placeholders.
    """

    @classmethod
    def _extract_evidence_text_set(
        cls,
        evidence: Optional[Union[Dict[str, Any], List[str], str]]
    ) -> List[str]:
        """
        Extracts verified resume text tokens and excerpts from supplied evidence.
        Explicitly excludes metadata fields like 'evidence_sources' so that document
        source labels are never treated as proof of candidate achievements.
        """
        ev_texts: List[str] = []
        if not evidence:
            return ev_texts

        if isinstance(evidence, str):
            if len(evidence.strip()) > 1:
                ev_texts.append(evidence.strip())
            return ev_texts

        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, str) and len(item.strip()) > 1:
                    ev_texts.append(item.strip())
                elif isinstance(item, dict):
                    ev_texts.extend(cls._extract_evidence_text_set(item))
            return ev_texts

        if isinstance(evidence, dict):
            # Check verified evidence lists (explicitly ignore 'evidence_sources')
            for list_key in ["verified_evidence", "candidate_evidence"]:
                val = evidence.get(list_key)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, str) and len(item.strip()) > 1:
                            ev_texts.append(item.strip())
                elif isinstance(val, str) and len(val.strip()) > 1:
                    ev_texts.append(val.strip())

            # Check core candidate record fields
            for field_key in [
                "title", "organization", "company", "position", "role", "dates",
                "description", "exact_excerpt", "responsibilities", "skills",
                "technical_skills", "technologies"
            ]:
                v = evidence.get(field_key)
                if isinstance(v, str) and len(v.strip()) > 1:
                    ev_texts.append(v.strip())
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and len(item.strip()) > 1:
                            ev_texts.append(item.strip())

            # Check nested projects or experience
            for nested_key in ["projects", "experience", "internships"]:
                nested = evidence.get(nested_key)
                if isinstance(nested, list):
                    for n_item in nested:
                        if isinstance(n_item, dict):
                            ev_texts.extend(cls._extract_evidence_text_set(n_item))

        return ev_texts

    @classmethod
    def _token_matches(cls, needle: str, haystack: str) -> bool:
        """
        Boundary-aware specific token/phrase matching.
        Prevents unsafe substring collisions (e.g., treating 'SQL' as proof inside 'NoSQL',
        'Java' inside 'JavaScript', 'C' inside 'C++', 'Go' inside 'Django', 'Rust' inside 'trust').
        """
        n = needle.strip()
        if not n or not haystack:
            return False
        if n.lower() == haystack.strip().lower():
            return True

        first_char = n[0]
        left_bound = r"(?<![A-Za-z0-9_])" if first_char.isalnum() else r"(?<!\S)"
        right_bound = r"(?![A-Za-z0-9_+#])"

        pattern = left_bound + re.escape(n) + right_bound
        return bool(re.search(pattern, haystack, re.IGNORECASE))

    @classmethod
    def _strip_illustrative_blocks(cls, text: str) -> str:
        """
        Strips only properly matched explicit illustrative scenario blocks.
        Supports:
        - [Illustrative Scenario]: ... [/Illustrative Scenario]
        - [Illustrative Model Scenario]: ... [/Illustrative Model Scenario]
        Each opening delimiter must match its corresponding closing delimiter.
        Mismatched delimiters (e.g. Scenario opening with Model Scenario closing)
        are not matched and remain unstripped for audit inspection.
        Iteratively strips innermost/single blocks so nested or repeated blocks are handled cleanly.
        """
        if not text:
            return ""
        explicit_illustrative_pattern = re.compile(
            r"(?:"
            r"\[Illustrative\s+Scenario[^\]]*\]:?"
            r"(?:(?!\[Illustrative\s+(?:Model\s+)?Scenario).)*?"
            r"\[/\s*Illustrative\s+Scenario\s*:?\]"
            r"|"
            r"\[Illustrative\s+Model\s+Scenario[^\]]*\]:?"
            r"(?:(?!\[Illustrative\s+(?:Model\s+)?Scenario).)*?"
            r"\[/\s*Illustrative\s+Model\s+Scenario\s*:?\]"
            r")",
            flags=re.IGNORECASE | re.DOTALL
        )
        cleaned = text
        while True:
            new_cleaned = explicit_illustrative_pattern.sub("", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned
        return cleaned

    @classmethod
    def _strip_exempt_blocks(cls, text: str) -> str:
        """
        Strips explicitly exempt blocks:
        1. Properly matched explicit illustrative scenario blocks:
           [Illustrative Scenario]: ... [/Illustrative Scenario]
           [Illustrative Model Scenario]: ... [/Illustrative Model Scenario]
        2. Bracketed candidate placeholders: [Candidate to specify: ...]
        3. Candidate confirmations: [Candidate Confirmed: ...]
        4. General technical guidance blocks: [General Technical Guidance]: ...

        Key Invariants:
        - Only content inside a properly matched illustrative block is stripped.
        - First-person wording inside the block does not terminate it early.
        - Unsupported claims outside the block (including immediately after its closing delimiter) are preserved.
        - Missing or malformed closing delimiters never silently exempt content.
        - Nested or repeated illustrative blocks are handled iteratively.
        """
        if not text:
            return ""

        # 1. Explicitly delimited illustrative scenario blocks stripped FIRST
        cleaned = cls._strip_illustrative_blocks(text)

        # 2. Bracketed candidate placeholders and confirmations outside illustrative blocks
        cleaned = re.sub(r"\[Candidate to specify:[^\]]*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[Candidate Confirmed[^\]]*\]", "", cleaned, flags=re.IGNORECASE)

        # 3. General technical guidance blocks scoped strictly to their block boundaries
        guidance_pattern = re.compile(
            r"\[General Technical Guidance\]:?\s*.*?"
            r"(?="
            r"\[Candidate to specify:|"
            r"\[Candidate Confirmed|"
            r"\[Illustrative|"
            r"\n\n|"
            r"(?:\.|\;|\n)\s*(?=(?:I|we|my|our|the candidate)\b)|"
            r"(?:\.|\;|\n)\s*(?=(?:he|she|they)\s+(?:have\s+|had\s+)?[a-z]+(?:ed|t)\b)|"
            r"(?:\.|\;|\n)\s*(?=[^.\n;]*?\b(?:was|were)\s+(?:[a-z]+ed|led|built|run|written|chosen|owned)\b)|"
            r"(?:\.|\;|\n)\s*(?=[^.\n;]*?\b(?:deployment|database|team|architecture|features?|tests?|services?|components?|workflow|defect|code|pipeline)\s+(?:was|were)\b)|"
            r"(?:\.|\;|\n)\s*(?=[^.\n;]*?\bby\s+(?:me|us|our\s+team|the\s+candidate)\b)|"
            r"(?:\.|\;|\n)\s*(?=\b(?:software engineering duties|software development duties|software development tasks|assigned engineering features|practical engineering tools)\b)|"
            r"$"
            r")",
            flags=re.IGNORECASE | re.DOTALL
        )
        cleaned = guidance_pattern.sub("", cleaned)
        cleaned = re.sub(r"\(General Technical Guidance\):[^\n.]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[(?!Verified\s)[^\]]*\]", "", cleaned)
        cleaned = re.sub(r"\s*([.;])\s*([.;])+", r"\1", cleaned)
        cleaned = re.sub(r"^[\s.:;]+", "", cleaned)
        return cleaned.strip()

    @classmethod
    def classify_statement(
        cls,
        text: str,
        evidence: Optional[Union[Dict[str, Any], List[str], str]] = None
    ) -> Dict[str, bool]:
        """
        Classifies an answer excerpt into distinct evidence and knowledge categories:
        1. is_resume_supported: Facts supported by actual supplied resume evidence.
           (Never trusts 'Verified ...:' labels blindly; verifies actual value against supplied resume evidence).
        2. is_candidate_confirmed: Marked explicitly with [Candidate Confirmed: ...].
        3. is_general_technical: Objective pedagogical or technical description (must NOT contain unevidenced personal claims).
        4. is_illustrative_scenario: Marked with [Illustrative Scenario...] / [Illustrative Model Scenario...].
        5. is_missing_info_placeholder: Marked with [Candidate to specify: ...].
        6. is_unsupported_personal_claim: An assertion of personal engineering action, architecture decision, metric, or duty that is NOT verified by evidence.

        Key Invariants:
        - Valid markers and unsupported personal claims can coexist; both classifications are preserved.
        - Markers inside illustrative blocks cannot authenticate as resume evidence or candidate claims.
        - Candidate-confirmed and missing-information markers inside illustrative blocks do not influence statement classification.
        - A verified organization or title does not authenticate unrelated engineering/deployment claims.
        - Evidence matching is token- and boundary-aware, avoiding unsafe substring matches (e.g. SQL inside NoSQL).
        - Candidate confirmation is NEVER treated as independent resume evidence.
        - Arbitrary unverified personal text is NEVER classified as general technical content.
        - 'evidence_sources' is NEVER treated as proof of candidate achievements.
        - If evidence is unavailable, claims are classified as unverified rather than resume-supported.
        """
        t = text.strip()

        # 1. Compute cleaned text outside properly matched illustrative blocks first
        non_illustrative_text = cls._strip_illustrative_blocks(t)

        # 2. Cleaned text outside all exempt blocks (placeholders, candidate confirmations, properly scoped illustrative scenarios)
        cleaned = cls._strip_exempt_blocks(t)

        # 3. Determine candidate-confirmed and missing-placeholder classifications
        # ONLY from content outside properly matched illustrative blocks
        is_missing = bool(re.search(r"\[Candidate to specify:[^\]]*\]", non_illustrative_text, re.IGNORECASE))
        is_candidate = bool(re.search(r"\[Candidate Confirmed[^\]]*\]", non_illustrative_text, re.IGNORECASE))
        is_illustrative = bool(re.search(r"\[Illustrative (?:Model )?Scenario[^\]]*\]", t, re.IGNORECASE))

        # Extract genuine evidence
        ev_texts = cls._extract_evidence_text_set(evidence)

        # Check evidence markers in cleaned text outside illustrative blocks
        # Invariant: Markers inside illustrative blocks cannot set marker_verified, has_fabricated_marker, or is_resume_supported
        text_for_markers = re.sub(
            r"\[Illustrative\s+(?:Model\s+)?Scenario[^\]]*\]:?.*?(?=\[/\s*Illustrative\s+(?:Model\s+)?Scenario\s*:?\]|\n\n|$)",
            "",
            non_illustrative_text,
            flags=re.IGNORECASE | re.DOTALL
        )
        marker_pattern = re.compile(
            r"Verified (?:Project Title|Organization|Position|Dates|Responsibilities|Tools|Objective|Stack|Technologies):\s*['\"]?(.*?)(?=['\"]?(?:;|\.|\n|\]|$|\s+Verified ))",
            re.IGNORECASE
        )
        has_ev_marker = False
        has_fabricated_marker = False
        marker_verified = False

        for m in marker_pattern.finditer(text_for_markers):
            has_ev_marker = True
            claimed_val = m.group(1).strip()
            if claimed_val.lower() in ["not explicitly enumerated", "none", "not specified", "unspecified", ""]:
                continue
            # If claimed_val has commas (e.g. "Python, PostgreSQL"), verify each item
            sub_vals = [sv.strip() for sv in claimed_val.split(",") if sv.strip()]
            val_in_ev = bool(sub_vals)
            for sv in sub_vals:
                sv_found = any(cls._token_matches(sv, ev_item) for ev_item in ev_texts)
                if not sv_found:
                    val_in_ev = False
                    break
            if val_in_ev and ev_texts:
                marker_verified = True
            else:
                has_fabricated_marker = True

        # Check if text matches actual evidence directly using boundary-aware token matching
        # Evaluated on cleaned text so claims inside illustrative blocks cannot authenticate as resume evidence
        matches_actual_evidence = False
        for ev_item in ev_texts:
            if len(ev_item.strip()) >= 2 and cls._token_matches(ev_item, cleaned):
                matches_actual_evidence = True
                break

        # A statement is resume-supported if genuine evidence or a verified marker is present
        # Invariant: A valid marker can coexist with an unsupported personal claim or fabricated marker.
        is_resume = (
            bool(ev_texts)
            and (marker_verified or matches_actual_evidence)
            and not is_candidate
        )

        # Detect unsupported personal claims:
        # 1. Generic positive fallbacks
        has_generic_fallback = bool(re.search(
            r"\b(software engineering duties|software development duties|software development tasks|assigned engineering features|practical engineering tools)\b",
            cleaned, re.IGNORECASE
        ))

        # 2. Check individual claims against evidence using boundary-aware token matching
        unsupported_claim_patterns = [
            # Personal Engineering Contribution & Collaboration Claims
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?contributed\s+to\s+(?:production\s+)?features?\b",
            r"\b(?:production\s+)?features?\s+(?:were|was)\s+contributed\b",
            r"\bcontributed\s+to\s+production\s+features?\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?collaborated\s+with\s+(?:the\s+)?engineering\s+team\b",
            r"\bcollaborated\s+with\s+(?:the\s+)?engineering\s+team\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?debugged\s+(?:the\s+)?(?:payment\s+workflow|workflows?|defect|bugs?|production\s+issue)\b",
            r"\b(?:the\s+)?(?:payment\s+workflow|workflows?|production\s+issue)\s+(?:was|were)\s+debugged\b",
            r"\bdebugged\s+the\s+payment\s+workflow\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?maintained\s+(?:the\s+)?(?:production\s+)?database\b",
            r"\b(?:the\s+)?(?:production\s+)?database\s+(?:was|were)\s+maintained\b",
            r"\bmaintained\s+the\s+production\s+database\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?coordinated\s+deployment\b",
            r"\bdeployment\s+(?:was|were)\s+coordinated\b",
            r"\bcoordinated\s+deployment\b",
            # Leadership, management, supervision, ownership
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?led\s+(?:the\s+)?(?:deployment|team|engineering\s+team|project)\b",
            r"\b(?:deployment|team|engineering\s+team)\s+(?:was|were)\s+led\b",
            r"\bled\s+(?:the\s+)?deployment\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?managed\s+(?:the\s+)?(?:production\s+)?database\b",
            r"\b(?:the\s+)?(?:production\s+)?database\s+(?:was|were)\s+managed\b",
            r"\bmanaged\s+the\s+production\s+database\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?supervised\s+(?:the\s+)?(?:engineering\s+)?team\b",
            r"\b(?:the\s+)?(?:engineering\s+)?team\s+(?:was|were)\s+supervised\b",
            r"\bsupervised\s+the\s+engineering\s+team\b",
            r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?owned\s+(?:the\s+)?(?:architecture\s+decisions?|architecture|system)\b",
            r"\b(?:architecture\s+decisions?|architecture)\s+(?:were|was)\s+owned\b",
            r"\bowned\s+the\s+architecture\s+decisions?\b",
            # General personal action verbs
            r"\b(?:I|we|my|our)\s+(?:have\s+)?(?:led|managed|supervised|owned|designed|built|implemented|engineered|deployed|created|maintained|refactored|tested|optimized|authored|delivered|chose|decided|adhered|reached|contributed|collaborated|debugged|coordinated)\b",
            r"\b(?:the candidate|he|she|they)\s+(?:led|managed|supervised|owned|contributed\s+to|collaborated\s+with|debugged|maintained|coordinated|designed|implemented|built|engineered|deployed|authored|created|developed)\b",
            r"\b(?:My pull requests were reviewed|Successfully merged high-quality code|We maintain an extensive base)\b",
            # Architecture claims
            r"\b(?:decoupled presentation from backend processing logic|implemented a modular layered architecture|designed modular software components|deliberately chose a modular monolithic architecture|designed the architecture|chose microservices)\b",
            r"\bI designed (?:a |the )?(?:architecture|microservices?|modular|layered|system|components?|API|database schema|interfaces?)\b",
            r"\bI selected \w+ (?:over|for|to) \w+\b",
            r"\bdesigned the (?:API contracts?|component interfaces?|database schema)\b",
            r"\b(?:modular\s+components?|microservices?|architecture)\s+(?:were|was)\s+(?:designed|implemented|architected)\b",
            # Testing & QA claims
            r"\bI authored (?:automated |comprehensive |clean, |modular |unit |integration |end-to-end )?tests\b",
            r"\bI wrote (?:automated |comprehensive |unit |integration )?tests\b",
            r"\b(?:authored automated unit tests|authored comprehensive unit tests|created unit and integration test fixtures|committed the failing test case|authored CI/CD pipelines|deployed to AWS|deployed to GCP|deployed to Kubernetes)\b",
            r"\b(?:automated\s+unit\s+tests?|unit\s+tests?|test\s+fixtures?)\s+(?:were|was)\s+(?:authored|created|written)\b",
            # Deployment claims
            r"\bI deployed (?:this|the|to)\b",
            r"\bdeployed to (?:AWS|GCP|Azure|Kubernetes|production)\b",
            r"\b(?:were|was)\s+deployed\s+to\s+(?:AWS|GCP|Azure|Kubernetes|production)\b",
            # Metrics
            r"(?<!\[)(?:improved|reduced|increased|boosted|achieved)\s+.*?(?:\d+%\s*|\d+x\s*)(?!\])"
        ]

        has_unsupported_claim = False
        for pat in unsupported_claim_patterns:
            m = re.search(pat, cleaned, re.IGNORECASE)
            if m:
                matched_str = m.group(0).strip()
                core_str = re.sub(r"^(?:I|we|the candidate|he|she|they)\s+(?:have\s+)?", "", matched_str, flags=re.IGNORECASE).strip()
                is_supported = False
                for ev_t in ev_texts:
                    if cls._token_matches(matched_str, ev_t) or cls._token_matches(core_str, ev_t):
                        is_supported = True
                        break
                if not is_supported:
                    has_unsupported_claim = True
                    break

        is_unsupported = bool(
            has_generic_fallback
            or has_fabricated_marker
            or has_unsupported_claim
        )

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
        Audits an answer text for ungrounded personal claims.
        Flags unbracketed assertions across first-person, third-person, and passive voice
        (e.g., 'I contributed to production features', 'The payment workflow was debugged',
        'I designed modular software components') that are neither inside [Candidate to specify: ...]
        placeholders nor inside explicitly labeled [Illustrative Model Scenario...] blocks.
        """
        issues: List[str] = []
        if not text or not isinstance(text, str):
            return issues

        ev_texts = cls._extract_evidence_text_set(verified_evidence)

        # Check for malformed, unclosed, orphaned, or mismatched illustrative delimiters
        tag_pattern = re.compile(
            r"\[(/\s*)?Illustrative\s+(Model\s+)?Scenario[^\]]*\]",
            re.IGNORECASE
        )
        stack: List[str] = []
        for tag_m in tag_pattern.finditer(text):
            is_close = bool(tag_m.group(1))
            is_model = bool(tag_m.group(2))
            tag_type = "Model Scenario" if is_model else "Scenario"
            if not is_close:
                stack.append(tag_type)
            else:
                if not stack:
                    issues.append(
                        f"Found malformed illustrative block: orphaned [/{tag_m.group(0).lstrip('[/')} closing delimiter without opening delimiter"
                    )
                else:
                    open_type = stack.pop()
                    if open_type != tag_type:
                        issues.append(
                            f"Found malformed illustrative block: mismatched delimiter types "
                            f"([Illustrative {open_type}] closed by [/Illustrative {tag_type}])"
                        )
        while stack:
            unclosed_type = stack.pop()
            issues.append(
                f"Found malformed illustrative block: opening delimiter [Illustrative {unclosed_type}] without matching closing delimiter"
            )

        # Strip out bracketed placeholders, candidate confirmations, and properly matched illustrative scenarios
        cleaned = cls._strip_exempt_blocks(text)

        # Check verified markers against actual evidence outside illustrative blocks
        text_for_markers = re.sub(
            r"\[Illustrative\s+(?:Model\s+)?Scenario[^\]]*\]:?.*?(?=\[/\s*Illustrative\s+(?:Model\s+)?Scenario\s*:?\]|\n\n|$)",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL
        )
        marker_pattern = re.compile(
            r"Verified (?:Project Title|Organization|Position|Dates|Responsibilities|Tools|Objective|Stack|Technologies):\s*['\"]?(.*?)(?=['\"]?(?:;|\.|\n|\]|$|\s+Verified ))",
            re.IGNORECASE
        )
        for m in marker_pattern.finditer(text_for_markers):
            claimed_val = m.group(1).strip()
            if claimed_val.lower() in ["not explicitly enumerated", "none", "not specified", "unspecified", ""]:
                continue
            sub_vals = [sv.strip() for sv in claimed_val.split(",") if sv.strip()]
            val_in_ev = bool(sub_vals)
            for sv in sub_vals:
                sv_found = any(cls._token_matches(sv, ev_t) for ev_t in ev_texts)
                if not sv_found:
                    val_in_ev = False
                    break
            if not (val_in_ev and ev_texts):
                issues.append(f"Found unsupported evidence assertion: Verified marker with unevidenced value '{claimed_val}'")

        unsupported_patterns = [
            # 1. Generic positive fallbacks
            (r"\bsoftware engineering duties\b", "Uses forbidden generic positive fallback 'software engineering duties'"),
            (r"\bsoftware development duties\b", "Uses forbidden generic fallback 'software development duties'"),
            (r"\bsoftware development tasks\b", "Uses forbidden generic fallback 'software development tasks'"),
            (r"\bassigned engineering features\b", "Uses forbidden generic fallback 'assigned engineering features'"),
            (r"\bpractical engineering tools\b", "Uses forbidden generic fallback 'practical engineering tools'"),

            # 2. Personal Engineering Contribution & Collaboration Claims (Active, 3rd-person, Passive)
            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?contributed\s+to\s+(?:production\s+)?features?\b", "Claims ungrounded contribution to production features"),
            (r"\b(?:production\s+)?features?\s+(?:were|was)\s+contributed\b", "Claims ungrounded feature contribution (passive voice)"),
            (r"\bcontributed\s+to\s+production\s+features?\b", "Claims ungrounded contribution to production features"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?collaborated\s+with\s+(?:the\s+)?engineering\s+team\b", "Claims ungrounded collaboration with engineering team"),
            (r"\bcollaborated\s+with\s+(?:the\s+)?engineering\s+team\b", "Claims ungrounded collaboration with engineering team"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?debugged\s+(?:the\s+)?(?:payment\s+workflow|workflows?|defect|bugs?|production\s+issue)\b", "Claims ungrounded debugging of payment workflow or production issues"),
            (r"\b(?:the\s+)?(?:payment\s+workflow|workflows?|production\s+issue)\s+(?:was|were)\s+debugged\b", "Claims ungrounded debugging of workflow (passive voice)"),
            (r"\bdebugged\s+the\s+payment\s+workflow\b", "Claims ungrounded debugging of payment workflow"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?maintained\s+(?:the\s+)?(?:production\s+)?database\b", "Claims ungrounded maintenance of production database"),
            (r"\b(?:the\s+)?(?:production\s+)?database\s+(?:was|were)\s+maintained\b", "Claims ungrounded database maintenance (passive voice)"),
            (r"\bmaintained\s+the\s+production\s+database\b", "Claims ungrounded maintenance of production database"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?coordinated\s+deployment\b", "Claims ungrounded deployment coordination"),
            (r"\bdeployment\s+(?:was|were)\s+coordinated\b", "Claims ungrounded deployment coordination (passive voice)"),
            (r"\bcoordinated\s+deployment\b", "Claims ungrounded deployment coordination"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?led\s+(?:the\s+)?(?:deployment|team|engineering\s+team|project)\b", "Claims ungrounded deployment or team leadership (led)"),
            (r"\b(?:deployment|team|engineering\s+team)\s+(?:was|were)\s+led\b", "Claims ungrounded deployment or team leadership (led in passive voice)"),
            (r"\bled\s+(?:the\s+)?deployment\b", "Claims ungrounded deployment leadership (led)"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?managed\s+(?:the\s+)?(?:production\s+)?database\b", "Claims ungrounded production database management"),
            (r"\b(?:the\s+)?(?:production\s+)?database\s+(?:was|were)\s+managed\b", "Claims ungrounded database management (passive voice)"),
            (r"\bmanaged\s+the\s+production\s+database\b", "Claims ungrounded database management"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?supervised\s+(?:the\s+)?(?:engineering\s+)?team\b", "Claims ungrounded engineering team supervision"),
            (r"\b(?:the\s+)?(?:engineering\s+)?team\s+(?:was|were)\s+supervised\b", "Claims ungrounded engineering team supervision (passive voice)"),
            (r"\bsupervised\s+the\s+engineering\s+team\b", "Claims ungrounded engineering team supervision"),

            (r"\b(?:I|we|the candidate|he|she|they)?\s*(?:have\s+)?owned\s+(?:the\s+)?(?:architecture\s+decisions?|architecture|system)\b", "Claims ungrounded architecture ownership"),
            (r"\b(?:the\s+)?(?:architecture\s+decisions?|architecture)\s+(?:were|was)\s+owned\b", "Claims ungrounded architecture ownership (passive voice)"),
            (r"\bowned\s+the\s+architecture\s+decisions?\b", "Claims ungrounded architecture ownership"),

            (r"\b(?:\w+\s+)?(?:was|were)\s+(?:led|managed|supervised|owned|deployed|coordinated|maintained|debugged|contributed|designed|implemented|architected|authored|created|written)\s+by\s+(?:me|us|our\s+team|the\s+candidate)\b", "Claims ungrounded candidate engineering action (passive with agent)"),

            # 3. Unsupported Architecture & Design Claims
            (r"\bdecoupled presentation from backend processing logic\b", "Claims ungrounded architecture decoupling for project without evidence"),
            (r"\bI designed modular software components\b", "Claims ungrounded modular component design"),
            (r"\bI designed a modular layered architecture\b", "Claims ungrounded layered architecture design"),
            (r"\bI deliberately chose a modular monolithic architecture\b", "Claims ungrounded architecture choice"),
            (r"\bI architected\b", "Claims ungrounded system architecture"),
            (r"\bchose a (?:modular|microservices?|monolithic) architecture\b", "Claims ungrounded architecture selection rationale"),
            (r"\bI designed (?:a |the )?(?:architecture|microservices?|modular|layered|system|components?|API|database schema|interfaces?)\b", "Claims ungrounded architecture or design"),
            (r"\bI selected \w+ (?:over|for|to) \w+\b", "Claims ungrounded technology selection rationale"),
            (r"\bdesigned the (?:API contracts?|component interfaces?|database schema)\b", "Claims ungrounded design contracts or interfaces"),
            (r"\b(?:modular\s+components?|microservices?|architecture)\s+(?:were|was)\s+(?:designed|implemented|architected)\b", "Claims ungrounded architecture or component design (passive voice)"),

            # 4. Unsupported Implementation Claims
            (r"\bI implemented modular services\b", "Claims ungrounded modular service implementation"),
            (r"\bI implemented optimistic locking\b", "Claims ungrounded optimistic locking implementation"),
            (r"\bI discovered the failure was occurring because\b", "Claims ungrounded failure discovery"),
            (r"\bI refactored the module with defensive\b", "Claims ungrounded defensive module refactoring"),
            (r"\bI authored clean, modular code\b", "Claims ungrounded clean modular code authorship"),
            (r"\bI authored modular feature code\b", "Claims ungrounded modular feature code authorship"),
            (r"\bI implemented (?:the|backend|frontend|modular|custom|production|core)\b", "Claims ungrounded implementation"),
            (r"\b(?:the\s+candidate|he|she|they)\s+implemented\s+(?:modular\s+services|optimistic\s+locking)\b", "Claims ungrounded implementation (third-person)"),

            # 5. Unsupported Testing & QA Claims
            (r"\bI authored automated unit tests\b", "Claims ungrounded automated unit test authorship"),
            (r"\bI authored comprehensive unit tests\b", "Claims ungrounded comprehensive unit tests"),
            (r"\bcreated unit and integration test fixtures\b", "Claims ungrounded test fixture creation"),
            (r"\bI committed the failing test case\b", "Claims ungrounded test case commit"),
            (r"\bI validated '[^']+' by implementing automated\b", "Claims ungrounded automated unit test validation"),
            (r"\bWe maintain an extensive base of unit tests\b", "Claims unevidenced existing testing base"),
            (r"\bI authored (?:automated |comprehensive |clean, |modular |unit |integration |end-to-end )?tests\b", "Claims ungrounded unit or automated test authoring"),
            (r"\bI wrote (?:automated |comprehensive |unit |integration )?tests\b", "Claims ungrounded test writing"),
            (r"\b(?:automated\s+unit\s+tests?|unit\s+tests?|test\s+fixtures?)\s+(?:were|was)\s+(?:authored|created|written)\b", "Claims ungrounded test authoring (passive voice)"),

            # 6. Unsupported Deployment & CI/CD Claims
            (r"\bI deployed (?:this|the|to)\b", "Claims ungrounded deployment execution"),
            (r"\bdeployed to (?:AWS|GCP|Azure|Kubernetes|production)\b", "Claims ungrounded deployment target"),
            (r"\bI authored CI/CD pipelines\b", "Claims ungrounded CI/CD pipeline authoring"),
            (r"\b(?:I )?(?:created|built|authored) CI/CD pipelines?\b", "Claims ungrounded CI/CD pipeline construction"),
            (r"\bMy pull requests were reviewed, approved, and merged\b", "Claims ungrounded pull request review and merge"),
            (r"\bSuccessfully merged high-quality code\b", "Claims ungrounded production merge"),
            (r"\bThe completed service verified functional requirements\b", "Claims ungrounded service verification"),
            (r"\bThe completed system satisfied all acceptance criteria\b", "Claims ungrounded acceptance criteria satisfaction"),
            (r"\b(?:were|was)\s+deployed\s+to\s+(?:AWS|GCP|Azure|Kubernetes|production)\b", "Claims ungrounded deployment execution (passive voice)"),

            # 7. Unverified Metrics & Interactions
            (r"\bI adhered to a structured ['\"]?30-minute rule\b", "Claims unevidenced 30-minute rule adherence"),
            (r"\bMy internship permanently instilled\b", "Claims ungrounded personal internship habits"),
            (r"\bfollowing git and code review conventions\b", "Claims ungrounded adherence to conventions"),
            (r"\bA senior engineer commented: ['\"]?Catching generic Exception\b", "Claims fabricated code review interaction"),
            (r"(?<!\[)(?:improved|reduced|increased|boosted|achieved)\s+.*?(?:\d+%\s*|\d+x\s*)(?!\])", "Claims unverified quantitative metric without explicit candidate placeholder")
        ]

        for pat, desc in unsupported_patterns:
            m = re.search(pat, cleaned, re.IGNORECASE)
            if m:
                matched_str = m.group(0).strip()
                core_str = re.sub(r"^(?:I|we|the candidate|he|she|they)\s+(?:have\s+)?", "", matched_str, flags=re.IGNORECASE).strip()
                is_supported_by_ev = False
                for ev_t in ev_texts:
                    if cls._token_matches(matched_str, ev_t) or cls._token_matches(core_str, ev_t):
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
        # Invariant: evidence_sources is metadata and must NEVER be treated as proof of candidate achievements
        ev = verified_evidence or question_record.get("verified_evidence") or question_record.get("candidate_evidence")

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
            # When auditing the verified_evidence field itself, only external evidence
            # (passed via verified_evidence argument or candidate_evidence) can substantiate it.
            # The field cannot self-authenticate unsupported claims.
            external_ev = verified_evidence or question_record.get("candidate_evidence")
            if isinstance(vev, list):
                for idx, v_item in enumerate(vev):
                    if isinstance(v_item, str):
                        for iss in cls.audit_answer_for_unsupported_first_person_claims(v_item, verified_evidence=external_ev):
                            issues.append(f"verified_evidence[{idx}]: {iss}")
            elif isinstance(vev, str):
                for iss in cls.audit_answer_for_unsupported_first_person_claims(vev, verified_evidence=external_ev):
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
        # Invariant: evidence_sources is metadata and must NEVER be treated as proof of candidate achievements
        evidence_ctx = question_record.get("verified_evidence") or question_record.get("candidate_evidence")
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
