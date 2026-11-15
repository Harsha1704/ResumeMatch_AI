"""Secure Rating Intake and Validation Engine for ResumeMatch AI Benchmark.

Validates human recruiter annotation submissions against strict schema,
manifest membership, verbatim quote matching, and duplicate prevention rules.
Maintains an immutable append-only ledger of verified submissions and enforces
blinding and quarantine protocols.
"""

import os
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional, Set

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DEFAULT_MANIFEST_PATH = os.path.join(
    WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_pilot_sampling_manifest.json"
)
DEFAULT_INTAKE_LEDGER_PATH = os.path.join(
    WORKSPACE_ROOT, "data", "benchmark_vault", "intake", "raw_submissions.jsonl"
)
DEFAULT_QUARANTINE_DIR = os.path.join(
    WORKSPACE_ROOT, "data", "benchmark_vault", "pilot_quarantine"
)

AUTHORIZED_EVALUATORS = {"REC_A_892", "REC_B_314", "LEAD_ADJ_001"}
VALID_RATINGS = {0, 1, 2}  # 0: No Fit, 1: Potential Fit, 2: Good Fit
VALID_CONFIDENCES = {1, 2, 3}  # 1: Low, 2: Medium, 3: High
VALID_RESUME_EVIDENCE_STATUSES = {
    "CONFIRMED_PRESENT",
    "CONFIRMED_CONTRADICTED",
    "UNSTATED_UNVERIFIED",
}
MIN_RATIONALE_LENGTH = 25


