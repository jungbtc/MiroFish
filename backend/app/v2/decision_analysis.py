"""Human-confirmed bridge between v2 runs and the pure decision engine."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from pydantic import ValidationError

from ..decision_analysis import (
    DecisionAnalysisInputError,
    DecisionAnalysisResult,
    DecisionModel,
    NeedsConfirmationResult,
    evaluate_decision_model,
)
from ..decision_analysis.audit import build_analysis_audit_record
from ..decision_analysis.evidence_updates import (
    EvidenceUpdateError,
    apply_confirmed_observation,
)
from ..decision_analysis.schemas import EvidenceObservation
from ..decision_analysis.validation import (
    DecisionModelValidationError,
    calculate_model_hash,
    validate_decision_model,
)
from .schemas import InternalEvidence, V2RunState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class V2DecisionAnalysisService:
    """Store proposals separately and calculate only after human confirmation."""

    def propose_model(
        self,
        state: V2RunState,
        payload: Mapping[str, Any],
        *,
        actor_id: str,
        proposed_by: str = "user",
    ) -> Dict[str, Any]:
        try:
            model = DecisionModel.model_validate(payload)
        except ValidationError as exc:
            raise ValueError("Decision-model proposal is invalid.") from exc

        # Approval claims inside a proposal are never trusted. The confirmation
        # endpoint is the only place that can stamp an actor and timestamp.
        model.approval_status = "proposed"
        model.approved_by = None
        model.approved_at = None
        model.model_hash = None
        for action in model.actions:
            action.status = "proposed"
            action.approved_by = None
            action.approved_at = None
        for variable in model.uncertain_variables:
            variable.approval_status = "proposed"
            variable.approved_by = None
            variable.approved_at = None
            variable.distribution.approval_status = "proposed"
            variable.distribution.approved_by = None
            variable.distribution.approved_at = None
        model.utility_model.approval_status = "proposed"
        model.utility_model.approved_by = None
        model.utility_model.approved_at = None

        canonical = json.dumps(
            model.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        proposal_id = f"model_proposal_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"
        record = {
            "proposal_id": proposal_id,
            "status": "proposed",
            "model": model.model_dump(mode="json"),
            "proposed_by": proposed_by,
            "proposed_by_actor_id": actor_id,
            "created_at": _now(),
            "warning": "Proposal only; no action, probability, consequence, or utility is approved.",
        }
        state.decision_model_proposal = record
        return record

    def confirm_model(
        self,
        state: V2RunState,
        *,
        actor_id: str,
        proposal_id: Optional[str],
        confirm_actions: bool,
        confirm_consequence_unit: bool,
        confirm_distributions: bool,
        confirm_utility_model: bool,
    ) -> DecisionModel | Dict[str, Any]:
        record = state.decision_model_proposal
        if not record or not isinstance(record.get("model"), dict):
            raise ValueError("No decision-model proposal is available to confirm.")
        if proposal_id and proposal_id != record.get("proposal_id"):
            raise ValueError("proposal_id does not match the current decision-model proposal.")

        missing = []
        for field, confirmed, reason in (
            ("actions", confirm_actions, "Confirm that every proposed action is actually available."),
            (
                "consequence_unit",
                confirm_consequence_unit,
                "Confirm the consequence and utility unit.",
            ),
            (
                "distributions",
                confirm_distributions,
                "Confirm every uncertain variable and distribution.",
            ),
            (
                "utility_model",
                confirm_utility_model,
                "Confirm the consequence payoffs and risk-neutral utility model.",
            ),
        ):
            if not confirmed:
                missing.append({"field": field, "item_id": None, "reason": reason})
        if missing:
            return {
                "status": "needs_confirmation",
                "missing_confirmations": missing,
                "warnings": ["The proposal has not been applied or calculated."],
            }

        model = DecisionModel.model_validate(record["model"])
        approved_at = _now()
        model.approval_status = "approved"
        model.approved_by = actor_id
        model.approved_at = approved_at
        for action in model.actions:
            action.status = "approved"
            action.approved_by = actor_id
            action.approved_at = approved_at
        for variable in model.uncertain_variables:
            variable.approval_status = "approved"
            variable.approved_by = actor_id
            variable.approved_at = approved_at
            variable.distribution.approval_status = "approved"
            variable.distribution.approved_by = actor_id
            variable.distribution.approved_at = approved_at
        model.utility_model.approval_status = "approved"
        model.utility_model.approved_by = actor_id
        model.utility_model.approved_at = approved_at
        model.model_hash = None
        validate_decision_model(model)
        model.model_hash = calculate_model_hash(model)

        record["status"] = "confirmed"
        record["confirmed_by_actor_id"] = actor_id
        record["confirmed_at"] = approved_at
        record["confirmations"] = {
            "actions": True,
            "consequence_unit": True,
            "distributions": True,
            "utility_model": True,
        }
        state.decision_model = model.model_dump(mode="json")
        state.decision_model_version_id = (
            f"{model.id}:{model.version}:{model.model_hash[:12]}"
        )
        state.decision_analysis_result = None
        state.decision_analysis_options = {}
        state.decision_analysis_trace_id = None
        state.decision_analysis_trace = None
        state.decision_analysis_audit = None
        return model

    def evaluate(
        self,
        state: V2RunState,
        *,
        seed: int = 0,
        sample_count: int = 10_000,
        information_costs: Optional[Mapping[str, Any]] = None,
        evppi_groups: Optional[Mapping[str, list[str]]] = None,
        force_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        model_payload = state.decision_model
        if model_payload is None:
            if state.decision_model_proposal and isinstance(
                state.decision_model_proposal.get("model"), dict
            ):
                outcome = evaluate_decision_model(state.decision_model_proposal["model"])
                return outcome.model_dump(mode="json")
            return {
                "status": "needs_confirmation",
                "missing_confirmations": [
                    {
                        "field": "actions",
                        "item_id": None,
                        "reason": "At least two available actions must be proposed and confirmed.",
                    },
                    {
                        "field": "consequence_unit",
                        "item_id": None,
                        "reason": "A shared consequence or utility unit must be confirmed.",
                    },
                    {
                        "field": "uncertain_variables",
                        "item_id": None,
                        "reason": "At least one uncertain variable and distribution must be confirmed.",
                    },
                    {
                        "field": "utility_model",
                        "item_id": None,
                        "reason": "Consequences and the risk-neutral utility model must be confirmed.",
                    },
                ],
                "warnings": [],
            }

        model = DecisionModel.model_validate(model_payload)
        outcome = evaluate_decision_model(
            model,
            seed=seed,
            sample_count=sample_count,
            information_costs=information_costs,
            evppi_groups=evppi_groups,
            force_method=force_method,
        )
        if isinstance(outcome, NeedsConfirmationResult):
            return outcome.model_dump(mode="json")
        if not isinstance(outcome, DecisionAnalysisResult):
            raise DecisionAnalysisInputError("Unexpected decision-analysis result type.")

        trace_id = f"trace_{uuid4().hex[:20]}"
        full_result = outcome.model_dump(mode="json")
        trace = full_result.pop("trace")
        compact = {**full_result, "trace_id": trace_id}
        audit = build_analysis_audit_record(
            model,
            outcome,
            run_id=state.run_id,
            parent_run_id=state.parent_run_id,
            run_type=state.run_type,
            tenant_id=state.tenant_id,
            owner_actor_id=state.owner_actor_id,
            llm_model_name=state.research_job.model if state.research_job else None,
            provider_response_id=(
                state.research_job.provider_response_id if state.research_job else None
            ),
            prompt_identifier=state.prompt_identifier,
            prompt_hash=state.prompt_hash,
            ontology_hash=state.ontology_hash,
        ).model_dump(mode="json")
        calculation_options = {
            "seed": outcome.seed,
            "sample_count": sample_count,
            "information_costs": full_result.get("information_costs", {}),
            "evppi_groups": {
                str(group_id): list(variable_ids)
                for group_id, variable_ids in (evppi_groups or {}).items()
            },
            "force_method": force_method,
        }
        # Costs and grouping affect information-priority output but not the
        # canonical decision-model hash, so record them as separate confirmed
        # calculation inputs for deterministic replay.
        audit["calculation_options"] = calculation_options
        state.decision_analysis_result = compact
        state.decision_analysis_options = calculation_options
        state.decision_analysis_trace_id = trace_id
        state.decision_analysis_trace = {
            "trace_id": trace_id,
            "run_id": state.run_id,
            "parent_run_id": state.parent_run_id,
            "calculated_at": audit["calculated_at"],
            "trace": trace,
        }
        state.decision_analysis_audit = audit
        state.calculation_version = outcome.calculation_engine_version
        state.calculation_seed = outcome.seed
        state.calculation_sample_count = outcome.sample_count
        return compact

    def propose_evidence_update(
        self,
        state: V2RunState,
        observation_payload: Mapping[str, Any],
        *,
        actor_id: str,
    ) -> Dict[str, Any]:
        if state.decision_model is None:
            raise ValueError("Confirm a decision model before mapping internal evidence.")
        try:
            observation = EvidenceObservation.model_validate(observation_payload)
        except ValidationError as exc:
            raise ValueError("Evidence-update proposal is invalid.") from exc
        evidence = self._active_evidence(state, observation.source_evidence_id)
        observation.approval_status = "proposed"
        observation.approved_by = None
        observation.approved_at = None
        payload = observation.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()[:16]
        proposal = {
            "proposal_id": f"evidence_update_{digest}",
            "status": "proposed",
            "observation": payload,
            "proposed_by_actor_id": actor_id,
            "created_at": _now(),
            "warning": "Proposal only; the distribution has not changed.",
        }
        state.evidence_update_proposals = [
            item
            for item in state.evidence_update_proposals
            if item.get("proposal_id") != proposal["proposal_id"]
        ]
        state.evidence_update_proposals.append(proposal)
        evidence.distribution_application_status = "proposed"
        return proposal

    def confirm_evidence_update(
        self,
        state: V2RunState,
        proposal_id: str,
        *,
        actor_id: str,
        confirmed: bool,
    ) -> Dict[str, Any]:
        proposal = next(
            (
                item
                for item in state.evidence_update_proposals
                if item.get("proposal_id") == proposal_id
            ),
            None,
        )
        if not proposal:
            raise ValueError("Evidence-update proposal was not found.")
        if proposal.get("status") != "proposed":
            raise ValueError("Evidence-update proposal is already resolved.")
        if not confirmed:
            return {
                "status": "needs_confirmation",
                "missing_confirmations": [
                    {
                        "field": "evidence_update",
                        "item_id": proposal_id,
                        "reason": "Confirm the variable mapping and deterministic distribution update.",
                    }
                ],
                "warnings": ["The proposed update has not been applied."],
            }
        if state.decision_model is None:
            raise ValueError("Confirmed decision model is unavailable.")

        observation = EvidenceObservation.model_validate(proposal["observation"])
        evidence = self._active_evidence(state, observation.source_evidence_id)
        observation.approval_status = "approved"
        observation.approved_by = actor_id
        observation.approved_at = _now()
        model = DecisionModel.model_validate(state.decision_model)
        try:
            update = apply_confirmed_observation(model, observation)
        except (EvidenceUpdateError, DecisionModelValidationError) as exc:
            raise ValueError(str(exc)) from exc

        proposal["status"] = update.status
        proposal["confirmed_by_actor_id"] = actor_id
        proposal["confirmed_at"] = observation.approved_at
        proposal["reason"] = update.reason
        proposal["observation"] = observation.model_dump(mode="json")
        evidence.distribution_application_status = update.status
        if proposal_id not in evidence.applied_observation_ids:
            evidence.applied_observation_ids.append(proposal_id)
        if update.status == "applied":
            state.decision_model = update.updated_model.model_dump(mode="json")
            state.decision_model_version_id = (
                f"{update.updated_model.id}:{update.updated_model.version}:"
                f"{(update.updated_model.model_hash or '')[:12]}"
            )
        options = dict(state.decision_analysis_options or {})
        return {
            "proposal": proposal,
            "analysis": self.evaluate(
                state,
                seed=options.get("seed", 0),
                sample_count=options.get("sample_count", 10_000),
                information_costs=options.get("information_costs"),
                evppi_groups=options.get("evppi_groups"),
                force_method=options.get("force_method"),
            ),
        }

    @staticmethod
    def _active_evidence(state: V2RunState, evidence_id: str) -> InternalEvidence:
        evidence = next(
            (
                item
                for item in state.internal_evidence
                if item.evidence_id == evidence_id and not item.retracted
            ),
            None,
        )
        if not evidence:
            raise ValueError("source_evidence_id must reference active evidence in this child run.")
        return evidence
