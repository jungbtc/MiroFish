"""Deterministic decision-intelligence loop over a completed MiroFish report.

This module deliberately makes no network or model calls. MiroFish reuses the
completed simulation evidence and only asks for
organization-private facts that can change the recommendation.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from .schemas import (
    AuditEvent,
    Contradiction,
    DecisionAssumption,
    DecisionHypothesis,
    DecisionImpact,
    ExtractedClaim,
    HypothesisChange,
    QuestionPriorityBreakdown,
    InternalEvidence,
    InternalQuestion,
    StopEvaluation,
    V2RunState,
)


QUESTION_PRIORITY_FORMULA = "100 × (0.40 sensitivity + 0.30 uncertainty + 0.20 answerability + 0.10 urgency)"
MATERIALITY_THRESHOLD = 45.0
MAX_INTERNAL_QUESTIONS = 4
ACTIONABLE_CONFIDENCE = 0.60
EVIDENCE_RULE_VERSION = "deterministic_category_rules_v2"

ACTION_VERBS = {
    "approve", "proceed", "launch", "expand", "accelerate", "pilot", "stage",
    "redesign", "revise", "modify", "cancel", "postpone", "defer", "pause",
    "choose", "select", "adopt", "implement", "commit", "invest", "fund",
    "reduce", "increase", "acquire", "divest", "partner", "retain", "exit",
    "restructure", "roll", "run", "hold", "reject", "continue",
}
ACTION_NOUNS = {
    "rollout", "pilot", "launch", "expansion", "redesign", "revision",
    "cancellation", "postponement", "deferral", "investment", "commitment",
    "acquisition", "divestiture", "partnership", "deployment", "restructuring",
    "initiative", "program", "trial",
}
STAKEHOLDER_ONLY_TERMS = {
    "customer", "customers", "member", "members", "nonmember", "nonmembers",
    "employee", "employees", "barista", "baristas", "manager", "managers",
    "investor", "investors", "union", "unions", "media", "regulator",
    "regulators", "competitor", "competitors", "advocate", "advocates",
    "supplier", "suppliers", "consumer", "consumers", "stakeholder", "stakeholders",
}
OBSERVATION_PREFIX_RE = re.compile(
    r"^(?:the\s+)?(?:market|demand|revenue|sales|customers?|stakeholders?|momentum|"
    r"results?|outlook|cycle|peak)\b|^(?:have|has|had|driven|reported|remains?|"
    r"shows?|indicates?|suggests?|simulate|forecast)\b",
    re.IGNORECASE,
)


def is_executable_action_label(value: str) -> bool:
    """Return true only for a management-selectable action label."""
    label = re.sub(r"[*_`#>]", "", str(value or "")).strip(" \t\n?.")
    if len(label) < 4 or len(label) > 160 or OBSERVATION_PREFIX_RE.search(label):
        return False
    tokens = re.findall(r"[a-z0-9]+", label.lower())
    if not tokens:
        return False
    residual = set(tokens) - ACTION_VERBS - {
        "a", "an", "the", "to", "with", "for", "of", "and", "or",
        "store", "frontline", "current", "prospective", "non", "recommend",
    }
    if residual and residual <= STAKEHOLDER_ONLY_TERMS:
        return False
    return bool(set(tokens) & ACTION_VERBS or set(tokens) & ACTION_NOUNS)


def build_decision_completion(state: V2RunState) -> Dict[str, Any]:
    """Describe workflow completion without conflating evidence stop with approval."""
    research_complete = bool(state.documents or state.initial_report_markdown)
    internal_evidence_complete = bool(
        state.stop_evaluation and state.stop_evaluation.should_stop
    )
    actions_valid = bool(state.hypotheses) and all(
        is_executable_action_label(item.label) for item in state.hypotheses
    )
    confirmed_ids = set((state.action_confirmation or {}).get("action_ids") or [])
    current_ids = {item.hypothesis_id for item in state.hypotheses}
    actions_confirmed = bool(
        actions_valid
        and (state.action_confirmation or {}).get("status") == "confirmed"
        and confirmed_ids == current_ids
    )
    decision_model_calculated = bool(
        state.decision_model
        and (state.decision_analysis_result or {}).get("status") == "calculated"
    )
    waiver = state.decision_analysis_waiver or {}
    decision_model_waived = bool(
        waiver.get("status") == "confirmed"
        and set(waiver.get("action_ids") or []) == current_ids
        and waiver.get("action_hash") == (state.action_confirmation or {}).get("action_hash")
    )
    decision_model_complete = decision_model_calculated or decision_model_waived
    model_actions = (state.decision_model or {}).get("actions") or []
    model_action_ids = {str(item.get("id") or "") for item in model_actions}
    model_action_labels = {
        re.sub(r"\s+", " ", str(item.get("label") or "").strip().lower())
        for item in model_actions
    }
    all_hypothesis_ids = {item.hypothesis_id for item in state.hypotheses}
    active_hypothesis_ids = {
        item.hypothesis_id for item in state.hypotheses if item.status != "pruned"
    }
    all_hypothesis_labels = {
        re.sub(r"\s+", " ", item.label.strip().lower()) for item in state.hypotheses
    }
    active_hypothesis_labels = {
        re.sub(r"\s+", " ", item.label.strip().lower())
        for item in state.hypotheses
        if item.status != "pruned"
    }
    decision_model_actions_aligned = bool(
        decision_model_waived
        or (
            model_actions
            and (
                frozenset(model_action_ids)
                in {frozenset(all_hypothesis_ids), frozenset(active_hypothesis_ids)}
                or frozenset(model_action_labels)
                in {frozenset(all_hypothesis_labels), frozenset(active_hypothesis_labels)}
            )
        )
    )
    unresolved_critical = [
        item.contradiction_id
        for item in state.contradictions
        if str(item.status).lower() not in {"resolved", "closed", "dismissed"}
        and str(item.severity).lower() in {"high", "critical"}
    ]
    execution_plan_complete = bool(
        state.execution_plan
        and state.execution_plan.ready
        and state.execution_plan.coverage.get("complete")
    )
    final_approval_ready = bool(
        research_complete
        and internal_evidence_complete
        and actions_confirmed
        and decision_model_complete
        and decision_model_actions_aligned
        and execution_plan_complete
        and not unresolved_critical
    )

    blocked_reasons: List[str] = []
    if internal_evidence_complete and not actions_valid:
        blocked_reasons.append("Action alternatives are not executable management choices.")
    if internal_evidence_complete and actions_valid and not actions_confirmed:
        blocked_reasons.append("Management has not confirmed the available actions.")
    if actions_confirmed and not decision_model_complete:
        blocked_reasons.append(
            "Choose a confirmed quantitative model or explicitly approve a qualitative decision."
        )
    if decision_model_complete and not decision_model_actions_aligned:
        blocked_reasons.append(
            "The calculated model action set does not match the confirmed management actions."
        )
    if decision_model_complete and not execution_plan_complete:
        failures = (
            state.execution_plan.executability.get("hard_failures", [])
            if state.execution_plan else []
        )
        blocked_reasons.append(
            failures[0]
            if failures
            else "The selected decision has not been compiled into a complete executable plan."
        )
    if unresolved_critical:
        blocked_reasons.append(
            f"{len(unresolved_critical)} high-severity evidence conflict(s) remain unresolved."
        )

    if final_approval_ready:
        stage = "final_approval_ready"
    elif decision_model_complete and not execution_plan_complete:
        stage = "execution_plan_completion"
    elif decision_model_complete:
        stage = "final_review"
    elif internal_evidence_complete and not actions_confirmed:
        stage = "action_confirmation"
    elif actions_confirmed and not decision_model_complete:
        stage = "decision_model_completion"
    else:
        stage = "internal_evidence_refinement"

    return {
        "research_complete": research_complete,
        "internal_evidence_complete": internal_evidence_complete,
        "actions_valid": actions_valid,
        "actions_confirmed": actions_confirmed,
        "decision_model_calculated": decision_model_calculated,
        "decision_model_waived": decision_model_waived,
        "decision_model_complete": decision_model_complete,
        "decision_model_actions_aligned": decision_model_actions_aligned,
        "execution_plan_complete": execution_plan_complete,
        "critical_conflicts_resolved": not unresolved_critical,
        "unresolved_critical_contradiction_ids": unresolved_critical,
        "final_approval_ready": final_approval_ready,
        "stage": stage,
        "blocked_reasons": blocked_reasons,
    }


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _question_priority_score(components: QuestionPriorityBreakdown) -> float:
    value = 100 * (
        0.40 * components.decision_sensitivity
        + 0.30 * components.uncertainty
        + 0.20 * components.answerability
        + 0.10 * components.urgency
    )
    return round(value, 1)


class DecisionIntelligenceService:
    """Create and update a transparent decision case without duplicating research."""

    POSITIVE_TERMS = {
        "yes", "approved", "sufficient", "available", "committed", "funded",
        "ready", "strong", "high", "acceptable", "within", "exceed", "met",
        "green", "proceed", "support", "capacity", "confirmed",
    }
    NEGATIVE_TERMS = {
        "no", "not", "insufficient", "unavailable", "blocked", "unapproved",
        "weak", "low", "cannot", "can't", "over", "delayed", "unacceptable",
        "missing", "red", "reject", "oppose", "none", "shortfall",
    }
    CAUTIOUS_TERMS = {
        "partial", "pilot", "staged", "uncertain", "unknown", "conditional",
        "limited", "mixed", "maybe", "contingent", "validate", "test",
    }
    INTERNAL_QUESTION_CATEGORIES = {
        "strategic_success", "constraints", "financial_capacity",
        "execution_capacity", "risk_tolerance", "timing",
    }

    def initialize(self, state: V2RunState) -> V2RunState:
        state.assumptions = self._build_assumptions(state.question)
        state.contradictions = self._detect_contradictions(state.claims)
        state.hypotheses = self._build_hypotheses(state.question, state.claims, state.assumptions)
        state.internal_questions = self._build_internal_questions(state)
        self._activate_next_question(state.internal_questions)
        state.stop_evaluation = self.evaluate_stop(state)
        state.decision_completion = build_decision_completion(state)
        state.graph = self.build_decision_graph(state)

        external_links = sum(
            1
            for document in state.documents
            for citation in document.imported_citations
            if citation.url
        )
        report_only_claims = sum(1 for claim in state.claims if claim.provenance_status == "report_only")
        self._audit(
            state,
            "import_completed",
            "Completed FOREFOLD report analyzed.",
            {
                "documents": len(state.documents),
                "external_source_links_preserved": external_links,
                "processing_mode": state.token_usage.processing_mode,
                "external_llm_calls": state.token_usage.external_llm_calls,
            },
        )
        self._audit(
            state,
            "evidence_classified",
            "Imported statements were separated from FOREFOLD-generated interpretations.",
            {
                "sourced_claims": len(state.claims),
                "report_only_claims": report_only_claims,
                "generated_assumptions": len(state.assumptions),
            },
        )
        self._audit(
            state,
            "contradictions_detected",
            f"Detected {len(state.contradictions)} potentially conflicting claim pair(s).",
            {"contradiction_ids": [item.contradiction_id for item in state.contradictions]},
        )
        self._audit(
            state,
            "hypotheses_created",
            "Created competing decision paths and marked their evidence coverage.",
            {"hypothesis_ids": [item.hypothesis_id for item in state.hypotheses]},
        )
        top_question = next((item for item in state.internal_questions if item.status == "requested"), None)
        self._audit(
            state,
            "questions_ranked",
            "Ranked organization-only questions by explainable Question Priority Score.",
            {
                "formula": QUESTION_PRIORITY_FORMULA,
                "top_question_id": top_question.question_id if top_question else None,
                "top_score": top_question.question_priority_score if top_question else 0,
                "privacy_boundary": "Internal answers remain local and are not sent upstream.",
            },
        )
        self._audit_stop(state)
        return state

    def confirm_actions(
        self,
        state: V2RunState,
        action_ids: Sequence[str],
        *,
        confirmed_by: str = "decision_owner",
    ) -> V2RunState:
        """Confirm the considered management actions without pretending the numeric model is complete."""
        if not (state.stop_evaluation and state.stop_evaluation.should_stop):
            raise ValueError("Complete the bounded internal-fact collection before confirming actions.")
        if not state.hypotheses or not all(
            is_executable_action_label(item.label) for item in state.hypotheses
        ):
            raise ValueError("Every path must be written as an executable management action before confirmation.")
        expected_ids = {item.hypothesis_id for item in state.hypotheses}
        supplied_ids = {str(item).strip() for item in action_ids if str(item).strip()}
        if supplied_ids != expected_ids:
            raise ValueError("Confirm the complete current action set; partial confirmation is not allowed.")

        canonical_actions = [
            {
                "id": item.hypothesis_id,
                "label": item.label,
                "role": item.decision_role,
            }
            for item in sorted(state.hypotheses, key=lambda item: item.hypothesis_id)
        ]
        action_hash = hashlib.sha256(
            repr(canonical_actions).encode("utf-8")
        ).hexdigest()
        state.action_confirmation = {
            "status": "confirmed",
            "action_ids": sorted(expected_ids),
            "actions": canonical_actions,
            "action_hash": action_hash,
            "confirmed_by": (confirmed_by or "decision_owner").strip(),
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        self._audit(
            state,
            "management_actions_confirmed",
            "Management confirmed that every scored path is a real action considered in the decision; pruned paths remain explicitly unavailable.",
            {
                "action_ids": sorted(expected_ids),
                "action_hash": action_hash,
                "confirmed_by": state.action_confirmation["confirmed_by"],
            },
        )
        return state

    def waive_quantitative_analysis(
        self,
        state: V2RunState,
        *,
        confirmed_by: str = "decision_owner",
        reason: str = "The decision owner approved an evidence-backed qualitative decision without a quantitative utility model.",
    ) -> V2RunState:
        """Finalize the qualitative path through an explicit, auditable owner choice."""
        completion = build_decision_completion(state)
        if not completion["internal_evidence_complete"]:
            raise ValueError("Complete the bounded internal-fact collection first.")
        if not completion["actions_confirmed"]:
            raise ValueError("Confirm the management action set before choosing a decision method.")
        if completion["decision_model_calculated"]:
            raise ValueError("A confirmed quantitative decision model has already been calculated.")

        action_confirmation = state.action_confirmation or {}
        state.decision_analysis_waiver = {
            "status": "confirmed",
            "method": "evidence_backed_qualitative_decision",
            "action_ids": list(action_confirmation.get("action_ids") or []),
            "action_hash": action_confirmation.get("action_hash"),
            "confirmed_by": (confirmed_by or "decision_owner").strip(),
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason.strip(),
            "numeric_claims_made": False,
        }
        state.decision_model_proposal = None
        state.decision_model = None
        state.decision_analysis_result = None
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        self._audit(
            state,
            "quantitative_decision_analysis_waived",
            "Decision owner explicitly approved the evidence-backed qualitative method without numeric utility claims.",
            {
                "action_ids": state.decision_analysis_waiver["action_ids"],
                "action_hash": state.decision_analysis_waiver["action_hash"],
                "confirmed_by": state.decision_analysis_waiver["confirmed_by"],
                "numeric_claims_made": False,
            },
        )
        return state

    def ensure_valid_actions(self, state: V2RunState) -> bool:
        """Repair legacy stakeholder/prompt-fragment paths and replay their internal evidence."""
        if state.hypotheses and all(
            is_executable_action_label(item.label) for item in state.hypotheses
        ):
            state.decision_completion = build_decision_completion(state)
            return False

        prior_labels = [item.label for item in state.hypotheses]
        state.hypotheses = self._build_hypotheses(
            state.question,
            state.claims,
            state.assumptions,
        )
        affected_ids = [item.hypothesis_id for item in state.hypotheses]
        for question in state.internal_questions:
            question.affected_hypothesis_ids = affected_ids

        state.decision_impacts = []
        for evidence in state.internal_evidence:
            if not evidence.decision_usable or evidence.retracted:
                continue
            question = next(
                (item for item in state.internal_questions if item.question_id == evidence.question_id),
                None,
            )
            if question is None:
                continue
            changes = self._apply_hypothesis_changes(state, question, evidence)
            strengthened = sum(change.delta > 0.001 for change in changes)
            weakened = sum(change.delta < -0.001 for change in changes)
            pruned = sum(change.after_status == "pruned" for change in changes)
            state.decision_impacts.append(
                DecisionImpact(
                    impact_id=_stable_id("impact", evidence.evidence_id),
                    question_id=question.question_id,
                    evidence_id=evidence.evidence_id,
                    summary=(
                        f"Internal evidence {evidence.evidence_id} strengthened {strengthened} action(s), "
                        f"weakened {weakened} action(s), and pruned {pruned} action(s)."
                    ),
                    hypothesis_changes=changes,
                    graph_change_summary=self._graph_change_summary(changes),
                    graph_revision=state.graph_revision + 1,
                    created_at=evidence.created_at,
                )
            )

        state.action_confirmation = None
        state.decision_analysis_waiver = None
        state.decision_model_proposal = None
        state.decision_model = None
        state.decision_analysis_result = None
        state.stop_evaluation = self.evaluate_stop(state)
        state.graph_revision += 1
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        state.graph = self.build_decision_graph(state)
        self._audit(
            state,
            "invalid_actions_reconstructed",
            "Rejected non-action paths and reconstructed executable management alternatives.",
            {
                "rejected_labels": prior_labels,
                "replacement_actions": [item.label for item in state.hypotheses],
                "internal_evidence_replayed": len(state.decision_impacts),
            },
        )
        return True

    def reassess_retained_evidence(self, state: V2RunState) -> bool:
        """Re-evaluate previously retained answers after deterministic rules improve.

        Only the most recent unresolved answer for a question is eligible, so a
        migration cannot double-count repeated clarification attempts.
        """
        question_by_id = {
            item.question_id: item
            for item in state.internal_questions
            if item.status != "answered" and not item.answer_id
        }
        selected: Dict[str, InternalEvidence] = {}
        for evidence in reversed(state.internal_evidence):
            if (
                evidence.retracted
                or evidence.decision_usable
                or evidence.question_id not in question_by_id
                or evidence.question_id in selected
                or evidence.interpretation_method == EVIDENCE_RULE_VERSION
            ):
                continue
            selected[evidence.question_id] = evidence
        if not selected:
            return False

        changed = False
        applied = 0
        for question_id, evidence in selected.items():
            question = question_by_id[question_id]
            interpretation, interpretation_rationale = self._interpret_answer(
                evidence.answer,
                question.category,
            )
            relevant, relevance_rationale = self._answer_relevance(
                evidence.answer,
                question.category,
            )
            usable = bool(
                evidence.confidence >= ACTIONABLE_CONFIDENCE
                and interpretation != "uncertain"
                and relevant
            )
            evidence.interpretation = interpretation
            evidence.question_relevant = relevant
            evidence.interpretation_method = EVIDENCE_RULE_VERSION
            evidence.interpretation_rationale = (
                f"{interpretation_rationale} {relevance_rationale}".strip()
            )
            evidence.decision_usable = usable
            changed = True
            if not usable:
                continue

            question.status = "answered"
            question.answer_id = evidence.evidence_id
            changes = self._apply_hypothesis_changes(state, question, evidence)
            self._update_assumption_statuses(
                state,
                question.category,
                interpretation,
            )
            strengthened = sum(change.delta > 0.001 for change in changes)
            weakened = sum(change.delta < -0.001 for change in changes)
            pruned = sum(change.after_status == "pruned" for change in changes)
            state.decision_impacts.append(
                DecisionImpact(
                    impact_id=_stable_id("impact", evidence.evidence_id),
                    question_id=question.question_id,
                    evidence_id=evidence.evidence_id,
                    summary=(
                        f"Reassessed internal evidence strengthened {strengthened} action(s), "
                        f"weakened {weakened} action(s), and pruned {pruned} action(s)."
                    ),
                    hypothesis_changes=changes,
                    graph_change_summary=self._graph_change_summary(changes),
                    graph_revision=state.graph_revision + 1,
                    created_at=evidence.created_at,
                )
            )
            applied += 1

        if applied:
            self._refresh_internal_questions(state)
            state.graph_revision += 1
        state.stop_evaluation = self.evaluate_stop(state)
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        state.graph = self.build_decision_graph(state)
        self._audit(
            state,
            "retained_evidence_reassessed",
            "Re-evaluated retained internal evidence under the current deterministic rules.",
            {
                "answers_reassessed": len(selected),
                "answers_applied": applied,
                "rule_version": EVIDENCE_RULE_VERSION,
                "raw_answer_logged": False,
            },
        )
        return changed

    def submit_answer(
        self,
        state: V2RunState,
        question_id: str,
        answer: str,
        *,
        submitted_by: str = "decision_owner",
        confidential: bool = True,
        confidence: float = 0.8,
        interpretation: Optional[str] = None,
        evidence_id: Optional[str] = None,
        submitted_by_actor_id: str = "local-workspace",
        visibility: str = "restricted",
        classification: str = "internal_confidential",
        supersedes_evidence_id: Optional[str] = None,
        retention_policy: str = "inherit_run_policy",
        retention_until: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> V2RunState:
        answer = (answer or "").strip()
        if not answer:
            raise ValueError("answer is required")
        question = next((item for item in state.internal_questions if item.question_id == question_id), None)
        if not question:
            raise ValueError(f"Unknown internal question: {question_id}")
        if question.status == "answered" or question.answer_id:
            raise ValueError(f"Internal question already answered: {question_id}")
        if question.status != "requested":
            raise ValueError(
                "Only the currently requested highest-value internal question can be answered."
            )
        if state.stop_evaluation and state.stop_evaluation.should_stop:
            raise ValueError("This decision case has stopped; reopen it before adding more evidence.")

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be a finite number from 0 to 1") from exc
        if not math.isfinite(confidence_value) or not 0.0 <= confidence_value <= 1.0:
            raise ValueError("confidence must be a finite number from 0 to 1")

        answer_interpretation, interpretation_rationale = self._interpret_answer(
            answer,
            question.category,
        )
        question_relevant, relevance_rationale = self._answer_relevance(
            answer,
            question.category,
        )
        interpretation_rationale = f"{interpretation_rationale} {relevance_rationale}".strip()
        explicit_interpretation = self._normalize_explicit_interpretation(interpretation)
        if explicit_interpretation and explicit_interpretation != answer_interpretation:
            raise ValueError(
                "Provided interpretation conflicts with the answer; remove it or make the answer explicit."
            )
        decision_usable = (
            confidence_value >= ACTIONABLE_CONFIDENCE
            and answer_interpretation != "uncertain"
            and question_relevant
        )
        evidence_id = evidence_id or f"internal_{uuid4().hex[:16]}"
        evidence = InternalEvidence(
            evidence_id=evidence_id,
            question_id=question_id,
            answer=answer,
            interpretation=answer_interpretation,
            confidence=confidence_value,
            decision_usable=decision_usable,
            question_relevant=question_relevant,
            interpretation_method=EVIDENCE_RULE_VERSION,
            interpretation_rationale=interpretation_rationale,
            submitted_by=(submitted_by or "decision_owner").strip(),
            submitted_by_actor_id=submitted_by_actor_id,
            confidential=bool(confidential),
            visibility=visibility,
            classification=classification,
            supersedes_evidence_id=supersedes_evidence_id,
            retention_policy=retention_policy,
            retention_until=retention_until,
            outbound_external_use=False,
            **({"created_at": created_at} if created_at else {}),
        )
        state.internal_evidence.append(evidence)

        if not decision_usable:
            state.stop_evaluation = self.evaluate_stop(state)
            state.decision_completion = build_decision_completion(state)
            state.workflow_stage = state.decision_completion["stage"]
            state.graph_revision += 1
            state.graph = self.build_decision_graph(state)
            self._audit(
                state,
                "answer_insufficient",
                "Internal evidence was retained but did not resolve the requested question.",
                {
                    "question_id": question_id,
                    "evidence_id": evidence_id,
                    "interpretation": answer_interpretation,
                    "confidence": confidence_value,
                    "minimum_actionable_confidence": ACTIONABLE_CONFIDENCE,
                    "question_relevant": question_relevant,
                    "raw_answer_logged": False,
                    "outbound_external_use": False,
                },
            )
            self._audit(
                state,
                "decision_graph_updated",
                "Decision graph revision added internal evidence that was retained without resolving the question.",
                {
                    "evidence_id": evidence_id,
                    "question_id": question_id,
                    "revision": state.graph_revision,
                    "decision_usable": False,
                    "changes": [],
                },
            )
            self._audit_stop(state)
            return state

        answered_rank = question.rank
        question.status = "answered"
        question.answer_id = evidence_id

        changes = self._apply_hypothesis_changes(state, question, evidence)
        self._update_assumption_statuses(state, question.category, answer_interpretation)
        self._refresh_internal_questions(state)

        strengthened = [change for change in changes if change.delta > 0.001]
        weakened = [change for change in changes if change.delta < -0.001]
        pruned = [change for change in changes if change.after_status == "pruned"]
        summary = (
            f"Internal evidence {evidence_id} strengthened {len(strengthened)} path(s), "
            f"weakened {len(weakened)} path(s), and pruned {len(pruned)} path(s)."
        )
        state.graph_revision += 1
        impact = DecisionImpact(
            impact_id=_stable_id("impact", evidence_id),
            question_id=question_id,
            evidence_id=evidence_id,
            summary=summary,
            hypothesis_changes=changes,
            graph_change_summary=self._graph_change_summary(changes),
            graph_revision=state.graph_revision,
        )
        state.decision_impacts.append(impact)
        state.stop_evaluation = self.evaluate_stop(state)
        if state.stop_evaluation.should_stop:
            for pending_question in state.internal_questions:
                if pending_question.status in {"pending", "requested"}:
                    pending_question.status = "deferred"
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        state.graph = self.build_decision_graph(state)

        self._audit(
            state,
            "internal_answer_received",
            f"Received internal evidence for ranked question {answered_rank}.",
            {
                "question_id": question_id,
                "evidence_id": evidence_id,
                "interpretation": answer_interpretation,
                "interpretation_rationale": interpretation_rationale,
                "confidential": evidence.confidential,
                "raw_answer_logged": False,
                "outbound_external_use": False,
            },
        )
        self._audit(
            state,
            "decision_graph_updated",
            impact.graph_change_summary,
            {
                "impact_id": impact.impact_id,
                "revision": state.graph.get("revision", 0),
                "changes": [change.model_dump(mode="json") for change in changes],
            },
        )
        self._audit_stop(state)
        return state

    def propose_internal_question(
        self,
        state: V2RunState,
        question_text: str,
        category: str,
        *,
        owner_hint: str = "Decision owner",
    ) -> V2RunState:
        """Admit a user question without increasing the bounded question budget."""
        question_text = (question_text or "").strip()
        category = (category or "").strip().lower()
        owner_hint = (owner_hint or "Decision owner").strip()
        if not question_text:
            raise ValueError("question is required")
        if category not in self.INTERNAL_QUESTION_CATEGORIES:
            raise ValueError("category is not supported")
        if state.stop_evaluation and state.stop_evaluation.should_stop:
            raise ValueError("This decision case has stopped; no additional question is material.")

        candidates = self._build_internal_questions(state, enforce_core_bound=False)
        candidate = next((item for item in candidates if item.category == category), None)
        if not candidate or candidate.question_priority_score < MATERIALITY_THRESHOLD:
            raise ValueError(
                f"The proposed question does not clear the Question Priority threshold of {MATERIALITY_THRESHOLD:.1f}."
            )

        existing = next(
            (
                item for item in state.internal_questions
                if item.category == category and item.status != "answered"
            ),
            None,
        )
        if existing:
            existing.question = question_text
            existing.owner_hint = owner_hint
            existing.origin = "user_proposed"
            existing.question_priority_score = candidate.question_priority_score
            existing.value_components = candidate.value_components
            existing.maximum_plausible_swing = candidate.maximum_plausible_swing
            existing.report_coverage = candidate.report_coverage
        else:
            candidate.question_id = _stable_id("question_user", f"{category}:{question_text}")
            candidate.question = question_text
            candidate.owner_hint = owner_hint
            candidate.origin = "user_proposed"
            candidate.status = "pending"
            replaceable = [
                item for item in state.internal_questions
                if item.status in {"pending", "requested", "deferred"}
            ]
            if len(state.internal_questions) >= MAX_INTERNAL_QUESTIONS:
                if not replaceable:
                    raise ValueError("The bounded internal-question budget is already resolved.")
                non_requested = [item for item in replaceable if item.status != "requested"]
                replaced = min(
                    non_requested or replaceable,
                    key=lambda item: item.question_priority_score,
                )
                state.internal_questions = [
                    item for item in state.internal_questions if item.question_id != replaced.question_id
                ]
            state.internal_questions.append(candidate)

        state.internal_questions.sort(
            key=lambda item: item.question_priority_score,
            reverse=True,
        )
        for rank, item in enumerate(state.internal_questions, 1):
            item.rank = rank
        self._activate_next_question(state.internal_questions)
        state.stop_evaluation = self.evaluate_stop(state)
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        state.graph_revision += 1
        state.graph = self.build_decision_graph(state)
        self._audit(
            state,
            "internal_question_proposed",
            "A user-proposed internal question passed materiality review and entered the bounded queue.",
            {
                "category": category,
                "question_priority_score": candidate.question_priority_score,
                "question_count": len(state.internal_questions),
                "max_internal_questions": MAX_INTERNAL_QUESTIONS,
            },
        )
        return state

    def evaluate_stop(self, state: V2RunState) -> StopEvaluation:
        ranked = sorted(
            (item for item in state.hypotheses if item.status != "pruned"),
            key=lambda item: item.support_score,
            reverse=True,
        )
        leader = ranked[0] if ranked else None
        runner_up = ranked[1] if len(ranked) > 1 else None
        if leader and runner_up:
            margin = round(leader.support_score - runner_up.support_score, 3)
        elif leader and len(state.hypotheses) > 1:
            margin = 1.0
        else:
            margin = 0.0
        unique_leader = bool(leader and (runner_up is None or margin > 0.015))
        remaining_questions = [
            item
            for item in state.internal_questions
            if item.status in {"pending", "requested", "deferred"}
        ]
        remaining = sorted(
            (item.question_priority_score for item in remaining_questions),
            reverse=True,
        )
        remaining_value = remaining[0] if remaining else 0.0
        max_remaining_swing = max(
            (item.maximum_plausible_swing for item in remaining_questions),
            default=0.0,
        )
        answered_count = sum(item.status == "answered" for item in state.internal_questions)

        should_stop = False
        if state.hypotheses and not ranked:
            should_stop = True
            reason = "Stop: every explicit decision path has been disqualified by internal evidence."
        elif not remaining:
            should_stop = True
            reason = (
                "Stop: every ranked decision-critical internal question has been resolved or fell "
                "below the materiality threshold."
            )
        elif answered_count >= MAX_INTERNAL_QUESTIONS:
            should_stop = True
            reason = f"Stop: the bounded internal-information budget of {MAX_INTERNAL_QUESTIONS} questions is exhausted."
        elif answered_count == 0:
            if state.internal_evidence:
                reason = (
                    "Continue: internal evidence was supplied but none was actionable enough to resolve a "
                    f"question; the highest remaining Question Priority Score is {remaining_value:.1f}."
                )
            else:
                reason = (
                    "Continue: no internal evidence has been supplied, and the highest-value private fact "
                    f"still has a Question Priority Score of {remaining_value:.1f}."
                )
        elif remaining_value < MATERIALITY_THRESHOLD:
            should_stop = True
            reason = (
                f"Stop: the highest remaining Question Priority Score is {remaining_value:.1f}, below the "
                f"materiality threshold of {MATERIALITY_THRESHOLD:.1f}."
            )
        else:
            reason = (
                f"Continue: a remaining internal question scores {remaining_value:.1f}; its maximum plausible "
                f"branch swing is {max_remaining_swing:.0%}, versus a {margin:.0%} leading margin."
            )

        return StopEvaluation(
            should_stop=should_stop,
            reason=reason,
            remaining_question_priority=round(remaining_value, 1),
            highest_unanswered_priority=round(remaining_value, 1),
            max_remaining_plausible_swing=round(max_remaining_swing, 3),
            materiality_threshold=MATERIALITY_THRESHOLD,
            leading_hypothesis_id=leader.hypothesis_id if unique_leader else None,
            leading_margin=margin,
        )

    def recommendation(self, state: V2RunState) -> str:
        if not state.hypotheses:
            return "No recommendation is available because no decision paths were generated."
        ranked = sorted(
            (item for item in state.hypotheses if item.status != "pruned"),
            key=lambda item: item.support_score,
            reverse=True,
        )
        if not ranked:
            return "No recommendation is available because every decision path is explicitly disqualified."
        leader = ranked[0]
        if len(ranked) > 1 and leader.support_score - ranked[1].support_score <= 0.015:
            tied = [
                item.label
                for item in ranked
                if leader.support_score - item.support_score <= 0.015
            ]
            return (
                f"No unique recommendation: all {len(tied)} tied paths "
                f"({'; '.join(tied)}) remain tied on the evidence currently available."
            )
        if state.stop_evaluation and state.stop_evaluation.should_stop:
            return f"Recommend **{leader.label}** for the decision: {state.question}"
        return (
            f"Working recommendation: **{leader.label}**. Resolve the currently requested internal "
            "question before treating this as final."
        )

    def refresh_stop_evaluation(self, state: V2RunState) -> V2RunState:
        state.stop_evaluation = self.evaluate_stop(state)
        state.decision_completion = build_decision_completion(state)
        state.workflow_stage = state.decision_completion["stage"]
        previous_graph = state.graph
        refreshed_graph = self.build_decision_graph(state)
        if self._graph_content(refreshed_graph) != self._graph_content(previous_graph):
            state.graph_revision += 1
            refreshed_graph = self.build_decision_graph(state)
            self._audit(
                state,
                "decision_graph_updated",
                "Decision graph revision updated the decision stop status.",
                {
                    "revision": state.graph_revision,
                    "changes": [],
                    "reason": "stop_evaluation_changed_graph_state",
                },
            )
        state.graph = refreshed_graph
        self._audit_stop(state)
        return state

    def record_memo_generated(self, state: V2RunState) -> None:
        completion = build_decision_completion(state)
        state.decision_completion = completion
        self._audit(
            state,
            "memo_generated",
            "Generated the executive decision memo from the current evidence and stop state.",
            {
                "status": "final" if completion["final_approval_ready"] else (
                    "blocked" if completion["internal_evidence_complete"] else "interim"
                ),
                "external_llm_calls": state.token_usage.external_llm_calls,
                "total_tokens": state.token_usage.total_tokens,
            },
        )

    def build_decision_graph(self, state: V2RunState) -> Dict:
        nodes: List[Dict] = [
            {
                "id": "decision_goal",
                "type": "decision",
                "label": state.question or state.project_name,
                "status": "stopped" if state.stop_evaluation and state.stop_evaluation.should_stop else "active",
            }
        ]
        edges: List[Dict] = []

        for hypothesis in state.hypotheses:
            nodes.append(
                {
                    "id": hypothesis.hypothesis_id,
                    "type": "hypothesis",
                    "label": hypothesis.label,
                    "status": hypothesis.status,
                    "score": hypothesis.support_score,
                    "delta": hypothesis.last_change,
                    "prune_reason": hypothesis.prune_reason,
                }
            )
            edges.append(
                {
                    "id": f"edge_decision_{hypothesis.hypothesis_id}",
                    "source": "decision_goal",
                    "target": hypothesis.hypothesis_id,
                    "type": "decision_path",
                    "status": hypothesis.status,
                    "weight": hypothesis.support_score,
                }
            )

        claim_lookup = {claim.claim_id: claim for claim in state.claims}
        included_claims = set()
        for hypothesis in state.hypotheses:
            for claim_id in hypothesis.supporting_claim_ids[:4]:
                claim = claim_lookup.get(claim_id)
                if not claim:
                    continue
                if claim_id not in included_claims:
                    included_claims.add(claim_id)
                    nodes.append(
                        {
                            "id": claim_id,
                            "type": "sourced_fact",
                            "label": claim.text[:120],
                            "status": claim.provenance_status,
                            "citations": [item.model_dump(mode="json") for item in claim.citations],
                        }
                    )
                edges.append(
                    {
                        "id": f"edge_{claim_id}_{hypothesis.hypothesis_id}",
                        "source": claim_id,
                        "target": hypothesis.hypothesis_id,
                        "type": "supports",
                        "status": "sourced",
                    }
                )
            for claim_id in hypothesis.opposing_claim_ids[:4]:
                claim = claim_lookup.get(claim_id)
                if not claim:
                    continue
                if claim_id not in included_claims:
                    included_claims.add(claim_id)
                    nodes.append(
                        {
                            "id": claim_id,
                            "type": "sourced_fact",
                            "label": claim.text[:120],
                            "status": claim.provenance_status,
                            "citations": [item.model_dump(mode="json") for item in claim.citations],
                        }
                    )
                edges.append(
                    {
                        "id": f"edge_{claim_id}_{hypothesis.hypothesis_id}_opposes",
                        "source": claim_id,
                        "target": hypothesis.hypothesis_id,
                        "type": "opposes",
                        "status": "sourced",
                    }
                )

        for contradiction in state.contradictions:
            nodes.append(
                {
                    "id": contradiction.contradiction_id,
                    "type": "contradiction",
                    "label": contradiction.summary,
                    "status": contradiction.status,
                    "severity": contradiction.severity,
                }
            )
            for claim_id in contradiction.claim_ids:
                claim = claim_lookup.get(claim_id)
                if claim and claim_id not in included_claims:
                    included_claims.add(claim_id)
                    nodes.append(
                        {
                            "id": claim_id,
                            "type": "sourced_fact",
                            "label": claim.text[:120],
                            "status": claim.provenance_status,
                            "citations": [item.model_dump(mode="json") for item in claim.citations],
                        }
                    )
                edges.append(
                    {
                        "id": f"edge_{claim_id}_{contradiction.contradiction_id}",
                        "source": claim_id,
                        "target": contradiction.contradiction_id,
                        "type": "conflicts_in",
                        "status": contradiction.status,
                    }
                )

        for assumption in state.assumptions:
            nodes.append(
                {
                    "id": assumption.assumption_id,
                    "type": "assumption",
                    "label": assumption.text,
                    "status": assumption.status,
                }
            )
            for hypothesis in state.hypotheses:
                if assumption.assumption_id in hypothesis.assumption_ids:
                    edges.append(
                        {
                            "id": f"edge_{assumption.assumption_id}_{hypothesis.hypothesis_id}",
                            "source": assumption.assumption_id,
                            "target": hypothesis.hypothesis_id,
                            "type": "depends_on",
                            "status": assumption.status,
                        }
                    )

        evidence_lookup = {item.evidence_id: item for item in state.internal_evidence}
        impact_lookup = {item.evidence_id: item for item in state.decision_impacts}
        included_evidence = set()
        for question in state.internal_questions:
            nodes.append(
                {
                    "id": question.question_id,
                    "type": "internal_question",
                    "label": question.question,
                    "status": question.status,
                    "question_priority_score": question.question_priority_score,
                }
            )
            for hypothesis_id in question.affected_hypothesis_ids:
                edges.append(
                    {
                        "id": f"edge_{question.question_id}_{hypothesis_id}",
                        "source": question.question_id,
                        "target": hypothesis_id,
                        "type": "could_change",
                        "status": question.status,
                    }
                )
            if question.answer_id and question.answer_id in evidence_lookup:
                evidence = evidence_lookup[question.answer_id]
                included_evidence.add(evidence.evidence_id)
                nodes.append(
                    {
                        "id": evidence.evidence_id,
                        "type": "internal_evidence",
                        "label": f"Internal answer to rank {question.rank}",
                        "status": evidence.interpretation,
                        "confidential": evidence.confidential,
                    }
                )
                edges.append(
                    {
                        "id": f"edge_{evidence.evidence_id}_{question.question_id}",
                        "source": evidence.evidence_id,
                        "target": question.question_id,
                        "type": "answers",
                        "status": "internal_only",
                    }
                )
                impact = impact_lookup.get(evidence.evidence_id)
                if impact:
                    for change in impact.hypothesis_changes:
                        effect_type = (
                            "supports"
                            if change.delta > 0.001
                            else ("opposes" if change.delta < -0.001 else "no_material_effect")
                        )
                        edges.append(
                            {
                                "id": f"edge_{evidence.evidence_id}_{change.hypothesis_id}_effect",
                                "source": evidence.evidence_id,
                                "target": change.hypothesis_id,
                                "type": effect_type,
                                "status": change.after_status,
                                "delta": change.delta,
                                "before_score": change.before_score,
                                "after_score": change.after_score,
                                "interpretation": evidence.interpretation,
                                "interpretation_rationale": evidence.interpretation_rationale,
                                "revision": impact.graph_revision,
                            }
                        )

        for evidence in state.internal_evidence:
            if evidence.evidence_id in included_evidence:
                continue
            nodes.append(
                {
                    "id": evidence.evidence_id,
                    "type": "internal_evidence",
                    "label": "Internal evidence retained without resolving the question",
                    "status": evidence.interpretation,
                    "decision_usable": evidence.decision_usable,
                    "confidential": evidence.confidential,
                }
            )
            edges.append(
                {
                    "id": f"edge_{evidence.evidence_id}_{evidence.question_id}",
                    "source": evidence.evidence_id,
                    "target": evidence.question_id,
                    "type": "attempted_answer",
                    "status": "insufficient_evidence",
                }
            )

        return {
            "schema": "decision_graph_v2",
            "revision": state.graph_revision,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "legend": {
                "sourced_fact": "Imported report statement with preserved provenance",
                "assumption": "FOREFOLD-generated interpretation awaiting internal validation",
                "internal_question": "Organization-only fact ranked by Question Priority Score",
                "internal_evidence": "Private answer stored locally; never sent upstream",
            },
        }

    def _graph_content(self, graph: Optional[Dict]) -> Dict:
        """Return graph semantics without its monotonic revision marker."""
        content = dict(graph or {})
        content.pop("revision", None)
        return content

    def _build_assumptions(self, question: str) -> List[DecisionAssumption]:
        decision = question or "the proposed decision"
        specs = [
            (
                "strategic_success",
                f"The organization has a shared, measurable definition of success for '{decision}'.",
                "Public evidence cannot establish the organization's private priorities or success threshold.",
            ),
            (
                "financial_capacity",
                "Approved budget and downside capacity are sufficient for the preferred path.",
                "External research cannot verify current internal budget approvals, runway, or opportunity cost.",
            ),
            (
                "execution_capacity",
                "A named owner and sufficient operating capacity exist to execute the decision.",
                "Team capacity, ownership, and delivery constraints are organization-private facts.",
            ),
            (
                "constraints",
                "No internal legal, security, procurement, or policy constraint disqualifies the preferred path.",
                "Non-public controls and contractual constraints can invalidate an otherwise attractive option.",
            ),
            (
                "timing",
                "The decision window and internal implementation timeline are compatible.",
                "External market timing does not reveal internal dependencies or approval lead times.",
            ),
            (
                "risk_tolerance",
                "The organization's downside tolerance is consistent with the preferred path.",
                "Risk appetite is a governance choice, not a fact the public web can answer.",
            ),
        ]
        return [
            DecisionAssumption(
                assumption_id=_stable_id("assumption", category),
                text=text,
                category=category,
                rationale=rationale,
            )
            for category, text, rationale in specs
        ]

    def _build_hypotheses(
        self,
        decision: str,
        claims: Sequence[ExtractedClaim],
        assumptions: Sequence[DecisionAssumption],
    ) -> List[DecisionHypothesis]:
        positive = [claim for claim in claims if self._claim_polarity(claim.text) > 0]
        negative = [claim for claim in claims if self._claim_polarity(claim.text) < 0]
        neutral = [claim for claim in claims if claim not in positive and claim not in negative]
        assumption_ids = [item.assumption_id for item in assumptions]
        weighted_positive = sum(claim.confidence for claim in positive)
        weighted_negative = sum(claim.confidence for claim in negative)
        weighted_neutral = sum(claim.confidence for claim in neutral)
        evidence_total = weighted_positive + weighted_negative + weighted_neutral
        balance = (
            (weighted_positive - weighted_negative) / evidence_total
            if evidence_total
            else 0.0
        )
        neutral_share = weighted_neutral / evidence_total if evidence_total else 1.0

        options = self._infer_decision_options(decision)
        explicit_option_count = self._explicit_option_count(decision)
        named_alternatives = self._explicit_options_are_named(options, explicit_option_count)
        option_term_sets = [self._option_terms(label) for label, _role in options]
        option_term_counts = Counter(term for terms in option_term_sets for term in terms)
        option_labels = [label for label, _role in options]
        claim_option_mentions = [
            self._mentioned_option_indices(claim.text, option_labels)
            for claim in claims
        ]
        claim_option_exclusions = [
            self._comparative_rhs_option_indices(claim.text, option_labels)
            for claim in claims
        ]
        role_counts: Dict[str, int] = {}
        for _label, role in options:
            role_counts[role] = role_counts.get(role, 0) + 1

        hypotheses: List[DecisionHypothesis] = []
        for index, (label, role) in enumerate(options, 1):
            raw_option_terms = option_term_sets[index - 1]
            option_terms = {
                term for term in raw_option_terms if option_term_counts[term] == 1
            } or raw_option_terms
            matched = [
                claim
                for claim, mentioned_options, excluded_options in zip(
                    claims,
                    claim_option_mentions,
                    claim_option_exclusions,
                )
                if index - 1 not in excluded_options
                and (
                    index - 1 in mentioned_options
                or (
                    not mentioned_options
                    and option_terms & self._evidence_terms(claim.text)
                )
                )
            ]
            matched_positive = [
                claim
                for claim in matched
                if self._claim_polarity_for_option(claim.text, index - 1, option_labels) > 0
            ]
            matched_negative = [
                claim
                for claim in matched
                if self._claim_polarity_for_option(claim.text, index - 1, option_labels) < 0
            ]
            directional_matched = matched_positive + matched_negative
            matched_weight = sum(claim.confidence for claim in directional_matched) or 0.0
            matched_balance = (
                (
                    sum(claim.confidence for claim in matched_positive)
                    - sum(claim.confidence for claim in matched_negative)
                )
                / matched_weight
                if matched_weight
                else 0.0
            )

            option_specific = named_alternatives and 0 < index <= explicit_option_count
            if not evidence_total:
                score = 0.35
                supporting, opposing = [], []
            elif option_specific:
                coverage = min(1.0, len(directional_matched) / 3.0)
                score = 0.35 + 0.22 * matched_balance + 0.08 * coverage
                supporting, opposing = matched_positive, matched_negative
            elif role == "immediate":
                score = 0.42 + 0.30 * balance - 0.08 * neutral_share
                supporting, opposing = positive, negative
            elif role == "staged":
                score = 0.38 + 0.20 * neutral_share + 0.10 * (1.0 - abs(balance))
                supporting, opposing = neutral + positive, negative
            elif role == "defer":
                score = 0.34 - 0.30 * balance + 0.05 * (
                    weighted_negative / evidence_total if evidence_total else 0.0
                )
                supporting, opposing = negative, positive
            else:
                coverage = min(1.0, len(directional_matched) / 3.0)
                score = 0.35 + 0.22 * matched_balance + 0.08 * coverage
                supporting, opposing = matched_positive, matched_negative

            score = round(_clamp(score, 0.05, 0.95), 3)
            if role == "immediate" and role_counts[role] == 1:
                hypothesis_id = "hypothesis_proceed"
            elif role == "staged" and role_counts[role] == 1:
                hypothesis_id = "hypothesis_stage"
            elif role == "defer" and role_counts[role] == 1:
                hypothesis_id = "hypothesis_defer"
            else:
                hypothesis_id = f"hypothesis_option_{index}"

            description = self._option_description(label, role)
            rationale = (
                "Generated interpretation from imported evidence: "
                f"{len(supporting)} supporting, {len(opposing)} opposing, and "
                f"{len(neutral)} directionally neutral claim(s) were considered. "
                "The score is relative decision support, not a probability."
            )
            hypotheses.append(
                DecisionHypothesis(
                    hypothesis_id=hypothesis_id,
                    label=label,
                    description=description,
                    status="active" if supporting or opposing else "unsupported",
                    decision_role=role,
                    support_score=score,
                    previous_score=score,
                    rationale=rationale,
                    supporting_claim_ids=[claim.claim_id for claim in supporting[:8]],
                    opposing_claim_ids=[claim.claim_id for claim in opposing[:8]],
                    assumption_ids=assumption_ids,
                )
            )

        ranked = sorted(hypotheses, key=lambda item: item.support_score, reverse=True)
        if ranked and (len(ranked) == 1 or ranked[0].support_score - ranked[1].support_score > 0.015):
            ranked[0].status = "leading"
        return hypotheses

    def _infer_decision_options(self, decision: str) -> List[Tuple[str, str]]:
        options = self._parse_executable_options(decision)
        if len(options) < 2:
            options = [
                ("Proceed with the proposed initiative", "immediate"),
                ("Run a smaller, controlled pilot", "staged"),
                ("Redesign the initiative before launch", "redesign"),
                ("Cancel or defer the initiative", "defer"),
            ]
        elif not any(role == "defer" for _label, role in options) and len(options) < 4:
            options.append(("Cancel or defer the initiative", "defer"))
        return options[:4]

    def _decision_clause(self, decision: str) -> str:
        text = re.sub(r"\s+", " ", decision or "").strip()
        if not text:
            return ""
        matches = list(
            re.finditer(
                r"\b(?:determine|decide|assess|evaluate|recommend)\s+(?:whether|which(?:\s+of)?)\s+(.+)",
                text,
                flags=re.IGNORECASE,
            )
        )
        if matches:
            return matches[-1].group(1).strip(" ?.\t\n")
        whether_matches = list(re.finditer(r"\bwhether\s+(.+)", text, flags=re.IGNORECASE))
        if whether_matches:
            return whether_matches[-1].group(1).strip(" ?.\t\n")
        return re.sub(r"^\s*should\s+", "", text, flags=re.IGNORECASE).strip(" ?.\t\n")

    def _parse_executable_options(self, decision: str) -> List[Tuple[str, str]]:
        clause = self._decision_clause(decision)
        raw_parts = [
            part.strip(" ,.;")
            for part in re.split(r"\s*[,;]\s*(?:or\s+)?|\s+or\s+", clause, flags=re.IGNORECASE)
            if part.strip(" ,.;")
        ][:8]
        if len(raw_parts) < 2:
            return []

        raw_parts[0] = re.sub(
            r"^(?:we|management|the organization|the company)\s+",
            "",
            raw_parts[0],
            flags=re.IGNORECASE,
        )
        first_tokens = raw_parts[0].split()
        if (
            len(first_tokens) >= 2
            and re.fullmatch(r"[A-Z][A-Za-z0-9&.'-]*", first_tokens[0])
            and first_tokens[1].lower() in ACTION_VERBS
        ):
            raw_parts[0] = " ".join(first_tokens[1:])

        inherited_verb = next(
            (
                token
                for token in re.findall(r"[a-z]+", raw_parts[0].lower())[:3]
                if token in ACTION_VERBS
            ),
            None,
        )
        options: List[Tuple[str, str]] = []
        seen: set[str] = set()
        for part in raw_parts:
            normalized = self._normalize_action_candidate(part, inherited_verb)
            if not normalized or not is_executable_action_label(normalized):
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            lower = normalized.lower()
            if any(term in lower for term in ("cancel", "defer", "postpone", "decline", "no action")):
                role = "defer"
            elif any(term in lower for term in ("stage", "pilot", "phase", "trial", "reversible", "controlled")):
                role = "staged"
            elif any(term in lower for term in ("redesign", "revise", "modify", "rework")):
                role = "redesign"
            elif any(
                term in lower
                for term in (
                    "proceed", "launch", "expand", "accelerate", "commit",
                    "implement", "rollout", "restructure now", "immediate",
                )
            ):
                role = "immediate"
            else:
                role = "alternative"
            options.append((normalized, role))
        return options[:4]

    def _normalize_action_candidate(
        self,
        candidate: str,
        inherited_verb: Optional[str],
    ) -> str:
        value = re.sub(r"\s+", " ", candidate or "").strip(" ,.;:?")
        value = re.sub(
            r"^(?:momentum\s+(?:builds?|moves?)\s+toward|the\s+outcome\s+is|to)\s+",
            "",
            value,
            flags=re.IGNORECASE,
        )
        lower = value.lower()
        if re.fullmatch(r"(?:a\s+)?(?:full\s+)?national rollout", lower):
            return "Proceed to a national rollout"
        if re.fullmatch(r"(?:a\s+)?(?:smaller|limited|controlled|tightly controlled)?\s*pilot", lower):
            return "Run a smaller, controlled pilot"
        if re.fullmatch(r"(?:a\s+)?(?:redesign|revision|rework)", lower):
            return "Redesign the benefit and operating model before launch"
        if re.fullmatch(r"(?:a\s+)?(?:cancel|cancellation|postpone|postponement)", lower):
            return "Cancel or postpone the initiative"

        tokens = re.findall(r"[a-z0-9]+", lower)
        if tokens and tokens[0] not in ACTION_VERBS and inherited_verb:
            value = f"{inherited_verb.capitalize()} {value}"
        return value[:1].upper() + value[1:] if value else ""

    def _explicit_option_count(self, decision: str) -> int:
        """Count options supplied by the decision owner, excluding generated fallbacks."""
        return len(self._parse_executable_options(decision))

    def _explicit_options_are_named(
        self,
        options: Sequence[Tuple[str, str]],
        explicit_option_count: int,
    ) -> bool:
        """Distinguish named alternatives from generic proceed/stage/defer paths."""
        if explicit_option_count < 2:
            return False
        generic_path_terms = {
            "a", "an", "the", "now", "proceed", "launch", "expand", "restructure",
            "implement", "stage", "staged", "phase", "phased", "pilot", "trial",
            "reversible", "defer", "deferred", "delay", "delayed", "wait", "decline",
            "decision", "option", "path", "choose", "select", "use", "with", "no",
            "action", "proposed",
        }
        explicit_options = options[:explicit_option_count]
        distinguishing_terms = [
            {
                token
                for token in self._option_phrase_tokens(label)
                if token not in generic_path_terms
            }
            for label, _role in explicit_options
        ]
        return all(distinguishing_terms)

    def _option_terms(self, label: str) -> set[str]:
        stopwords = {
            "the", "a", "an", "to", "with", "and", "or", "for", "of", "decision",
            "proceed", "choose", "select", "option", "proposed", "now",
        }
        terms = {
            token
            for token in re.findall(r"[a-z0-9]+", label.lower())
            if len(token) >= 2 and token not in stopwords
        }
        tokens = re.findall(r"[a-z0-9]+", label.lower())
        compounds = {
            f"{tokens[index - 1]}_{token}"
            for index, token in enumerate(tokens)
            if index > 0 and len(token) == 1 and tokens[index - 1] not in stopwords
        }
        return compounds or terms

    def _evidence_terms(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9]+", self._semantic_text(text).lower())
        terms = {token for token in tokens if len(token) >= 2}
        terms.update(
            f"{tokens[index - 1]}_{token}"
            for index, token in enumerate(tokens)
            if index > 0 and len(token) == 1
        )
        return terms

    def _option_phrase_tokens(self, label: str) -> List[str]:
        """Normalize an option label while retaining discriminating one-letter suffixes."""
        tokens = re.findall(r"[a-z0-9]+", label.lower())
        removable_prefix = {
            "should", "we", "the", "organization", "company", "choose", "select",
            "option", "proceed", "with", "proposed", "implement", "use",
        }
        while tokens and tokens[0] in removable_prefix:
            tokens.pop(0)
        while tokens and tokens[-1] in {"decision", "option"}:
            tokens.pop()
        return tokens

    def _mentioned_option_indices(self, text: str, option_labels: Sequence[str]) -> set[int]:
        """Match explicit option entities, preferring a longer phrase over its subset.

        A separate occurrence of the shorter option is retained, so a sentence that
        explicitly compares ``Standard Plan`` with ``Standard Plan Plus`` targets both.
        """
        normalized_text = " ".join(
            re.findall(r"[a-z0-9]+", self._semantic_text(text).lower())
        )
        occurrences: List[Tuple[int, int, int, int]] = []
        for option_index, label in enumerate(option_labels):
            tokens = self._option_phrase_tokens(label)
            if not tokens:
                continue
            phrase = " ".join(tokens)
            for match in re.finditer(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized_text):
                occurrences.append((option_index, match.start(), match.end(), len(tokens)))

        retained: set[int] = set()
        for option_index, start, end, length in occurrences:
            shadowed = any(
                other_length > length
                and other_start <= start
                and end <= other_end
                for _other_index, other_start, other_end, other_length in occurrences
            )
            if not shadowed:
                retained.add(option_index)
        return retained

    def _split_option_evidence_clauses(
        self,
        text: str,
        option_labels: Sequence[str],
    ) -> List[str]:
        primary = [
            item.strip()
            for item in re.split(
                r"\b(?:but|however|whereas|while|yet)\b|[;\n]+",
                self._semantic_text(text),
                flags=re.IGNORECASE,
            )
            if item.strip()
        ]
        result: List[str] = []
        for clause in primary or [self._semantic_text(text)]:
            fragments = [
                item.strip()
                for item in re.split(r"\s*,\s*|\s+and\s+", clause, flags=re.IGNORECASE)
                if item.strip()
            ]
            if len(fragments) < 2:
                result.append(clause)
                continue
            current = fragments[0]
            for fragment in fragments[1:]:
                current_mentions = self._mentioned_option_indices(current, option_labels)
                fragment_mentions = self._mentioned_option_indices(fragment, option_labels)
                if (
                    current_mentions
                    and fragment_mentions
                    and self._claim_polarity(current)
                    and self._claim_polarity(fragment)
                ):
                    result.append(current)
                    current = fragment
                else:
                    current = f"{current} and {fragment}"
            result.append(current)
        return result

    def _comparative_rhs_option_indices(
        self,
        text: str,
        option_labels: Sequence[str],
    ) -> set[int]:
        excluded: set[int] = set()
        connector = re.compile(
            r"\b(?:than|compared\s+(?:with|to)|relative\s+to|versus|vs\.?)\b",
            re.IGNORECASE,
        )
        for clause in self._split_option_evidence_clauses(text, option_labels):
            for match in connector.finditer(clause):
                left = clause[: match.start()]
                right = clause[match.end() :]
                left_mentions = self._mentioned_option_indices(left, option_labels)
                right_mentions = self._mentioned_option_indices(right, option_labels)
                if left_mentions and right_mentions:
                    excluded.update(right_mentions)
                elif not left.strip() and "," in right:
                    benchmark, subject = right.split(",", 1)
                    benchmark_mentions = self._mentioned_option_indices(benchmark, option_labels)
                    subject_mentions = self._mentioned_option_indices(subject, option_labels)
                    if benchmark_mentions and subject_mentions:
                        excluded.update(benchmark_mentions)
        return excluded

    def _claim_polarity_for_option(
        self,
        text: str,
        option_index: int,
        option_labels: Sequence[str],
    ) -> int:
        excluded = self._comparative_rhs_option_indices(text, option_labels)
        if option_index in excluded:
            return 0
        clauses = self._split_option_evidence_clauses(text, option_labels)
        explicit_mentions = False
        polarities: List[int] = []
        for clause in clauses:
            mentions = self._mentioned_option_indices(clause, option_labels)
            explicit_mentions = explicit_mentions or bool(mentions)
            if option_index in mentions:
                polarity = self._claim_polarity(clause)
                if polarity:
                    polarities.append(polarity)
        if polarities:
            return 1 if all(item > 0 for item in polarities) else (
                -1 if all(item < 0 for item in polarities) else 0
            )
        return 0 if explicit_mentions else self._claim_polarity(text)

    def _option_description(self, label: str, role: str) -> str:
        descriptions = {
            "immediate": f"Take the '{label}' path now.",
            "staged": f"Use {label.lower()} to preserve reversibility while private facts are resolved.",
            "redesign": f"Use {label.lower()} to address operating and stakeholder risks before commitment.",
            "defer": f"Use {label.lower()} to protect downside while evidence or constraints remain unresolved.",
            "alternative": f"Select {label} over the other explicit decision alternatives.",
        }
        return descriptions[role]

    def _build_internal_questions(
        self,
        state: V2RunState,
        *,
        enforce_core_bound: bool = True,
    ) -> List[InternalQuestion]:
        hypotheses = state.hypotheses
        affected = [item.hypothesis_id for item in hypotheses]
        specs = [
            (
                "strategic_success",
                "What measurable outcome must this strategy achieve, and what is the minimum acceptable threshold?",
                "Executive sponsor / strategy",
                "The answer can reorder every path because the external report cannot know the organization's objective function.",
                (0.98, 0.95, 0.92, 0.90),
                "Could change the leading path and move relative support by up to 20 points.",
            ),
            (
                "constraints",
                "Is there any non-negotiable legal, security, procurement, policy, or contractual constraint that disqualifies a path?",
                "Legal / security / procurement",
                "A private hard constraint can prune a branch immediately, regardless of public evidence quality.",
                (0.97, 0.92, 0.88, 0.95),
                "Could immediately prune one or more decision branches.",
            ),
            (
                "financial_capacity",
                "What budget is actually approved, and what downside or payback limit must the decision stay within?",
                "Finance / budget owner",
                "Approved capacity—not market estimates—determines whether the preferred path is feasible.",
                (0.94, 0.96, 0.90, 0.88),
                "Could strengthen proceed, favor a staged pilot, or rule out commitment.",
            ),
            (
                "execution_capacity",
                "Who owns execution, and what team capacity can be committed without displacing higher-priority work?",
                "Operating owner",
                "The public report cannot observe staffing, ownership, or competing internal commitments.",
                (0.88, 0.93, 0.91, 0.82),
                "Could move support between immediate execution and a staged path by up to 15 points.",
            ),
            (
                "risk_tolerance",
                "What downside outcome would make leadership regret this decision, and how much exposure is acceptable?",
                "Executive sponsor / risk owner",
                "Risk appetite changes how the same external evidence should be converted into a recommendation.",
                (0.86, 0.90, 0.84, 0.78),
                "Could strengthen the defer path or validate a higher-commitment path.",
            ),
            (
                "timing",
                "What is the real decision deadline, and which internal dependencies determine the earliest feasible start?",
                "Program owner",
                "A time-sensitive opportunity can disappear, while internal dependencies can make immediate action impossible.",
                (0.78, 0.87, 0.92, 0.84),
                "Could change whether to proceed now or use a reversible staging step.",
            ),
        ]

        category_terms = {
            "strategic_success": {"growth", "benefit", "outcome", "success", "revenue", "customer", "demand"},
            "constraints": {"legal", "security", "procurement", "policy", "contract", "approval", "regulator"},
            "financial_capacity": {"budget", "funding", "funded", "cash", "liquidity", "debt", "payback", "loss"},
            "execution_capacity": {"capacity", "owner", "staff", "team", "execution", "supplier", "delivery"},
            "risk_tolerance": {"risk", "downside", "loss", "exposure", "regret", "tolerance"},
            "timing": {"deadline", "timing", "delay", "week", "month", "start", "window", "urgent"},
        }
        ranked_hypotheses = sorted(
            (item for item in hypotheses if item.status != "pruned"),
            key=lambda item: item.support_score,
            reverse=True,
        )
        if len(ranked_hypotheses) > 1:
            margin = ranked_hypotheses[0].support_score - ranked_hypotheses[1].support_score
        elif len(ranked_hypotheses) == 1 and len(hypotheses) > 1:
            margin = 1.0
        else:
            margin = 0.0
        closeness = _clamp(1.0 - margin / 0.50, 0.25, 1.0)
        report_text = " ".join(claim.text.lower() for claim in state.claims)
        private_gap_text = bool(
            re.search(r"\b(?:cannot|does not|doesn't|not reveal|private|internal|unknown|unresolved)\b", report_text)
        )
        contradiction_pressure = min(0.15, len(state.contradictions) * 0.03)

        questions: List[InternalQuestion] = []
        for category, question, owner, rationale, raw_components, expected_change in specs:
            terms = category_terms[category]
            relevant_claims = [
                claim
                for claim in state.claims
                if terms & set(re.findall(r"[a-z0-9]+", claim.text.lower()))
            ]
            coverage = min(1.0, len(relevant_claims) / 4.0)
            negative_pressure = min(
                1.0,
                sum(self._claim_polarity(claim.text) < 0 for claim in relevant_claims) / 3.0,
            )
            sensitivity = raw_components[0] * closeness + 0.08 * negative_pressure
            if category == "constraints":
                sensitivity = max(sensitivity, 0.82)
            uncertainty = (
                raw_components[1] * (1.0 - 0.25 * coverage)
                + contradiction_pressure
                + (0.05 if private_gap_text else 0.0)
            )
            sensitivity = _clamp(sensitivity)
            uncertainty = _clamp(uncertainty)
            preliminary_swing = 0.04 + 0.18 * sensitivity * uncertainty
            decision_relevance = (
                _clamp(preliminary_swing / margin, 0.05, 1.0)
                if margin > preliminary_swing and margin > 0
                else 1.0
            )
            sensitivity *= decision_relevance
            uncertainty *= decision_relevance
            urgency = raw_components[3] * decision_relevance
            components = QuestionPriorityBreakdown(
                decision_sensitivity=round(_clamp(sensitivity), 3),
                uncertainty=round(_clamp(uncertainty), 3),
                answerability=raw_components[2],
                urgency=round(_clamp(urgency), 3),
            )
            maximum_swing = round(preliminary_swing * decision_relevance, 3)
            expected_change = self._expected_change_text(category, maximum_swing)
            questions.append(
                InternalQuestion(
                    question_id=_stable_id("question", category),
                    question=question,
                    category=category,
                    rationale=rationale,
                    owner_hint=owner,
                    question_priority_score=_question_priority_score(components),
                    value_components=components,
                    expected_change=expected_change,
                    maximum_plausible_swing=maximum_swing,
                    report_coverage=round(coverage, 3),
                    affected_hypothesis_ids=affected,
                )
            )
        questions.sort(key=lambda item: item.question_priority_score, reverse=True)
        if enforce_core_bound:
            questions = [
                question for question in questions
                if question.question_priority_score >= MATERIALITY_THRESHOLD
            ][:MAX_INTERNAL_QUESTIONS]
        for rank, question in enumerate(questions, 1):
            question.rank = rank
        return questions

    def _expected_change_text(self, category: str, maximum_swing: float) -> str:
        swing = f"{maximum_swing:.0%}"
        descriptions = {
            "strategic_success": "Could reorder the actions by testing them against the confirmed success threshold.",
            "constraints": "Could immediately prune an action that violates a non-negotiable constraint.",
            "financial_capacity": "Could favor a lower-commitment action or rule out an unfunded action.",
            "execution_capacity": "Could shift support between immediate execution, a controlled pilot, and redesign.",
            "risk_tolerance": "Could favor a staged, redesigned, or deferred action when downside exposure is too high.",
            "timing": "Could change whether to proceed now, stage the launch, redesign, or defer.",
        }
        return f"{descriptions.get(category, 'Could change the action ranking.')} Modeled maximum branch swing: {swing}."

    def _detect_contradictions(self, claims: Sequence[ExtractedClaim]) -> List[Contradiction]:
        contradictions: List[Contradiction] = []
        stopwords = {
            "this", "that", "with", "from", "have", "will", "would", "could",
            "their", "there", "were", "been", "into", "about", "which", "while",
        }

        def keywords(text: str) -> set[str]:
            return {
                token
                for token in re.findall(r"[a-z0-9]+", text.lower())
                if len(token) >= 4 and token not in stopwords and not token.isdigit()
            }

        def temporal_scope(text: str) -> set[str]:
            lower = text.lower()
            scope = set(re.findall(r"\b(?:19|20)\d{2}\b", lower))
            scope.update(re.findall(r"\bq[1-4](?:\s+(?:19|20)\d{2})?\b", lower))
            scope.update(
                re.findall(
                    r"\b(?:january|february|march|april|may|june|july|august|"
                    r"september|october|november|december)\s+(?:19|20)\d{2}\b",
                    lower,
                )
            )
            return scope

        def metric_values(text: str) -> set[str]:
            years = set(re.findall(r"\b(?:19|20)\d{2}\b", text))
            values = set(
                re.findall(
                    r"(?<![A-Za-z0-9])(?:[$€£]\s*)?\d+(?:\.\d+)?(?:\s*(?:%|percent|"
                    r"million|billion|thousand|[kmb]))?(?![A-Za-z0-9])",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            return {re.sub(r"\s+", "", value.lower()) for value in values if value.strip() not in years}

        for index, left in enumerate(claims[:60]):
            left_words = keywords(left.text)
            left_numbers = metric_values(left.text)
            left_scope = temporal_scope(left.text)
            for right in claims[index + 1:60]:
                shared = left_words & keywords(right.text)
                if len(shared) < 4:
                    continue
                right_numbers = metric_values(right.text)
                right_scope = temporal_scope(right.text)
                opposite = self._claim_polarity(left.text) * self._claim_polarity(right.text) < 0
                comparable_scope = (
                    left_scope == right_scope
                    if left_scope or right_scope
                    else True
                )
                numeric_conflict = bool(
                    comparable_scope
                    and left_numbers
                    and right_numbers
                    and left_numbers != right_numbers
                )
                if not (opposite or numeric_conflict):
                    continue
                contradiction_id = _stable_id("contradiction", f"{left.claim_id}:{right.claim_id}")
                left.contradicts_claim_ids.append(right.claim_id)
                right.contradicts_claim_ids.append(left.claim_id)
                citations = (left.citations[:2] + right.citations[:2])[:4]
                contradictions.append(
                    Contradiction(
                        contradiction_id=contradiction_id,
                        claim_ids=[left.claim_id, right.claim_id],
                        summary=(
                            "Imported claims use overlapping evidence language but differ in direction or reported values; "
                            "retain both until a decision owner resolves the conflict."
                        ),
                        severity="high" if numeric_conflict else "medium",
                        citations=citations,
                    )
                )
                if len(contradictions) >= 12:
                    return contradictions
        return contradictions

    def _apply_hypothesis_changes(
        self,
        state: V2RunState,
        question: InternalQuestion,
        evidence: InternalEvidence,
    ) -> List[HypothesisChange]:
        factor = 0.75 + (question.question_priority_score / 400)
        confirmed_disqualifier_clauses, _qualified_disqualifier_clauses = (
            self._classify_disqualifier_clauses(evidence.answer)
        )
        confirmed_disqualifier_text = " ".join(confirmed_disqualifier_clauses)
        targeted_ids = self._targeted_hypothesis_ids(state.hypotheses, evidence.answer)
        if evidence.interpretation == "unfavorable" and confirmed_disqualifier_text:
            local_disqualifier_targets = self._targeted_hypothesis_ids(
                state.hypotheses,
                confirmed_disqualifier_text,
            )
            if local_disqualifier_targets:
                targeted_ids = local_disqualifier_targets
        before: Dict[str, Tuple[float, str]] = {
            item.hypothesis_id: (item.support_score, item.status)
            for item in state.hypotheses
        }
        action_interpretations: Dict[str, str] = {}

        for hypothesis in state.hypotheses:
            hypothesis.previous_score = hypothesis.support_score
            if hypothesis.status == "pruned":
                hypothesis.last_change = 0.0
                continue
            action_interpretation = self._action_specific_interpretation(
                hypothesis,
                evidence.answer,
                evidence.interpretation,
            )
            action_interpretations[hypothesis.hypothesis_id] = action_interpretation
            raw_delta = (
                self._interpretation_weight(
                    hypothesis,
                    question.category,
                    action_interpretation,
                    targeted_ids,
                )
                * factor
                * evidence.confidence
            )
            hypothesis.support_score = round(_clamp(hypothesis.support_score + raw_delta), 3)
            hypothesis.last_change = round(hypothesis.support_score - hypothesis.previous_score, 3)

        disqualifier = bool(
            evidence.confidence >= 0.80
            and evidence.interpretation == "unfavorable"
            and confirmed_disqualifier_text
        )
        prune_targets = (
            set(self._targeted_hypothesis_ids(state.hypotheses, confirmed_disqualifier_text))
            if disqualifier
            else set()
        )
        if (
            disqualifier
            and not prune_targets
            and self._has_global_disqualifier_scope(confirmed_disqualifier_text)
        ):
            prune_targets = {
                item.hypothesis_id
                for item in state.hypotheses
                if item.decision_role != "defer"
            }
        elif disqualifier and not prune_targets and question.category in {
            "constraints",
            "financial_capacity",
            "execution_capacity",
        }:
            prune_targets = {
                item.hypothesis_id
                for item in state.hypotheses
                if item.decision_role == "immediate"
            }

        for hypothesis in state.hypotheses:
            if hypothesis.status == "pruned" or hypothesis.hypothesis_id not in prune_targets:
                continue
            hypothesis.status = "pruned"
            hypothesis.pruned_by_evidence_id = evidence.evidence_id
            hypothesis.prune_rule = "explicit_high_confidence_disqualifier"
            hypothesis.prune_reason = (
                "Pruned by high-confidence internal evidence that explicitly disqualified this path."
            )

        ranked = sorted(
            (item for item in state.hypotheses if item.status != "pruned"),
            key=lambda item: item.support_score,
            reverse=True,
        )
        leader = ranked[0] if ranked else None
        for hypothesis in state.hypotheses:
            if hypothesis.status == "pruned":
                continue
            gap = (leader.support_score - hypothesis.support_score) if leader else 0.0
            if hypothesis is leader:
                hypothesis.status = "leading"
            elif hypothesis.last_change > 0.01:
                hypothesis.status = "strengthened"
            elif hypothesis.last_change < -0.01 or gap >= 0.14:
                hypothesis.status = "weakened"
            else:
                hypothesis.status = "active"

        changes: List[HypothesisChange] = []
        for hypothesis in state.hypotheses:
            before_score, before_status = before[hypothesis.hypothesis_id]
            changes.append(
                HypothesisChange(
                    hypothesis_id=hypothesis.hypothesis_id,
                    before_score=before_score,
                    after_score=hypothesis.support_score,
                    delta=round(hypothesis.support_score - before_score, 3),
                    before_status=before_status,
                    after_status=hypothesis.status,
                    explanation=self._hypothesis_change_explanation(
                        hypothesis,
                        question.category,
                        action_interpretations.get(
                            hypothesis.hypothesis_id,
                            evidence.interpretation,
                        ),
                        hypothesis.hypothesis_id in targeted_ids,
                        round(hypothesis.support_score - before_score, 3),
                    ),
                )
            )
        return changes

    def _targeted_hypothesis_ids(
        self,
        hypotheses: Sequence[DecisionHypothesis],
        answer: str,
    ) -> set[str]:
        explicitly_mentioned = self._mentioned_option_indices(
            answer,
            [hypothesis.label for hypothesis in hypotheses],
        )
        if explicitly_mentioned:
            matched = {
                hypothesis.hypothesis_id
                for index, hypothesis in enumerate(hypotheses)
                if index in explicitly_mentioned
            }
        else:
            matched = set()
        matched.update(
            hypothesis.hypothesis_id
            for hypothesis in hypotheses
            if self._action_alias_mentioned(hypothesis, answer)
        )
        if matched:
            return matched
        answer_tokens = self._evidence_terms(answer)
        term_sets = [self._option_terms(item.label) for item in hypotheses]
        term_counts = Counter(term for terms in term_sets for term in terms)
        return {
            hypothesis.hypothesis_id
            for hypothesis, raw_terms in zip(hypotheses, term_sets)
            if (target_terms := {term for term in raw_terms if term_counts[term] == 1} or raw_terms)
            and target_terms <= answer_tokens
        }

    def _action_alias_mentioned(
        self,
        hypothesis: DecisionHypothesis,
        text: str,
    ) -> bool:
        lower = re.sub(r"\s+", " ", self._semantic_text(text).lower())
        patterns = {
            "immediate": r"\b(?:national|full|immediate)\s+(?:rollout|launch|deployment)\b|\broll\s*out nationally\b",
            "staged": r"\b(?:pilot|trial|limited rollout|controlled launch|\d+[- ]stores?)\b",
            "redesign": r"\b(?:redesign|rework|revise|modify|change the (?:benefit|operating) model)\b",
            "defer": r"\b(?:cancel|cancellation|postpone|postponement|defer|deferral|no action)\b",
        }
        pattern = patterns.get(hypothesis.decision_role)
        return bool(pattern and re.search(pattern, lower))

    def _action_specific_interpretation(
        self,
        hypothesis: DecisionHypothesis,
        answer: str,
        default: str,
    ) -> str:
        """Read action-local clauses so mixed answers can move paths differently."""
        coarse_clauses = [
            item.strip()
            for item in re.split(
                r"\b(?:but|however|while|whereas)\b|[;.!?\n]+",
                self._semantic_text(answer).lower(),
            )
            if item.strip()
        ]
        clauses = [
            predicate.strip()
            for clause in coarse_clauses
            for predicate in self._split_constraint_predicate_clauses(clause)
            if predicate.strip()
        ]
        mentioned = [
            clause
            for clause in clauses
            if self._action_alias_mentioned(hypothesis, clause)
            or hypothesis.hypothesis_id
            in self._targeted_hypothesis_ids_by_label([hypothesis], clause)
        ]
        if not mentioned:
            return default
        local = " ".join(mentioned)
        masked_local, cleared_disqualifiers = self._mask_negated_disqualifiers(local)
        negative = bool(
            re.search(
                r"\b(?:not approved|unapproved|(?:will not|won't|does not|doesn't|cannot|can't) approve|"
                r"not permitted|not allowed|not available|unavailable|cannot|can't|"
                r"insufficient|not sufficient|no (?:approved )?(?:budget|funding|capacity)|"
                r"blocked|prohibited|disqualified|illegal)\b",
                masked_local,
            )
        )
        positive = cleared_disqualifiers > 0 or bool(
            re.search(
                r"\b(?:approved|permitted|allowed|available|sufficient|committed|cleared|ready|can support|"
                r"no (?:legal |policy |hard )?(?:blocker|constraint)s?)\b",
                masked_local,
            )
        )
        conditional = bool(
            re.search(
                r"\b(?:permitted only if|allowed only if|subject to|until|provided that|"
                r"approval (?:requires|depends on))\b",
                local,
            )
        )
        if conditional and positive and not negative:
            return "mixed"
        if positive and not negative:
            return "favorable"
        if negative and not positive:
            return "unfavorable"
        return default

    def _targeted_hypothesis_ids_by_label(
        self,
        hypotheses: Sequence[DecisionHypothesis],
        answer: str,
    ) -> set[str]:
        indices = self._mentioned_option_indices(
            answer,
            [hypothesis.label for hypothesis in hypotheses],
        )
        return {
            hypothesis.hypothesis_id
            for index, hypothesis in enumerate(hypotheses)
            if index in indices
        }

    def _interpretation_weight(
        self,
        hypothesis: DecisionHypothesis,
        category: str,
        interpretation: str,
        targeted_ids: set[str],
    ) -> float:
        targeted = hypothesis.hypothesis_id in targeted_ids
        another_targeted = bool(targeted_ids) and not targeted
        role = hypothesis.decision_role
        category_weights = {
            "strategic_success": {
                "favorable": {"immediate": 0.10, "staged": 0.055, "redesign": 0.015, "alternative": 0.04, "defer": -0.08},
                "unfavorable": {"immediate": -0.10, "staged": 0.035, "redesign": 0.075, "alternative": -0.035, "defer": 0.09},
                "mixed": {"immediate": -0.04, "staged": 0.085, "redesign": 0.06, "alternative": 0.0, "defer": 0.02},
            },
            "constraints": {
                "favorable": {"immediate": 0.075, "staged": 0.045, "redesign": -0.01, "alternative": 0.035, "defer": -0.065},
                "unfavorable": {"immediate": -0.13, "staged": -0.035, "redesign": 0.09, "alternative": -0.07, "defer": 0.12},
                "mixed": {"immediate": -0.05, "staged": 0.075, "redesign": 0.085, "alternative": -0.015, "defer": 0.035},
            },
            "financial_capacity": {
                "favorable": {"immediate": 0.11, "staged": 0.065, "redesign": 0.015, "alternative": 0.045, "defer": -0.09},
                "unfavorable": {"immediate": -0.13, "staged": 0.045, "redesign": 0.075, "alternative": -0.065, "defer": 0.12},
                "mixed": {"immediate": -0.055, "staged": 0.09, "redesign": 0.065, "alternative": -0.01, "defer": 0.025},
            },
            "execution_capacity": {
                "favorable": {"immediate": 0.10, "staged": 0.06, "redesign": -0.015, "alternative": 0.04, "defer": -0.08},
                "unfavorable": {"immediate": -0.12, "staged": 0.055, "redesign": 0.09, "alternative": -0.055, "defer": 0.10},
                "mixed": {"immediate": -0.05, "staged": 0.09, "redesign": 0.075, "alternative": -0.005, "defer": 0.025},
            },
            "risk_tolerance": {
                "favorable": {"immediate": 0.085, "staged": 0.055, "redesign": 0.0, "alternative": 0.03, "defer": -0.07},
                "unfavorable": {"immediate": -0.11, "staged": 0.06, "redesign": 0.085, "alternative": -0.045, "defer": 0.105},
                "mixed": {"immediate": -0.055, "staged": 0.09, "redesign": 0.075, "alternative": -0.01, "defer": 0.035},
            },
            "timing": {
                "favorable": {"immediate": 0.10, "staged": 0.045, "redesign": -0.03, "alternative": 0.04, "defer": -0.085},
                "unfavorable": {"immediate": -0.12, "staged": 0.065, "redesign": 0.075, "alternative": -0.05, "defer": 0.10},
                "mixed": {"immediate": -0.045, "staged": 0.09, "redesign": 0.06, "alternative": -0.005, "defer": 0.025},
            },
        }
        category_map = category_weights.get(category, {})
        interpretation_map = category_map.get(interpretation, {})
        if targeted:
            return {
                "favorable": 0.14,
                "unfavorable": -0.13,
                "mixed": 0.055,
            }.get(interpretation, 0.0)
        if another_targeted:
            role_weight = interpretation_map.get(role)
            if role_weight is not None:
                return role_weight * 0.55
            return {
                "favorable": -0.04,
                "unfavorable": 0.025,
                "mixed": -0.015,
            }.get(interpretation, 0.0)
        if role in interpretation_map:
            return interpretation_map[role]
        if interpretation == "favorable":
            return {"immediate": 0.10, "staged": 0.045, "redesign": 0.0, "defer": -0.08}.get(role, 0.035)
        if interpretation == "unfavorable":
            return {"immediate": -0.11, "staged": 0.045, "redesign": 0.08, "defer": 0.11}.get(role, -0.04)
        if interpretation == "mixed":
            return {"immediate": -0.04, "staged": 0.085, "redesign": 0.065, "defer": 0.025}.get(role, 0.0)
        return 0.0

    def _hypothesis_change_explanation(
        self,
        hypothesis: DecisionHypothesis,
        category: str,
        interpretation: str,
        explicitly_targeted: bool,
        delta: float,
    ) -> str:
        direction = "strengthened" if delta > 0.001 else "weakened" if delta < -0.001 else "did not materially move"
        if explicitly_targeted:
            rationale = "The internal answer explicitly referenced this action."
        else:
            category_rationales = {
                "strategic_success": {
                    "immediate": "A verified success threshold tests whether full commitment is justified.",
                    "staged": "A staged action can validate the success threshold before scale.",
                    "redesign": "A redesign can align the offer more closely with the success threshold.",
                    "defer": "Deferral becomes less attractive when the target is achievable and more attractive when it is not.",
                },
                "constraints": {
                    "immediate": "Hard constraints directly affect whether immediate execution is feasible.",
                    "staged": "A controlled pilot can contain constraints while preserving learning.",
                    "redesign": "Redesign can remove operational or policy constraints before launch.",
                    "defer": "Deferral protects against unresolved hard constraints.",
                },
                "financial_capacity": {
                    "immediate": "Approved budget and downside limits determine whether a high-commitment action is feasible.",
                    "staged": "A smaller pilot requires less committed capital and preserves optionality.",
                    "redesign": "Redesign may reduce cost before capital is committed.",
                    "defer": "Deferral protects capital when funding or payback limits are not met.",
                },
                "execution_capacity": {
                    "immediate": "Named ownership and available capacity are prerequisites for immediate execution.",
                    "staged": "A limited pilot reduces the operating load while testing delivery capacity.",
                    "redesign": "Redesign can remove workload and throughput bottlenecks.",
                    "defer": "Deferral avoids launching without sufficient operating capacity.",
                },
                "risk_tolerance": {
                    "immediate": "A high-commitment action consumes more of the approved downside envelope.",
                    "staged": "A staged action limits exposure while preserving learning.",
                    "redesign": "Redesign can lower stakeholder and operating risk before launch.",
                    "defer": "Deferral best protects a low risk tolerance.",
                },
                "timing": {
                    "immediate": "The deadline determines whether immediate action captures or misses the opportunity.",
                    "staged": "A pilot can begin inside the window while later commitments remain gated.",
                    "redesign": "Redesign consumes time but may be necessary before launch.",
                    "defer": "Deferral is safer when dependencies make the current timing infeasible.",
                },
            }
            rationale = category_rationales.get(category, {}).get(
                hypothesis.decision_role,
                "This internal fact changes the feasibility or attractiveness of the action.",
            )
        return (
            f"The {category.replace('_', ' ')} answer was interpreted as {interpretation}. "
            f"{rationale} Therefore this action {direction}; relative support remains a heuristic, not a probability."
        )

    def _normalize_explicit_interpretation(self, explicit: Optional[str]) -> Optional[str]:
        if explicit is None or not str(explicit).strip():
            return None
        normalized = str(explicit).strip().lower().replace("-", "_")
        aliases = {
            "supports": "favorable",
            "support": "favorable",
            "positive": "favorable",
            "opposes": "unfavorable",
            "oppose": "unfavorable",
            "negative": "unfavorable",
            "uncertain": "uncertain",
            "unknown": "uncertain",
            "mixed": "mixed",
            "favorable": "favorable",
            "unfavorable": "unfavorable",
        }
        if normalized not in aliases:
            raise ValueError("interpretation must be favorable, unfavorable, mixed, or uncertain")
        return aliases[normalized]

    def _interpret_answer(self, answer: str, category: Optional[str] = None) -> Tuple[str, str]:
        lower = re.sub(r"\s+", " ", answer.lower()).strip()
        if lower in {"yes", "no", "y", "n"} or re.search(
            r"\b(?:unknown|not known|do not know|don't know|cannot verify|could not verify|tbd|unsure)\b",
            lower,
        ):
            return "uncertain", "The answer does not contain a verifiable decision fact."

        if re.search(
            r"\b(?:no|without)\b.{0,35}\b(?:blocker|constraint)s?\b.{0,70}"
            r"\b(?:not|never)\b.{0,25}\b(?:reviewed|verified|confirmed|assessed)\b",
            lower,
        ):
            return "uncertain", "The claimed absence of a blocker has not been reviewed or verified."

        capacity_text = self._mask_false_zero_capacity_phrases(lower, category)
        zero_quantity = r"(?:0(?:\.0+)?|zero|none)"
        if category == "financial_capacity" and (
            re.search(r"(?:[$€£]\s*0(?:\.0+)?\b)", capacity_text)
            or re.search(
                rf"\b(?:budget|funding|cash|liquidity|runway)\b.{{0,35}}\b{zero_quantity}\b|"
                rf"\b{zero_quantity}\b.{{0,20}}\b(?:budget|funding|cash|liquidity|runway)\b",
                capacity_text,
            )
        ):
            return "unfavorable", "The supplied financial capacity is explicitly zero."
        if category == "execution_capacity" and re.search(
            rf"\b(?:staff|people|fte|headcount|engineers?|team members?|resources?|capacity)\b"
            rf".{{0,35}}\b{zero_quantity}\b|"
            rf"\b{zero_quantity}\b.{{0,20}}"
            rf"\b(?:staff|people|fte|headcount|engineers?|team members?|resources?|capacity)\b",
            capacity_text,
        ):
            return "unfavorable", "The supplied execution capacity is explicitly zero."

        constraint_text, cleared_count = self._mask_negated_disqualifiers(capacity_text)
        confirmed_disqualifiers, qualified_disqualifiers = self._classify_disqualifier_clauses(
            lower
        )
        if qualified_disqualifiers and not confirmed_disqualifiers:
            if any(
                self._has_epistemic_disqualifier_qualifier(clause)
                for clause in qualified_disqualifiers
            ):
                return "uncertain", "The possible blocker has not been confirmed as a current fact."
            return "mixed", "The possible blocker is modal, conditional, or temporary rather than final."
        if confirmed_disqualifiers:
            return "unfavorable", "The answer explicitly identifies a confirmed disqualifying constraint."

        conditional_approval = bool(
            re.search(
                r"\b(?:will not|won't|does not|doesn't|cannot|can't)\s+approve\b|"
                r"\b(?:not permitted|not allowed|permitted|allowed)(?:\s+only\s+if)?\b",
                lower,
            )
            and re.search(
                r"\b(?:until|unless|only if|subject to|requires?|after|before)\b",
                lower,
            )
        )
        if conditional_approval:
            return "mixed", "The answer supplies a binding but conditional approval boundary."
        if re.search(
            r"\b(?:will not|won't|does not|doesn't|cannot|can't)\s+approve\b|"
            r"\b(?:not permitted|not allowed)\b",
            lower,
        ):
            return "unfavorable", "The answer explicitly identifies a current approval prohibition."

        # Evaluate each contrastive clause before accepting a broad "no blocker"
        # statement. A concrete disqualifier in any clause dominates the absence
        # of a different constraint.
        for clause in re.split(r"\b(?:but|however|although|yet)\b|[;]", constraint_text):
            if re.search(
                r"\b(?:blocker|constraint)\b.{0,60}\b(?:prohibit(?:s|ed)?|block(?:s|ed)?|"
                r"disqualif(?:y|ies|ied)|cannot proceed|illegal)\b|"
                r"\b(?:is|are|was|were|remains?)\s+(?:prohibited|blocked|illegal|disqualified)\b",
                clause,
            ):
                return "unfavorable", "The answer explicitly identifies a disqualifying constraint."

        if cleared_count and not re.search(
            r"\b(?:insufficient|shortfall|blocked|prohibited|illegal|disqualif(?:y|ies|ied))\b",
            constraint_text,
        ):
            return "favorable", "The answer explicitly rules out a feasibility shortfall or prohibition."

        if re.search(
            r"\b(?:no|without)\b.{0,45}\b(?:non-negotiable )?(?:legal )?(?:blocker|blockers|constraint|constraints)\b",
            lower,
        ) or "nothing disqualifies" in lower:
            return "favorable", "The answer explicitly states that no hard constraint disqualifies the path."

        if re.search(
            r"\b(?:not sufficient|insufficient|not approved|unapproved|not available|unavailable|"
            r"cannot proceed|no budget(?: is)? approved|no approved budget|no execution owner|no capacity|shortfall)\b",
            constraint_text,
        ):
            return "unfavorable", "The answer explicitly identifies a feasibility shortfall or blocker."

        if re.search(
            r"\b(?:blocker|blocked|prohibited|illegal|disqualif(?:y|ies|ied))\b",
            constraint_text,
        ):
            return "unfavorable", "The answer explicitly identifies a disqualifying constraint."

        if (
            re.search(r"\b(?:approved|available|funded|committed|confirmed|ready)\b", lower)
            and re.search(r"\b(?:sufficient|capacity|budget|funding|owner|threshold|within)\b", lower)
        ):
            return "favorable", "The answer confirms an approved and sufficient internal condition."

        if category == "strategic_success" and (
            re.search(
                r"\b(?:threshold|target|outcome|metric|success|conversion|transactions?|"
                r"retention|churn|revenue|margin|profit|contribution|wait|service time)\b",
                lower,
            )
            and re.search(r"\d", lower)
        ):
            return "mixed", "A measurable success threshold was supplied without uniformly favoring every path."
        if category == "execution_capacity" and (
            re.search(r"\d", lower)
            and re.search(
                r"\b(?:capacity|staff|headcount|fte|people|team|owner|stores?|locations?|"
                r"sites?|labor hours?|resources?)\b",
                lower,
            )
        ):
            return "mixed", "A measurable execution boundary was supplied and must be applied by action."
        if category in {"timing", "risk_tolerance"} and (
            re.search(r"\d", lower)
            or re.search(r"\b(?:deadline|week|month|maximum|limit|cap|acceptable)\b", lower)
        ):
            return "mixed", "A usable boundary was supplied, but its effect depends on the decision path."

        tokens = set(re.findall(r"[a-z']+", lower))
        cautious = tokens & self.CAUTIOUS_TERMS
        positive = tokens & {"sufficient", "approved", "available", "funded", "ready", "confirmed"}
        negative = tokens & {"insufficient", "blocked", "unavailable", "shortfall", "unapproved"}
        if cautious or (positive and negative):
            return "mixed", "The answer contains conditional or directionally mixed evidence."
        if positive:
            return "favorable", "The answer states a concrete favorable internal condition."
        if negative:
            return "unfavorable", "The answer states a concrete unfavorable internal condition."
        return "uncertain", "The answer is not specific enough to move a decision branch safely."

    def _mask_false_zero_capacity_phrases(self, text: str, category: Optional[str]) -> str:
        """Mask explicit nonzero and double-negative capacity phrases before zero checks."""
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        normalized = re.sub(
            r"\b(?:not|above|over|greater than|more than|in excess of)\s+"
            r"(?:[$€£]\s*)?(?:0(?:\.0+)?|zero)\b|\bnon[- ]?zero\b",
            " positive quantity ",
            normalized,
        )
        nouns = {
            "financial_capacity": r"budget|funding|cash|liquidity|runway",
            "execution_capacity": (
                r"staff|people|fte|headcount|engineers?|team members?|resources?|capacity"
            ),
        }.get(category)
        if nouns:
            normalized = re.sub(
                rf"\bnone of\b.{{0,45}}\b(?:{nouns})\b.{{0,35}}"
                r"\b(?:is|are|was|were)?\s*(?:unavailable|unapproved|unfunded|"
                r"uncommitted|unused|blocked|not\s+(?:available|approved|funded|committed))\b",
                " available sufficient capacity ",
                normalized,
            )
        return normalized

    def _mask_negated_disqualifiers(self, text: str) -> Tuple[str, int]:
        """Mask explicit negations so they cannot become blockers downstream."""
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        masked_count = 0
        for pattern in (
            r"\bno (?:material )?(?:capacity )?shortfall\b",
            r"\bneither\b.{0,100}\bnor\b.{0,100}"
            r"\b(?:is|are|was|were)\s+(?:currently\s+)?"
            r"(?:prohibited|blocked|disqualified|illegal)\b",
            r"\b(?:is|are|was|were)\s+by no means\s+"
            r"(?:prohibited|blocked|disqualified|illegal)\b",
            r"\b(?:the\s+)?(?:prohibition|ban|blocker|restriction)\s+"
            r"(?:has\s+been|was|is)\s+(?:lifted|removed|rescinded|waived|cleared|resolved)\b",
            r"\b(?:is|are|was|were)\s+now\s+(?:cleared|allowed|approved)\b",
            r"\b(?:it\s+(?:is|was)\s+)?(?:false|untrue|incorrect)\s+that\b.{0,80}?"
            r"\b(?:is|are|was|were)\s+(?:currently\s+)?"
            r"(?:prohibited|blocked|disqualified|illegal)\b",
            r"\b(?:is|are|was|were)?\s*"
            r"(?:not(?:\s+(?:currently|legally|presently|now|yet|actually|explicitly))?|no longer)\s+"
            r"(?:prohibited|blocked|disqualified|illegal)\b",
            r"\b(?:no|without(?: any)?)\s+"
            r"(?:(?:non[- ]negotiable|material|legal|security|policy|contractual|hard)\s+){0,3}"
            r"(?:blockers?|constraints?)"
            r"(?:\s+that\s+disqualif(?:y|ies|ied))?\b",
        ):
            normalized, count = re.subn(pattern, " cleared ", normalized)
            masked_count += count
        return normalized, masked_count

    def _classify_disqualifier_clauses(self, text: str) -> Tuple[List[str], List[str]]:
        """Separate confirmed blockers from modal, conditional, or unverified ones."""
        lower = re.sub(r"\s+", " ", text.lower()).strip()
        clauses = re.split(
            r"\b(?:but|however|although|yet|whereas|while)\b|[;.!?\n]+",
            lower,
        )
        confirmed: List[str] = []
        qualified: List[str] = []
        for clause in clauses:
            for predicate_clause in self._split_constraint_predicate_clauses(clause):
                masked_clause, _cleared_count = self._mask_negated_disqualifiers(
                    predicate_clause
                )
                if not self._contains_prune_disqualifier(masked_clause):
                    continue
                if self._has_qualified_disqualifier_context(predicate_clause):
                    qualified.append(predicate_clause)
                else:
                    confirmed.append(masked_clause)
        return confirmed, qualified

    def _split_constraint_predicate_clauses(self, clause: str) -> List[str]:
        """Split coordinated independent predicates without breaking option lists."""
        fragments = [item.strip() for item in re.split(r"\s*,\s*|\s+and\s+", clause) if item.strip()]
        if len(fragments) < 2:
            return fragments or [clause]
        result: List[str] = []
        current = fragments[0]
        for fragment in fragments[1:]:
            current_complete = self._has_constraint_predicate(current)
            fragment_complete = self._has_constraint_predicate(fragment)
            has_disqualifier = self._contains_prune_disqualifier(current) or (
                self._contains_prune_disqualifier(fragment)
            )
            if current_complete and fragment_complete and has_disqualifier:
                result.append(current)
                current = fragment
            else:
                current = f"{current} and {fragment}"
        result.append(current)
        return result

    def _has_constraint_predicate(self, text: str) -> bool:
        return bool(
            re.search(
                r"\b(?:is|are|was|were|has|have|had|may|might|could|can|cannot|"
                r"approved|cleared|allowed|prohibited|blocked|illegal|disqualified|"
                r"passes?|passed|fails?|failed|remains?)\b",
                text,
            )
        )

    def _contains_prune_disqualifier(self, text: str) -> bool:
        return bool(
            re.search(
                r"\b(?:disqualif(?:y|ies|ied)|cannot proceed|can't proceed|unable to proceed|"
                r"illegal|prohibit(?:s|ed)?|"
                r"block(?:s|ed)|hard blocker|"
                r"no approved budget|no budget is approved|no execution owner|no capacity)\b|"
                r"\b(?:no\s+(?:option|path|alternative)s?|none of (?:the )?"
                r"(?:options|paths|alternatives)|neither\b.{0,70}\bnor\b.{0,70})"
                r"\s+can proceed\b",
                text,
            )
        )

    def _has_global_disqualifier_scope(self, text: str) -> bool:
        return bool(
            re.search(
                r"\b(?:all|every)\b.{0,55}\b(?:deployments?|implementations?|options?|"
                r"paths?|alternatives?|products?|services?|cloud)\b|"
                r"\b(?:policy\s+)?prohibit(?:s|ed)?\b.{0,35}\b(?:cloud\s+)?deployments?\b|"
                r"\b(?:cloud\s+)?deployments?\b.{0,35}\b(?:cannot|can't|unable to)\s+proceed\b|"
                r"\bno\b.{0,45}\b(?:option|path|alternative|deployment|implementation)s?\b"
                r".{0,30}\b(?:can|may|is able to)\s+proceed\b|"
                r"\bnone of (?:the )?(?:options|paths|alternatives)\s+can proceed\b|"
                r"\ball (?:options|paths|alternatives) are unable to proceed\b|"
                r"\b(?:no approved budget|no budget is approved|no execution owner|no capacity)\b|"
                r"\b(?:deployment|implementation)s?\s+(?:across|for)\s+all\b",
                text,
            )
        )

    def _has_epistemic_disqualifier_qualifier(self, clause: str) -> bool:
        return bool(
            re.search(
                r"\b(?:no evidence|without evidence|not (?:yet )?(?:confirmed|verified|"
                r"established|determined|known)|unconfirmed|unverified|unclear|unknown|"
                r"uncertain|whether|suspected|alleged)\b",
                clause,
            )
        )

    def _has_qualified_disqualifier_context(self, clause: str) -> bool:
        if self._has_epistemic_disqualifier_qualifier(clause):
            return True
        current_blocker = bool(
            re.search(
                r"\b(?:currently|now|today|still|remains?|continu(?:e|es) to)\b.{0,30}"
                r"\b(?:prohibited|blocked|illegal|disqualified)\b|"
                r"\b(?:prohibited|blocked|illegal|disqualified)\b.{0,20}"
                r"\b(?:currently|now|today|still|remains?)\b",
                clause,
            )
        )
        historical_blocker = bool(
            re.search(
                r"\b(?:previously|formerly|historically|last (?:year|month|quarter|week)|"
                r"during (?:the )?(?:pilot|trial|test)|at the time)\b|"
                r"\b(?:was|were)\s+(?:prohibited|blocked|illegal|disqualified)\b",
                clause,
            )
        )
        if historical_blocker and not current_blocker:
            return True
        return bool(
            re.search(
                r"\b(?:may|might|could|possibly|potentially|perhaps|maybe|appears? to|"
                r"seems? to|can be|at risk of|if|unless|until|provided that|depending on|"
                r"subject to|pending|awaiting|temporar(?:y|ily)|provisionally|interim)\b",
                clause,
            )
        )

    def _answer_relevance(self, answer: str, category: str) -> Tuple[bool, str]:
        lower = re.sub(r"\s+", " ", answer.lower())
        has_number = bool(re.search(r"\d", lower))
        if category == "strategic_success":
            relevant = bool(
                re.search(
                    r"\b(?:metric|outcome|success|threshold|target|minimum|goal|"
                    r"conversion|churn|retention|revenue|growth|margin|satisfaction|"
                    r"service time|pickup time|throughput)\b",
                    lower,
                )
                and (
                    has_number
                    or re.search(
                        r"\b(?:at least|no less than|no more than|must (?:exceed|improve|"
                        r"remain|stay)|minimum acceptable|above|below)\b",
                        lower,
                    )
                )
            )
        elif category == "constraints":
            relevant = bool(
                re.search(
                    r"\b(?:blockers?|constraints?|prohibit(?:ed|s)?|disqualif(?:y|ies|ied)|illegal|"
                    r"nothing disqualifies|contractual restriction|conditional approval)\b|"
                    r"\b(?:cannot|can't|unable to|can)\s+proceed\b|"
                    r"\b(?:will not|won't|does not|doesn't|cannot|can't)\s+approve\b|"
                    r"\b(?:not permitted|not allowed|permitted only if|allowed only if|"
                    r"permitted (?:after|if|subject to)|allowed (?:after|if|subject to)|"
                    r"approval (?:requires|depends on)|subject to (?:approval|review|consultation))\b",
                    lower,
                )
            )
        elif category == "financial_capacity":
            relevant = bool(
                re.search(
                    r"\b(?:budget|funding|cash|liquidity|runway|payback|cost|spend|loss|"
                    r"tranche|contribution|financial limit)\b",
                    lower,
                )
                and (
                    has_number
                    or re.search(
                        r"\b(?:approved|unapproved|sufficient|insufficient|available|unavailable|"
                        r"shortfall|limit|maximum|within)\b",
                        lower,
                    )
                )
            )
        elif category == "execution_capacity":
            relevant = bool(
                re.search(
                    r"\b(?:execution|operating|implementation|delivery|team|staff|resource|capacity)\b",
                    lower,
                )
                and re.search(
                    r"\b(?:owner|owns?|named|assigned|committed|available|unavailable|sufficient|"
                    r"insufficient|capacity|headcount|capped?|stores?|locations?|labor hours?)\b",
                    lower,
                )
            )
        elif category == "risk_tolerance":
            relevant = bool(
                re.search(r"\b(?:risk|downside|loss|exposure|tolerance|regret)\b", lower)
                and (
                    has_number
                    or re.search(r"\b(?:maximum|limit|cap|acceptable|unacceptable|no more than)\b", lower)
                )
            )
        elif category == "timing":
            relevant = bool(
                re.search(r"\b(?:deadline|date|start|timing|window|dependency|dependencies|earliest)\b", lower)
                and (
                    has_number
                    or re.search(r"\b(?:cleared|blocked|ready|before|after|by|earliest)\b", lower)
                )
            )
        else:
            relevant = False
        if relevant:
            return True, f"The answer fills the required {category.replace('_', ' ')} decision slot."
        return (
            False,
            f"The answer does not fill the required {category.replace('_', ' ')} decision slot.",
        )

    def _normalize_interpretation(self, explicit: Optional[str], answer: str) -> str:
        inferred, _rationale = self._interpret_answer(answer)
        normalized_explicit = self._normalize_explicit_interpretation(explicit)
        if normalized_explicit and normalized_explicit != inferred:
            raise ValueError("Provided interpretation conflicts with the answer.")
        return inferred

    def _claim_polarity(self, text: str) -> int:
        working = re.sub(r"\s+", " ", self._semantic_text(text).lower())
        working = re.sub(
            r"\b(did|does|do|is|are|was|were|has|have|had)n['’]t\b",
            r"\1 not",
            working,
        )
        working = re.sub(r"[-‐-―]", " ", working)
        epistemic_patterns = (
            r"\b(?:no evidence(?:\s+that)?|did not find (?:any\s+)?evidence(?:\s+that)?|"
            r"could not confirm(?:\s+(?:that|whether))?|unclear whether|uncertain whether|"
            r"unconfirmed(?:\s+(?:that|whether))?)\b.*?"
            r"(?=\b(?:but|however|while|whereas)\b|[.;]|$)",
            r"\b(?:may|might|could)\s+not\s+"
            r"(?:increase|grow|worsen|improve|strengthen|reduce|lower|decrease|eliminate|"
            r"avoid|resolve)\w*\b.{0,40}"
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall|growth|revenue|demand|"
            r"benefit|reliability|retention|capacity|readiness|gain)s?\b",
        )
        for pattern in epistemic_patterns:
            working = re.sub(pattern, " ", working)
        # Negated or double-negated adverse outcomes are not reliable evidence of
        # either direction. Remove only those spans, preserving other claims in
        # the same sentence for scoring.
        neutralized_adverse_patterns = (
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b.{0,18}"
            r"\b(?:did not|does not|do not|was not|were not|is not|are not|never)\b.{0,18}"
            r"\b(?:increase|increased|grow|grew|worsen|worsened|high|severe|material)\b",
            r"\b(?:did not|does not|do not|has not|have not|had not|never|failed to)\b.{0,20}"
            r"\b(?:increase|grow|worsen|suffer|incur|experience|sustain|reduce|lower|"
            r"decrease|eliminate|avoid|resolve)\w*\b.{0,22}"
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?\b",
            r"\b(?:had|has|have|reported|showed|saw)?\s*no\s+(?:material\s+)?"
            r"(?:increase|rise|growth|worsening|reduction|decrease)\s+in\s+"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b",
            r"\b(?:avoid(?:ed|s)?|eliminat(?:e|ed|es)|reduc(?:e|ed|es)|resolv(?:e|ed|es))\b"
            r".{0,12}\b(?:no|none|not any)\b.{0,12}"
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall|blocker)s?\b",
            r"\b(?:has|have|had|there is|there are)?\s*no\s+"
            r"(?:(?:material|severe|high|significant|meaningful|implementation|migration|"
            r"financial|legal|security|operating)\s+){0,4}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?"
            r"(?:\s+(?:or|and)\s+(?:(?:material|severe|high|significant|implementation|"
            r"migration|financial|legal|security|operating)\s+){0,4}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?)*\b",
            r"\b(?:free of|without(?: any)?|absent)\s+"
            r"(?:(?:material|severe|high|significant|meaningful|implementation|migration|"
            r"financial|legal|security|operating)\s+){0,4}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?"
            r"(?:\s+(?:or|and)\s+(?:(?:material|severe|high|significant|implementation|"
            r"migration|financial|legal|security|operating)\s+){0,4}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?)*\b",
            r"\b(?:did not|does not|do not|has not|have not|had not|never)\s+"
            r"(?:have|pose|carry|face|show|present)\s+(?:a\s+|any\s+)?"
            r"(?:(?:material|severe|high|significant|meaningful|implementation|migration|"
            r"financial|legal|security|operating)\s+){0,4}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?\b",
            r"\b(?:is not|are not|was not|were not|not)\s+(?:a\s+|an\s+)?"
            r"(?:high|severe|material|significant|meaningful)\s+"
            r"(?:(?:implementation|migration|financial|legal|security|operating)\s+){0,3}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall|blocker)s?(?:\s+option)?\b",
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b.{0,18}"
            r"\b(?:is|are|was|were|remained|remains|stayed)?\s*"
            r"(?:manageable|flat|stable|unchanged)\b",
        )
        for pattern in neutralized_adverse_patterns:
            matches = list(re.finditer(pattern, working))
            for match in reversed(matches):
                working = (
                    working[: match.start()]
                    + " " * (match.end() - match.start())
                    + working[match.end() :]
                )
        positive_patterns = (
            r"\b(?:low|minimal)\s+"
            r"(?:(?:implementation|migration|financial|legal|security|operating)\s+){0,3}"
            r"(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b",
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b.{0,12}"
            r"\b(?:is|are|was|were|remained|remains|stayed)?\s*(?:low|minimal)\b",
            r"\b(?:reduc(?:e|ed|es)|lower(?:ed|s)?|decreas(?:e|ed|es)|eliminat(?:e|ed|es)|avoid(?:ed|s)?|resolv(?:e|ed|es))\b.{0,35}\b(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?\b",
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall|cash burn|burn|blocker)s?\b.{0,25}\b(?:fell|declined|reduced|lowered|decreased|eliminated|resolved)\b",
            r"\b(?:increas(?:e|ed|es)|improv(?:e|ed|es)|strengthen(?:ed|s)?|exceed(?:ed|s)?)\b.{0,35}\b(?:growth|revenue|demand|benefit|reliability|retention|capacity|readiness|gain)s?\b",
            r"\b(?:growth|revenue|demand|benefit|reliability|retention|capacity|readiness|gain)s?\b.{0,25}\b(?:grew|increased|improved|strong|strengthened|exceeded)\b",
            r"\b(?:approved|funded|committed|confirmed)\b.{0,25}\b(?:budget|funding|capacity|support|owner|plan)\b",
        )
        negative_patterns = (
            r"\b(?:did not|does not|do not|not|never|failed to)\b.{0,30}\b(?:improve|increase|grow|benefit|gain|approve|fund|commit|confirm|support)\w*\b",
            r"\bno\b.{0,30}\b(?:growth|benefit|gain|funding|budget|capacity|support|owner|approval)\b",
            r"\b(?:increas(?:e|ed|es)|worsen(?:ed|s)?|higher|severe)\b.{0,35}\b(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b",
            r"\b(?:risk|loss|debt|delay|cost|exposure|shortfall)s?\b.{0,25}\b(?:grew|increased|worsened|high|severe)\b",
            r"\b(?:declin(?:e|ed|es)|decreas(?:e|ed|es)|lower)\b.{0,35}\b(?:growth|revenue|demand|benefit|reliability|retention|capacity)\b",
            r"\b(?:growth|revenue|demand|benefit|reliability|retention|capacity)\b.{0,25}\b(?:fell|declined|decreased|weak|lower)\b",
        )

        positive = 0
        negative = 0
        for pattern in negative_patterns:
            matches = list(re.finditer(pattern, working))
            negative += len(matches)
            for match in reversed(matches):
                working = working[: match.start()] + " " * (match.end() - match.start()) + working[match.end() :]
        for pattern in positive_patterns:
            matches = list(re.finditer(pattern, working))
            positive += len(matches)
            for match in reversed(matches):
                working = working[: match.start()] + " " * (match.end() - match.start()) + working[match.end() :]

        remaining_tokens = set(re.findall(r"[a-z]+", working))
        positive += len(
            remaining_tokens
            & {"growth", "improved", "strong", "opportunity", "approved", "gain", "benefit", "ready"}
        )
        negative += len(
            remaining_tokens
            & {"decline", "risk", "weak", "loss", "delay", "rejected", "shortfall", "debt"}
        )
        return 1 if positive > negative else (-1 if negative > positive else 0)

    def _semantic_text(self, text: str) -> str:
        """Remove citation destinations before semantic scoring or option matching."""
        semantic = re.sub(
            r"\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)",
            r"\1",
            text or "",
        )
        semantic = re.sub(r"<https?://[^>]+>", " ", semantic, flags=re.IGNORECASE)
        return re.sub(r"https?://[^\s)\]>]+", " ", semantic, flags=re.IGNORECASE)

    def _update_assumption_statuses(
        self,
        state: V2RunState,
        category: str,
        interpretation: str,
    ) -> None:
        statuses = {
            "favorable": "validated",
            "unfavorable": "challenged",
            "mixed": "partially_validated",
            "uncertain": "uncertain",
        }
        for assumption in state.assumptions:
            if assumption.category == category:
                assumption.status = statuses[interpretation]

    def _refresh_internal_questions(self, state: V2RunState) -> None:
        bounded_previous = sorted(
            state.internal_questions,
            key=lambda item: (
                item.rank if item.rank > 0 else 999,
                -item.question_priority_score,
            ),
        )[:MAX_INTERNAL_QUESTIONS]
        previous = {item.question_id: item for item in bounded_previous}
        generated_by_category = {
            item.category: item
            for item in self._build_internal_questions(state, enforce_core_bound=False)
        }
        refreshed = []
        for old in previous.values():
            generated = generated_by_category.get(old.category)
            if not generated:
                continue
            generated.question_id = old.question_id
            if old.origin == "user_proposed":
                generated.question = old.question
                generated.owner_hint = old.owner_hint
                generated.origin = old.origin
            refreshed.append(generated)
        refreshed.sort(key=lambda item: item.question_priority_score, reverse=True)
        for question in refreshed:
            old = previous.get(question.question_id)
            if old and old.status == "answered":
                question.status = "answered"
                question.answer_id = old.answer_id
            else:
                question.status = "pending"
        for rank, question in enumerate(refreshed, 1):
            question.rank = rank
        state.internal_questions = refreshed
        self._activate_next_question(state.internal_questions)

    def _activate_next_question(self, questions: Iterable[InternalQuestion]) -> None:
        question_list = list(questions)
        for question in question_list:
            if question.status == "requested":
                question.status = "pending"
        candidates = [question for question in question_list if question.status == "pending"]
        if candidates:
            max(candidates, key=lambda item: item.question_priority_score).status = "requested"

    def _graph_change_summary(self, changes: Sequence[HypothesisChange]) -> str:
        strengthened = [item.hypothesis_id for item in changes if item.delta > 0.001]
        weakened = [item.hypothesis_id for item in changes if item.delta < -0.001]
        pruned = [item.hypothesis_id for item in changes if item.after_status == "pruned"]
        return (
            f"Decision graph revision: strengthened {', '.join(strengthened) or 'none'}; "
            f"weakened {', '.join(weakened) or 'none'}; pruned {', '.join(pruned) or 'none'}."
        )

    def _audit(
        self,
        state: V2RunState,
        event_type: str,
        summary: str,
        details: Optional[Dict] = None,
    ) -> None:
        state.audit_trail.append(
            AuditEvent(
                event_id=f"audit_{len(state.audit_trail) + 1:04d}",
                event_type=event_type,
                summary=summary,
                details=details or {},
            )
        )

    def _audit_stop(self, state: V2RunState) -> None:
        evaluation = state.stop_evaluation or self.evaluate_stop(state)
        self._audit(
            state,
            "stop_evaluated",
            evaluation.reason,
            {
                "should_stop": evaluation.should_stop,
                "remaining_question_priority": evaluation.remaining_question_priority,
                "highest_unanswered_priority": evaluation.highest_unanswered_priority,
                "max_remaining_plausible_swing": evaluation.max_remaining_plausible_swing,
                "materiality_threshold": evaluation.materiality_threshold,
                "leading_hypothesis_id": evaluation.leading_hypothesis_id,
                "leading_margin": evaluation.leading_margin,
            },
        )