class RatingIntakeValidator:
    """Validates, records, and audits recruiter pilot rating submissions."""

    def __init__(
        self,
        manifest_path: str = DEFAULT_MANIFEST_PATH,
        ledger_path: str = DEFAULT_INTAKE_LEDGER_PATH,
        authorized_evaluators: Optional[Set[str]] = None,
    ):
        self.manifest_path = os.path.abspath(manifest_path)
        self.ledger_path = os.path.abspath(ledger_path)
        self.authorized_evaluators = authorized_evaluators or AUTHORIZED_EVALUATORS

        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load frozen manifest and index pair details."""
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Sampling manifest not found at: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        self.manifest_metadata = {
            "phase": manifest_data.get("phase"),
            "pilot_name": manifest_data.get("pilot_name"),
            "total_pairs": manifest_data.get("total_pairs", 0),
        }
        self.pairs_by_id: Dict[str, Dict[str, Any]] = {}
        for p in manifest_data.get("pairs", []):
            self.pairs_by_id[p["pair_id"]] = p

        self.all_pair_ids = sorted(list(self.pairs_by_id.keys()))

    def get_existing_submissions(self) -> List[Dict[str, Any]]:
        """Read all existing immutable submissions from the ledger."""
        if not os.path.exists(self.ledger_path):
            return []

        submissions = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        submissions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return submissions

    def validate_submission_payload(
        self, submission: Dict[str, Any], existing_keys: Optional[Set[Tuple[str, str]]] = None
    ) -> Tuple[bool, List[str]]:
        """Validate a single submission payload against all intake rules.

        Returns (is_valid, list_of_errors).
        """
        errors = []

        # 1. Evaluator ID
        evaluator_id = submission.get("evaluator_id")
        if not evaluator_id:
            errors.append("Missing 'evaluator_id'.")
        elif evaluator_id not in self.authorized_evaluators:
            errors.append(
                f"Unauthorized evaluator '{evaluator_id}'. Must be one of {sorted(list(self.authorized_evaluators))}."
            )

        # 2. Pair ID format and manifest membership
        pair_id = submission.get("pair_id")
        if not pair_id:
            errors.append("Missing 'pair_id'.")
        elif not re.match(r"^PILOT_P_\d{4}$", str(pair_id)):
            errors.append(f"Invalid pair_id format '{pair_id}'. Must match 'PILOT_P_XXXX'.")
        elif pair_id not in self.pairs_by_id:
            errors.append(f"Pair ID '{pair_id}' is not in frozen pilot sampling manifest.")

        # 3. Duplicate check
        if evaluator_id and pair_id:
            if existing_keys is not None:
                if (evaluator_id, pair_id) in existing_keys:
                    errors.append(
                        f"Duplicate submission rejected: Evaluator '{evaluator_id}' has already submitted a rating for pair '{pair_id}'."
                    )
            else:
                existing = self.get_existing_submissions()
                for sub in existing:
                    if sub.get("evaluator_id") == evaluator_id and sub.get("pair_id") == pair_id:
                        errors.append(
                            f"Duplicate submission rejected: Evaluator '{evaluator_id}' has already submitted a rating for pair '{pair_id}'."
                        )
                        break

        # 4. Rating value in {0, 1, 2}
        rating = submission.get("rating")
        if rating is None:
            errors.append("Missing 'rating'.")
        elif rating not in VALID_RATINGS or isinstance(rating, bool):
            errors.append(f"Invalid rating '{rating}'. Must be an integer in {{0: No Fit, 1: Potential Fit, 2: Good Fit}}.")

        # 5. Confidence value in {1, 2, 3}
        confidence = submission.get("confidence")
        if confidence is None:
            errors.append("Missing 'confidence'.")
        elif confidence not in VALID_CONFIDENCES or isinstance(confidence, bool):
            errors.append(f"Invalid confidence '{confidence}'. Must be an integer in {{1: Low, 2: Medium, 3: High}}.")

        # 6. Resume evidence status
        res_ev = submission.get("resume_evidence_status")
        if not res_ev:
            errors.append("Missing 'resume_evidence_status'.")
        elif res_ev not in VALID_RESUME_EVIDENCE_STATUSES:
            errors.append(
                f"Invalid resume_evidence_status '{res_ev}'. Must be one of {sorted(list(VALID_RESUME_EVIDENCE_STATUSES))}."
            )

        # 7. Job evidence quote validation (verbatim verification)
        job_quote = submission.get("job_evidence_quote")
        if not job_quote or not str(job_quote).strip():
            errors.append("Missing 'job_evidence_quote'. Verbatim quotation from job description is mandatory.")
        else:
            job_quote_str = str(job_quote).strip()
            if pair_id in self.pairs_by_id:
                job_desc = self.pairs_by_id[pair_id].get("job_description_snippet", "")
                # Normalize whitespace for robust verbatim check
                norm_quote = re.sub(r"\s+", " ", job_quote_str.lower())
                norm_desc = re.sub(r"\s+", " ", job_desc.lower())
                if len(norm_quote) < 8:
                    errors.append("Job evidence quote too brief (minimum 8 characters).")
                elif norm_quote not in norm_desc:
                    errors.append(
                        f"Job evidence quote '{job_quote_str[:40]}...' was not found in job description snippet for {pair_id}."
                    )

        # 8. Decision rationale
        rationale = submission.get("decision_rationale")
        if not rationale or not str(rationale).strip():
            errors.append("Missing 'decision_rationale'.")
        elif len(str(rationale).strip()) < MIN_RATIONALE_LENGTH:
            errors.append(
                f"Decision rationale is too brief ({len(str(rationale).strip())} chars). Minimum {MIN_RATIONALE_LENGTH} characters required."
            )

        # 9. Mandatory skill justification
        mandatory = submission.get("mandatory_justification")
        if not mandatory or not str(mandatory).strip():
            errors.append("Missing 'mandatory_justification'.")
        elif len(str(mandatory).strip()) < 10:
            errors.append("Mandatory justification must be at least 10 characters.")

        # 10. Blinding violation check
        # Reject submissions that attempt to pass model predictions or peer ratings
        forbidden_fields = {"model_prediction", "peer_rating", "annotator_agreement", "challenger_pred"}
        leaked = set(submission.keys()).intersection(forbidden_fields)
        if leaked:
            errors.append(f"Blinding violation detected! Submission contains forbidden fields: {list(leaked)}.")

        return (len(errors) == 0, errors)

    def ingest_submission(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and append a single submission to the immutable ledger."""
        is_valid, errors = self.validate_submission_payload(submission)
        if not is_valid:
            return {
                "status": "REJECTED",
                "pair_id": submission.get("pair_id"),
                "evaluator_id": submission.get("evaluator_id"),
                "errors": errors,
            }

        # Format record for immutable ledger
        record = {
            "evaluator_id": submission["evaluator_id"],
            "pair_id": submission["pair_id"],
            "rating": int(submission["rating"]),
            "confidence": int(submission["confidence"]),
            "job_evidence_quote": str(submission["job_evidence_quote"]).strip(),
            "decision_rationale": str(submission["decision_rationale"]).strip(),
            "mandatory_justification": str(submission["mandatory_justification"]).strip(),
            "resume_evidence_status": submission["resume_evidence_status"],
            "submitted_at": submission.get("submitted_at") or datetime.now(timezone.utc).isoformat(),
        }

        # Calculate payload checksum
        payload_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
        record["intake_hash"] = hashlib.sha256(payload_bytes).hexdigest()
        record["intake_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Append to ledger
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return {
            "status": "ACCEPTED",
            "pair_id": record["pair_id"],
            "evaluator_id": record["evaluator_id"],
            "intake_hash": record["intake_hash"],
        }

    def ingest_batch(self, submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest a batch of submissions."""
        existing = self.get_existing_submissions()
        existing_keys = {(s["evaluator_id"], s["pair_id"]) for s in existing}

        accepted = []
        rejected = []

        for sub in submissions:
            is_valid, errors = self.validate_submission_payload(sub, existing_keys=existing_keys)
            if is_valid:
                res = self.ingest_submission(sub)
                if res["status"] == "ACCEPTED":
                    accepted.append(res)
                    existing_keys.add((sub["evaluator_id"], sub["pair_id"]))
                else:
                    rejected.append(res)
            else:
                rejected.append({
                    "status": "REJECTED",
                    "pair_id": sub.get("pair_id"),
                    "evaluator_id": sub.get("evaluator_id"),
                    "errors": errors,
                })

        return {
            "total_submitted": len(submissions),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "accepted": accepted,
            "rejected": rejected,
        }

    def get_evaluator_progress(self, evaluator_id: str) -> Dict[str, Any]:
        """Return completion progress for an evaluator."""
        existing = self.get_existing_submissions()
        eval_subs = [s for s in existing if s.get("evaluator_id") == evaluator_id]
        submitted_pairs = {s["pair_id"] for s in eval_subs}

        missing_pairs = [pid for pid in self.all_pair_ids if pid not in submitted_pairs]

        return {
            "evaluator_id": evaluator_id,
            "total_pairs_assigned": len(self.all_pair_ids),
            "submitted_count": len(submitted_pairs),
            "remaining_count": len(missing_pairs),
            "completion_percentage": round((len(submitted_pairs) / len(self.all_pair_ids)) * 100, 2)
            if self.all_pair_ids
            else 0.0,
            "is_complete": len(submitted_pairs) == len(self.all_pair_ids) and len(self.all_pair_ids) > 0,
            "missing_pairs": missing_pairs,
        }

    def get_pilot_intake_summary(self) -> Dict[str, Any]:
        """Return overall pilot progress and gate status."""
        rec_a_prog = self.get_evaluator_progress("REC_A_892")
        rec_b_prog = self.get_evaluator_progress("REC_B_314")

        total_ratings_received = rec_a_prog["submitted_count"] + rec_b_prog["submitted_count"]
        target_ratings = len(self.all_pair_ids) * 2

        both_complete = rec_a_prog["is_complete"] and rec_b_prog["is_complete"]

        gate_status = "PILOT COMPLETE" if both_complete else "PILOT READY — AWAITING REAL RECRUITER ANNOTATIONS"

        return {
            "pilot_name": self.manifest_metadata["pilot_name"],
            "total_pairs": len(self.all_pair_ids),
            "target_ratings_total": target_ratings,
            "total_ratings_received": total_ratings_received,
            "completion_percentage": round((total_ratings_received / target_ratings) * 100, 2)
            if target_ratings > 0
            else 0.0,
            "evaluators": {
                "REC_A_892": rec_a_prog,
                "REC_B_314": rec_b_prog,
            },
            "gate_status": gate_status,
            "ready_for_adjudication": both_complete,
        }

    def compute_pre_adjudication_reliability(self) -> Dict[str, Any]:
        """Compute pre-adjudication inter-annotator reliability metrics.

        Returns pending/null statistics if either evaluator has not completed all 200 pairs.
        """
        rec_a_prog = self.get_evaluator_progress("REC_A_892")
        rec_b_prog = self.get_evaluator_progress("REC_B_314")

        if not (rec_a_prog["is_complete"] and rec_b_prog["is_complete"]):
            return {
                "status": "PENDING_RECRUITER_RATINGS",
                "message": (
                    f"Reliability metrics cannot be computed until both evaluators submit all 200 pairs. "
                    f"Current: REC_A_892={rec_a_prog['submitted_count']}/200, "
                    f"REC_B_314={rec_b_prog['submitted_count']}/200."
                ),
                "pairs_completed_by_both": 0,
                "raw_agreement": None,
                "cohen_kappa_unweighted": None,
                "quadratic_weighted_kappa": None,
                "gwet_ac1": None,
                "specific_agreement": {
                    "0_no_fit": None,
                    "1_potential_fit": None,
                    "2_good_fit": None,
                },
                "adjudication_required_rate": None,
                "severe_discordance_count": None,
                "severe_discordance_rate": None,
                "confusion_matrix": None,
            }

        # If both are complete, compute exact metrics
        existing = self.get_existing_submissions()
        ratings_a = {s["pair_id"]: s["rating"] for s in existing if s["evaluator_id"] == "REC_A_892"}
        ratings_b = {s["pair_id"]: s["rating"] for s in existing if s["evaluator_id"] == "REC_B_314"}

        pairs = self.all_pair_ids
        y_a = [ratings_a[pid] for pid in pairs]
        y_b = [ratings_b[pid] for pid in pairs]
        N = len(pairs)

        # 3x3 confusion matrix
        matrix = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        agree_count = 0
        severe_count = 0
        adjudication_count = 0

        for a, b in zip(y_a, y_b):
            matrix[a][b] += 1
            if a == b:
                agree_count += 1
            else:
                adjudication_count += 1
                if abs(a - b) == 2:
                    severe_count += 1

        po = agree_count / N

        # Marginal proportions
        p_a = [sum(matrix[i][j] for j in range(3)) / N for i in range(3)]
        p_b = [sum(matrix[i][j] for i in range(3)) / N for j in range(3)]
        pe = sum(p_a[k] * p_b[k] for k in range(3))

        # Unweighted Kappa
        kappa = (po - pe) / (1.0 - pe) if pe < 1.0 else 1.0

        # Quadratic weighted kappa
        # w_ij = 1 - (i - j)^2 / (3 - 1)^2 = 1 - (i - j)^2 / 4
        weights = [[1.0 - ((i - j) ** 2) / 4.0 for j in range(3)] for i in range(3)]
        po_w = sum(matrix[i][j] * weights[i][j] for i in range(3) for j in range(3)) / N
        pe_w = sum(p_a[i] * p_b[j] * weights[i][j] for i in range(3) for j in range(3))
        kappa_w = (po_w - pe_w) / (1.0 - pe_w) if pe_w < 1.0 else 1.0

        # Gwet's AC1
        p_mean = [(p_a[k] + p_b[k]) / 2.0 for k in range(3)]
        pe_gwet = (1.0 / (3.0 - 1.0)) * sum(p * (1.0 - p) for p in p_mean)
        ac1 = (po - pe_gwet) / (1.0 - pe_gwet) if pe_gwet < 1.0 else 1.0

        # Specific agreement per category
        specific_agreement = {}
        for k, cat_name in [(0, "0_no_fit"), (1, "1_potential_fit"), (2, "2_good_fit")]:
            denom = p_a[k] * N + p_b[k] * N
            specific_agreement[cat_name] = (2 * matrix[k][k]) / denom if denom > 0 else 0.0

        return {
            "status": "COMPUTED",
            "pairs_completed_by_both": N,
            "raw_agreement": round(po, 4),
            "cohen_kappa_unweighted": round(kappa, 4),
            "quadratic_weighted_kappa": round(kappa_w, 4),
            "gwet_ac1": round(ac1, 4),
            "specific_agreement": {k: round(v, 4) for k, v in specific_agreement.items()},
            "adjudication_required_rate": round(adjudication_count / N, 4),
            "adjudication_required_count": adjudication_count,
            "severe_discordance_count": severe_count,
            "severe_discordance_rate": round(severe_count / N, 4),
            "confusion_matrix": matrix,
        }
