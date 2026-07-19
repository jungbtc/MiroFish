"""Typed data contracts for the MiroFish v2 pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SourceCitation(BaseModel):
    source_id: str
    citation_id: Optional[str] = None
    chunk_id: Optional[str] = None
    label: Optional[str] = None
    url: Optional[str] = None
    quote: Optional[str] = None
    source_type: str = "imported_report"
    provenance_status: str = "report_anchor"
    original_marker: Optional[str] = None
    original_source_id: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None


class ResearchChunk(BaseModel):
    chunk_id: str
    source_id: str
    text: str
    start_char: int = 0
    end_char: int = 0
    citations: List[SourceCitation] = Field(default_factory=list)
    page_number: Optional[int] = None


class ResearchDocument(BaseModel):
    document_id: str
    filename: str
    content_hash: str
    text: str
    chunks: List[ResearchChunk] = Field(default_factory=list)
    imported_citations: List[SourceCitation] = Field(default_factory=list)
    document_format: str = "text"
    provenance_summary: str = "Imported report; source links preserved when present."
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedClaim(BaseModel):
    claim_id: str
    original_claim_id: Optional[str] = None
    text: str
    source_document_id: str
    source_chunk_id: str
    confidence: float = 0.5
    timestamp: Optional[str] = None
    citations: List[SourceCitation] = Field(default_factory=list)
    kind: str = "sourced_fact"
    provenance_status: str = "report_only"
    is_generated: bool = False
    contradicts_claim_ids: List[str] = Field(default_factory=list)


class Entity(BaseModel):
    entity_id: str
    name: str
    type: str = "unknown"
    source_ids: List[str] = Field(default_factory=list)
    citations: List[SourceCitation] = Field(default_factory=list)


class Event(BaseModel):
    event_id: str
    title: str
    description: str
    timestamp: Optional[str] = None
    involved_entities: List[str] = Field(default_factory=list)
    citations: List[SourceCitation] = Field(default_factory=list)


class Relationship(BaseModel):
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    type: str
    description: str
    citations: List[SourceCitation] = Field(default_factory=list)


class StakeholderAgent(BaseModel):
    agent_id: str
    name: str
    type: str
    goals: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    incentives: List[str] = Field(default_factory=list)
    risk_tolerance: str = "medium"
    known_facts: List[ExtractedClaim] = Field(default_factory=list)
    likely_actions: List[str] = Field(default_factory=list)


class SimulationAction(BaseModel):
    action_id: str
    agent_id: str
    action: str
    reasoning_summary: str
    cited_evidence: List[SourceCitation] = Field(default_factory=list)
    changed_assumptions: List[str] = Field(default_factory=list)
    emerging_risks: List[str] = Field(default_factory=list)


class SimulationRound(BaseModel):
    round_id: str
    round_number: int
    scenario_theme: str
    actions: List[SimulationAction] = Field(default_factory=list)
    summary: str
    citations: List[SourceCitation] = Field(default_factory=list)


class ScenarioScore(BaseModel):
    name: str
    probability: float
    confidence: float
    upside_impact: str
    downside_impact: str
    key_drivers: List[str] = Field(default_factory=list)
    uncertainty_factors: List[str] = Field(default_factory=list)
    derivation: str


class ForecastReport(BaseModel):
    report_id: str
    title: str
    markdown: str
    citations: List[SourceCitation] = Field(default_factory=list)
    status: str = "interim"
    recommendation: Optional[str] = None
    stop_reason: Optional[str] = None


class DecisionAssumption(BaseModel):
    assumption_id: str
    text: str
    category: str
    status: str = "unresolved"
    rationale: str
    source_claim_ids: List[str] = Field(default_factory=list)
    citations: List[SourceCitation] = Field(default_factory=list)


class Contradiction(BaseModel):
    contradiction_id: str
    claim_ids: List[str] = Field(default_factory=list)
    summary: str
    severity: str = "medium"
    status: str = "open"
    citations: List[SourceCitation] = Field(default_factory=list)


class DecisionHypothesis(BaseModel):
    hypothesis_id: str
    label: str
    description: str
    status: str = "active"
    decision_role: str = "alternative"
    support_score: float = 0.0
    previous_score: float = 0.0
    last_change: float = 0.0
    rationale: str
    supporting_claim_ids: List[str] = Field(default_factory=list)
    opposing_claim_ids: List[str] = Field(default_factory=list)
    assumption_ids: List[str] = Field(default_factory=list)
    prune_reason: Optional[str] = None
    pruned_by_evidence_id: Optional[str] = None
    prune_rule: Optional[str] = None


class QuestionPriorityBreakdown(BaseModel):
    decision_sensitivity: float
    uncertainty: float
    answerability: float
    urgency: float
    formula: str = "100 × (0.40 sensitivity + 0.30 uncertainty + 0.20 answerability + 0.10 urgency)"


# Compatibility import for code that persisted the pre-2.3 class name. New
# state and API payloads use question-priority terminology exclusively.
InformationValueBreakdown = QuestionPriorityBreakdown


class InternalQuestion(BaseModel):
    question_id: str
    question: str
    category: str
    rationale: str
    owner_hint: str
    status: str = "pending"
    rank: int = 0
    question_priority_score: float
    value_components: QuestionPriorityBreakdown
    expected_change: str
    maximum_plausible_swing: float = 0.0
    report_coverage: float = 0.0
    affected_hypothesis_ids: List[str] = Field(default_factory=list)
    answer_id: Optional[str] = None
    origin: str = "engine_ranked"

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_information_value_score(cls, value: Any) -> Any:
        """Read historical state while emitting only corrected terminology."""
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if "question_priority_score" not in payload and "information_value_score" in payload:
            payload["question_priority_score"] = payload["information_value_score"]
        payload.pop("information_value_score", None)
        return payload

    @property
    def information_value_score(self) -> float:
        """Deprecated in-process alias; excluded from serialized output."""
        return self.question_priority_score


class InternalEvidence(BaseModel):
    evidence_id: str
    question_id: str
    answer: str
    interpretation: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, allow_inf_nan=False)
    decision_usable: bool = True
    question_relevant: bool = True
    interpretation_method: str = "deterministic_category_rules"
    interpretation_rationale: str = ""
    submitted_by: str = "decision_owner"
    submitted_by_actor_id: str = "local-workspace"
    confidential: bool = True
    visibility: Literal["public", "internal", "restricted"] = "restricted"
    classification: str = "internal_confidential"
    source_type: str = "internal_user_supplied"
    supersedes_evidence_id: Optional[str] = None
    retracted: bool = False
    retracted_at: Optional[str] = None
    retracted_by_actor_id: Optional[str] = None
    retraction_reason: Optional[str] = None
    retention_policy: str = "inherit_run_policy"
    retention_until: Optional[str] = None
    outbound_external_use: bool = False
    # Confidential answer text is persisted once in the run's owner-only
    # confidential area. Canonical state and public derivatives retain only
    # these references; ``V2Storage.load_state`` hydrates ``answer`` after the
    # run has passed its normal authorization boundary.
    answer_storage_ref: Optional[str] = None
    answer_storage_run_id: Optional[str] = None
    distribution_application_status: Literal[
        "not_proposed",
        "proposed",
        "applied",
        "not_applied_to_distribution",
    ] = "not_proposed"
    applied_observation_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class HypothesisChange(BaseModel):
    hypothesis_id: str
    before_score: float
    after_score: float
    delta: float
    before_status: str
    after_status: str
    explanation: str


class DecisionImpact(BaseModel):
    impact_id: str
    question_id: str
    evidence_id: str
    summary: str
    hypothesis_changes: List[HypothesisChange] = Field(default_factory=list)
    graph_change_summary: str
    graph_revision: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExecutionFact(BaseModel):
    fact_id: str
    fact_type: Literal[
        "objective",
        "hard_constraint",
        "budget",
        "capacity",
        "owner",
        "success_metric",
        "guardrail",
        "stop_trigger",
        "dependency",
        "assumption",
        "unknown",
        "stakeholder_risk",
    ]
    statement: str
    value: Optional[float] = None
    unit: Optional[str] = None
    scope: str = "selected action"
    clarity: Literal["low", "medium", "high"] = "medium"
    binding: bool = False
    source_question_id: Optional[str] = None
    source_question_category: Optional[str] = None
    source_answer_id: Optional[str] = None
    source_claim_id: Optional[str] = None
    approved_by: Optional[str] = None


class ExecutionAction(BaseModel):
    action_id: str
    action_type: Literal["COMMIT", "DESIGN", "BUILD", "VALIDATE", "GATE", "PAUSE_REVERSE"]
    stage: str
    title: str
    purpose: str
    owner: str
    accountable_executive: str
    contributors: List[str] = Field(default_factory=list)
    start_condition: str
    deliverable: str
    deadline: str
    budget_or_capacity: str
    acceptance_criteria: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    evidence_source_ids: List[str] = Field(default_factory=list)
    failure_response: str
    status: str = "not_started"


class ExecutionPlan(BaseModel):
    version: str = "execution_compiler_v1"
    decision_action_id: Optional[str] = None
    decision_action_label: str
    facts: List[ExecutionFact] = Field(default_factory=list)
    actions: List[ExecutionAction] = Field(default_factory=list)
    coverage: Dict[str, Any] = Field(default_factory=dict)
    executability: Dict[str, Any] = Field(default_factory=dict)
    ready: bool = False
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class StopEvaluation(BaseModel):
    should_stop: bool = False
    reason: str
    remaining_question_priority: float = 100.0
    highest_unanswered_priority: float = 100.0
    max_remaining_plausible_swing: float = 1.0
    materiality_threshold: float = 45.0
    leading_hypothesis_id: Optional[str] = None
    leading_margin: float = 0.0
    evaluated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_priority_names(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if "remaining_question_priority" not in payload:
            payload["remaining_question_priority"] = payload.get(
                "remaining_information_value", 100.0
            )
        if "highest_unanswered_priority" not in payload:
            payload["highest_unanswered_priority"] = payload.get(
                "highest_unanswered_score", payload["remaining_question_priority"]
            )
        payload.pop("remaining_information_value", None)
        payload.pop("highest_unanswered_score", None)
        return payload

    @property
    def remaining_information_value(self) -> float:
        """Deprecated in-process alias; excluded from serialized output."""
        return self.remaining_question_priority

    @property
    def highest_unanswered_score(self) -> float:
        """Deprecated in-process alias; excluded from serialized output."""
        return self.highest_unanswered_priority


class AuditEvent(BaseModel):
    event_id: str
    event_type: str
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TokenUsageSummary(BaseModel):
    processing_mode: str = "local_deterministic"
    external_llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    imported_evidence_reused: bool = True
    notes: str = (
        "The completed FOREFOLD report is reused as the evidence base; decision refinement runs "
        "locally without a second research or model pass."
    )


class CoreWorkflowLineage(BaseModel):
    """Immutable IDs tying refinement back to the primary MiroFish workflow."""

    project_id: str
    graph_id: str
    simulation_id: str
    initial_report_id: str
    decision_question: str
    graph_evidence_included: bool = False
    simulation_metadata_included: bool = False
    linked_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResearchJobState(BaseModel):
    """Durable state for one OpenAI background Deep Research response."""

    job_id: str
    status: str = "not_started"
    model: str = "o4-mini-deep-research"
    provider_response_id: Optional[str] = None
    attempt: int = 1
    progress: float = 0.0
    message: str = "Waiting to start public research."
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    last_polled_at: Optional[str] = None
    error: Optional[str] = None
    citation_count: int = 0
    research_document_id: Optional[str] = None
    private_evidence_included: bool = False


class TargetedReevaluation(BaseModel):
    reevaluation_id: str
    evidence_id: str
    affected_hypothesis_ids: List[str] = Field(default_factory=list)
    mode: str = "deterministic_branch_update"
    status: str = "completed"
    rationale: str
    simulation_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class V2RunState(BaseModel):
    schema_version: str = "2.2"
    state_revision: int = 0
    graph_revision: int = 0
    run_id: str
    # Compatibility defaults intentionally classify pre-lineage states as
    # local internal working cases. New public baselines are created
    # explicitly by the primary report workflow.
    run_type: Literal["public", "internal"] = "internal"
    parent_run_id: Optional[str] = None
    root_public_run_id: Optional[str] = None
    # Temporary read compatibility for an early lineage prototype. New writes
    # use ``root_public_run_id`` exclusively.
    root_run_id: Optional[str] = None
    tenant_id: str = "local-workspace"
    owner_actor_id: str = "local-workspace"
    owner_actor_ids: List[str] = Field(default_factory=lambda: ["local-workspace"])
    created_by_actor_id: str = "local-workspace"
    sealed_at: Optional[str] = None
    status: str = "active"
    decision_model_version_id: Optional[str] = None
    calculation_version: Optional[str] = None
    calculation_seed: Optional[int] = None
    calculation_sample_count: Optional[int] = None
    decision_model_proposal: Optional[Dict[str, Any]] = None
    decision_model: Optional[Dict[str, Any]] = None
    decision_analysis_result: Optional[Dict[str, Any]] = None
    decision_analysis_waiver: Optional[Dict[str, Any]] = None
    action_confirmation: Optional[Dict[str, Any]] = None
    decision_completion: Dict[str, Any] = Field(default_factory=dict)
    decision_analysis_options: Dict[str, Any] = Field(default_factory=dict)
    decision_analysis_trace_id: Optional[str] = None
    # In-memory handoff only. V2Storage persists this separately from state and
    # reports, then the field is absent on reload.
    decision_analysis_trace: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    decision_analysis_audit: Optional[Dict[str, Any]] = None
    evidence_update_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_identifier: Optional[str] = None
    prompt_hash: Optional[str] = None
    ontology_hash: Optional[str] = None
    production_auth_blocker: str = (
        "Local or shared API-key access is not user/tenant authentication; "
        "production multi-user deployment requires an external identity provider."
    )
    project_name: str
    case_title: Optional[str] = None
    question: str
    documents: List[ResearchDocument] = Field(default_factory=list)
    claims: List[ExtractedClaim] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    agents: List[StakeholderAgent] = Field(default_factory=list)
    rounds: List[SimulationRound] = Field(default_factory=list)
    scores: List[ScenarioScore] = Field(default_factory=list)
    report: Optional[ForecastReport] = None
    graph: Dict[str, Any] = Field(default_factory=dict)
    ingestion_status: str = "Completed FOREFOLD report imported and analyzed."
    assumptions: List[DecisionAssumption] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    hypotheses: List[DecisionHypothesis] = Field(default_factory=list)
    internal_questions: List[InternalQuestion] = Field(default_factory=list)
    internal_evidence: List[InternalEvidence] = Field(default_factory=list)
    decision_impacts: List[DecisionImpact] = Field(default_factory=list)
    execution_owner_assignments: Dict[str, str] = Field(default_factory=dict)
    execution_plan: Optional[ExecutionPlan] = None
    stop_evaluation: Optional[StopEvaluation] = None
    audit_trail: List[AuditEvent] = Field(default_factory=list)
    token_usage: TokenUsageSummary = Field(default_factory=TokenUsageSummary)
    workflow_origin: str = "legacy_research_import"
    workflow_stage: str = "decision_refinement"
    core_lineage: Optional[CoreWorkflowLineage] = None
    initial_report_markdown: Optional[str] = None
    public_research_context: Dict[str, Any] = Field(default_factory=dict)
    research_job: Optional[ResearchJobState] = None
    targeted_reevaluations: List[TargetedReevaluation] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @model_validator(mode="before")
    @classmethod
    def classify_legacy_lineage(cls, value: Any) -> Any:
        """Classify old payloads without rewriting their durable contents.

        Report-first core states with no private answers are public baselines.
        Older states that already contain private answers remain internal
        working cases so loading them cannot suddenly expose confidential data.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if "run_type" not in payload:
            is_clean_core_baseline = (
                payload.get("workflow_origin") == "core_mirofish_report"
                and not payload.get("internal_evidence")
            )
            payload["run_type"] = "public" if is_clean_core_baseline else "internal"
        if payload.get("run_type") == "public" and not payload.get("root_public_run_id"):
            payload["root_public_run_id"] = payload.get("root_run_id") or payload.get("run_id")
        if "owner_actor_id" not in payload:
            owners = payload.get("owner_actor_ids") or []
            payload["owner_actor_id"] = owners[0] if owners else "local-workspace"
        if "owner_actor_ids" not in payload:
            payload["owner_actor_ids"] = [payload["owner_actor_id"]]
        return payload

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat()
