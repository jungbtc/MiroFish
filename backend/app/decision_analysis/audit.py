"""Privacy-conscious audit metadata for reproducible decision calculations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from .schemas import DecisionAnalysisResult, DecisionModel, StrictModel
from .validation import approved_actions, approved_variables, canonical_model_payload


CALCULATION_ENGINE_VERSION = "mirofish-decision-analysis/1.0.0"
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AnalysisAuditRecord(StrictModel):
    run_id: str
    parent_run_id: Optional[str] = None
    run_type: str
    tenant_id: Optional[str] = None
    owner_actor_id: Optional[str] = None
    llm_model_name: Optional[str] = None
    provider_response_id: Optional[str] = None
    prompt_identifier: Optional[str] = None
    prompt_hash: Optional[Sha256Digest] = None
    ontology_hash: Optional[Sha256Digest] = None
    decision_model_hash: Sha256Digest
    calculation_engine_version: str = CALCULATION_ENGINE_VERSION
    utility_model_version: str
    random_seed: int
    sample_count: int
    source_evidence_ids: List[str] = Field(default_factory=list)
    approved_inputs: Dict[str, Any]
    actor_confirmations: List[Dict[str, Any]] = Field(default_factory=list)
    calculated_at: str


def build_analysis_audit_record(
    model: DecisionModel,
    result: DecisionAnalysisResult,
    *,
    run_id: str,
    run_type: str,
    parent_run_id: str | None = None,
    tenant_id: str | None = None,
    owner_actor_id: str | None = None,
    llm_model_name: str | None = None,
    provider_response_id: str | None = None,
    prompt_identifier: str | None = None,
    prompt_hash: str | None = None,
    ontology_hash: str | None = None,
) -> AnalysisAuditRecord:
    """Build audit data without copying confidential source text or model prompts."""

    variables = approved_variables(model)
    confirmations: List[Dict[str, Any]] = [
        {
            "kind": "decision_model",
            "item_id": model.id,
            "approved_by": model.approved_by,
            "approved_at": model.approved_at,
        },
        {
            "kind": "utility_model",
            "item_id": model.utility_model.version,
            "approved_by": model.utility_model.approved_by,
            "approved_at": model.utility_model.approved_at,
        },
    ]
    confirmations.extend(
        {
            "kind": "action",
            "item_id": action.id,
            "approved_by": action.approved_by,
            "approved_at": action.approved_at,
        }
        for action in approved_actions(model)
    )
    for variable in variables:
        confirmations.extend(
            [
                {
                    "kind": "uncertain_variable",
                    "item_id": variable.id,
                    "approved_by": variable.approved_by,
                    "approved_at": variable.approved_at,
                },
                {
                    "kind": "distribution",
                    "item_id": variable.id,
                    "approved_by": variable.distribution.approved_by,
                    "approved_at": variable.distribution.approved_at,
                },
            ]
        )
    source_evidence_ids = sorted(
        {evidence_id for variable in variables for evidence_id in variable.evidence_ids}
    )
    return AnalysisAuditRecord(
        run_id=run_id,
        parent_run_id=parent_run_id,
        run_type=run_type,
        tenant_id=tenant_id,
        owner_actor_id=owner_actor_id,
        llm_model_name=llm_model_name,
        provider_response_id=provider_response_id,
        prompt_identifier=prompt_identifier,
        prompt_hash=prompt_hash,
        ontology_hash=ontology_hash,
        decision_model_hash=result.model_hash,
        utility_model_version=result.utility_model_version,
        random_seed=result.seed,
        sample_count=result.sample_count,
        source_evidence_ids=source_evidence_ids,
        approved_inputs=canonical_model_payload(model),
        actor_confirmations=confirmations,
        calculated_at=datetime.now(timezone.utc).isoformat(),
    )
