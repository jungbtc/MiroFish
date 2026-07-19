"""End-to-end FOREFOLD decision orchestration."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from .authorization import ActorContext, RunAuthorization, local_actor
from .decision import DecisionIntelligenceService
from .decision_analysis import V2DecisionAnalysisService
from .extraction import ExtractionService
from .qa import FollowupQAService
from .report import ForecastReportService
from .research_ingestion import ResearchIngestionService
from .schemas import AuditEvent, InternalEvidence, ResearchDocument, TargetedReevaluation, V2RunState
from .storage import V2Storage


class MiroFishV2Pipeline:
    def __init__(self):
        self.ingestion = ResearchIngestionService()
        self.extraction = ExtractionService()
        self.decision = DecisionIntelligenceService()
        self.decision_analysis = V2DecisionAnalysisService()
        self.reports = ForecastReportService()
        self.qa = FollowupQAService()

    def run_from_uploads(
        self,
        uploaded_files: Iterable,
        question: str,
        project_name: str = "FOREFOLD Run",
        rounds: int = 3,
        scenario_theme: Optional[str] = None,
    ) -> V2RunState:
        run_id = V2Storage.create_run_id()
        try:
            documents = self.ingestion.ingest_uploads(run_id, uploaded_files)
            return self.run_from_documents(
                documents=documents,
                question=question,
                project_name=project_name,
                rounds=rounds,
                scenario_theme=scenario_theme,
                run_id=run_id,
            )
        except Exception:
            # Uploads are persisted under a provisional run ID.  Failed imports
            # must not leave orphaned payloads that accumulate indefinitely.
            V2Storage.discard_uninitialized_run(run_id)
            raise

    def run_from_inline_documents(
        self,
        document_items: Iterable[Dict[str, Any]],
        question: str,
        project_name: str = "FOREFOLD Run",
        rounds: int = 3,
        scenario_theme: Optional[str] = None,
    ) -> V2RunState:
        documents = self.ingestion.ingest_inline_documents(document_items)
        return self.run_from_documents(
            documents=documents,
            question=question,
            project_name=project_name,
            rounds=rounds,
            scenario_theme=scenario_theme,
        )

    def run_from_paths(
        self,
        paths: Iterable[Path | str],
        question: str,
        project_name: str = "FOREFOLD Run",
        rounds: int = 3,
        scenario_theme: Optional[str] = None,
    ) -> V2RunState:
        documents = self.ingestion.ingest_paths(paths)
        return self.run_from_documents(
            documents=documents,
            question=question,
            project_name=project_name,
            rounds=rounds,
            scenario_theme=scenario_theme,
        )

    def run_from_documents(
        self,
        documents: List[ResearchDocument],
        question: str,
        project_name: str = "FOREFOLD Run",
        rounds: int = 3,
        scenario_theme: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> V2RunState:
        if not documents:
            raise ValueError("At least one research document is required.")

        run_id = run_id or V2Storage.create_run_id()
        claims, entities, events, relationships = self.extraction.extract(documents)
        state = V2RunState(
            run_id=run_id,
            run_type="public",
            root_public_run_id=run_id,
            status="awaiting_decision_confirmation",
            project_name=project_name,
            question=question,
            documents=documents,
            claims=claims,
            entities=entities,
            events=events,
            relationships=relationships,
        )
        self.decision.initialize(state)
        self._assert_local_decision_invariant(state)
        state.report = self.reports.generate(state)
        self.decision.record_memo_generated(state)
        state.report = self.reports.generate(state)
        V2Storage.save_state(state)
        return state

    def resume_rounds(self, run_id: str, target_rounds: int) -> V2RunState:
        raise ValueError(
            "Decision-layer runs do not use simulation rounds. Submit ranked internal evidence instead."
        )

    def submit_internal_answer(
        self,
        run_id: str,
        question_id: str,
        answer: str,
        *,
        submitted_by: str = "decision_owner",
        confidential: bool = True,
        confidence: float = 0.8,
        interpretation: Optional[str] = None,
        actor: Optional[ActorContext] = None,
        visibility: Optional[str] = None,
        classification: Optional[str] = None,
        supersedes_evidence_id: Optional[str] = None,
        retention_policy: str = "inherit_run_policy",
        retention_until: Optional[str] = None,
    ) -> V2RunState:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            if supersedes_evidence_id:
                superseded = next(
                    (
                        item
                        for item in state.internal_evidence
                        if item.evidence_id == supersedes_evidence_id and not item.retracted
                    ),
                    None,
                )
                if not superseded:
                    raise ValueError("supersedes_evidence_id must reference active evidence in this run")
            if not state.hypotheses:
                self.decision.initialize(state)
            self.decision.submit_answer(
                state,
                question_id,
                answer,
                submitted_by=submitted_by,
                confidential=confidential,
                confidence=confidence,
                interpretation=interpretation,
                submitted_by_actor_id=actor.actor_id,
                visibility=visibility or ("restricted" if confidential else "internal"),
                classification=classification or (
                    "internal_confidential" if confidential else "internal"
                ),
                supersedes_evidence_id=supersedes_evidence_id,
                retention_policy=retention_policy,
                retention_until=retention_until,
            )
            newest_evidence = state.internal_evidence[-1] if state.internal_evidence else None
            newest_impact = state.decision_impacts[-1] if state.decision_impacts else None
            if newest_evidence and newest_evidence.decision_usable:
                affected = []
                if newest_impact and newest_impact.evidence_id == newest_evidence.evidence_id:
                    affected = [
                        change.hypothesis_id
                        for change in newest_impact.hypothesis_changes
                        if abs(change.delta) > 0.001 or change.before_status != change.after_status
                    ]
                state.targeted_reevaluations.append(
                    TargetedReevaluation(
                        reevaluation_id=f"reeval_{uuid4().hex[:16]}",
                        evidence_id=newest_evidence.evidence_id,
                        affected_hypothesis_ids=affected,
                        mode="bounded_branch_reevaluation",
                        rationale=(
                            "Re-evaluated only the decision paths affected by the new private fact; "
                            "the external research corpus was not queried again and the private answer "
                            "was not sent to a public model or web-search tool."
                        ),
                        simulation_id=(
                            state.core_lineage.simulation_id if state.core_lineage else None
                        ),
                    )
                )
            self._assert_local_decision_invariant(state)
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def evaluate_stop(
        self,
        run_id: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> V2RunState:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            if not state.hypotheses:
                self.decision.initialize(state)
            self.decision.refresh_stop_evaluation(state)
            self._assert_local_decision_invariant(state)
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def propose_internal_question(
        self,
        run_id: str,
        question: str,
        category: str,
        *,
        owner_hint: str = "Decision owner",
        actor: Optional[ActorContext] = None,
    ) -> V2RunState:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            self.decision.propose_internal_question(
                state,
                question,
                category,
                owner_hint=owner_hint,
            )
            self._assert_local_decision_invariant(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def propose_decision_model(
        self,
        run_id: str,
        model_payload: Dict[str, Any],
        *,
        actor: Optional[ActorContext] = None,
        proposed_by: str = "user",
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            state.decision_analysis_waiver = None
            proposal = self.decision_analysis.propose_model(
                state,
                model_payload,
                actor_id=actor.actor_id,
                proposed_by=proposed_by,
            )
            state.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{uuid4().hex[:16]}",
                    event_type="decision_model_proposed",
                    summary="Stored a decision-model proposal without approving or calculating it.",
                    details={
                        "proposal_id": proposal["proposal_id"],
                        "actor_id": actor.actor_id,
                        "proposal_only": True,
                    },
                )
            )
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return {"proposal": proposal, "state": state}

    def confirm_decision_actions(
        self,
        run_id: str,
        action_ids: List[str],
        *,
        actor: Optional[ActorContext] = None,
        confirmed_by: str = "decision_owner",
    ) -> V2RunState:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            self.decision.confirm_actions(
                state,
                action_ids,
                confirmed_by=confirmed_by,
            )
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def assign_execution_owners(
        self,
        run_id: str,
        owners: Dict[str, str],
        *,
        actor: Optional[ActorContext] = None,
    ) -> V2RunState:
        """Persist named owners and recompile only derived execution outputs."""
        actor = actor or local_actor()
        allowed_types = {"VALIDATE", "GATE"}
        normalized: Dict[str, str] = {}
        for action_type, owner in owners.items():
            if action_type not in allowed_types:
                raise ValueError("Execution owners may only be assigned for VALIDATE or GATE.")
            name = str(owner or "").strip()
            if not name:
                raise ValueError(f"{action_type} owner is required.")
            if self.reports.execution.is_placeholder_owner(name):
                raise ValueError(f"{action_type} requires a named accountable role or person.")
            normalized[action_type] = name
        if not normalized:
            raise ValueError("At least one execution owner assignment is required.")

        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            if not state.decision_completion.get("internal_evidence_complete"):
                raise ValueError("Complete internal evidence before assigning execution owners.")
            if not state.decision_completion.get("decision_model_complete"):
                raise ValueError("Approve the decision method before assigning execution owners.")
            state.execution_owner_assignments.update(normalized)
            state.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{uuid4().hex[:16]}",
                    event_type="execution_owners_assigned",
                    summary="Assigned named owners to the remaining execution stages.",
                    details={
                        "action_types": sorted(normalized),
                        "actor_id": actor.actor_id,
                        "simulation_rerun": False,
                    },
                )
            )
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def waive_quantitative_decision_analysis(
        self,
        run_id: str,
        *,
        actor: Optional[ActorContext] = None,
        confirmed_by: str = "decision_owner",
        reason: str = "The decision owner approved an evidence-backed qualitative decision without a quantitative utility model.",
    ) -> V2RunState:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            self.decision.waive_quantitative_analysis(
                state,
                confirmed_by=confirmed_by,
                reason=reason,
            )
            self._assert_local_decision_invariant(state)
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def confirm_decision_model(
        self,
        run_id: str,
        confirmation: Dict[str, Any],
        *,
        actor: Optional[ActorContext] = None,
        seed: int = 0,
        sample_count: int = 10_000,
        information_costs: Optional[Dict[str, Any]] = None,
        evppi_groups: Optional[Dict[str, List[str]]] = None,
        force_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            confirmed = self.decision_analysis.confirm_model(
                state,
                actor_id=actor.actor_id,
                proposal_id=confirmation.get("proposal_id"),
                confirm_actions=confirmation.get("confirm_actions") is True,
                confirm_consequence_unit=(
                    confirmation.get("confirm_consequence_unit") is True
                ),
                confirm_distributions=confirmation.get("confirm_distributions") is True,
                confirm_utility_model=confirmation.get("confirm_utility_model") is True,
            )
            if isinstance(confirmed, dict):
                return {"analysis": confirmed, "state": state}

            analysis = self.decision_analysis.evaluate(
                state,
                seed=seed,
                sample_count=sample_count,
                information_costs=information_costs,
                evppi_groups=evppi_groups,
                force_method=force_method,
            )
            state.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{uuid4().hex[:16]}",
                    event_type="decision_model_confirmed",
                    summary="Human-confirmed actions, consequences, distributions, and utility model.",
                    details={
                        "decision_model_version_id": state.decision_model_version_id,
                        "actor_id": actor.actor_id,
                        "calculation_status": analysis.get("status"),
                    },
                )
            )
            self._publish_decision_analysis_state(state)
            return {"analysis": analysis, "state": state}

    def evaluate_decision_analysis(
        self,
        run_id: str,
        *,
        actor: Optional[ActorContext] = None,
        seed: int = 0,
        sample_count: int = 10_000,
        information_costs: Optional[Dict[str, Any]] = None,
        evppi_groups: Optional[Dict[str, List[str]]] = None,
        force_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            analysis = self.decision_analysis.evaluate(
                state,
                seed=seed,
                sample_count=sample_count,
                information_costs=information_costs,
                evppi_groups=evppi_groups,
                force_method=force_method,
            )
            if analysis.get("status") == "calculated":
                state.audit_trail.append(
                    AuditEvent(
                        event_id=f"audit_{uuid4().hex[:16]}",
                        event_type="decision_analysis_calculated",
                        summary="Calculated expected utility, regret, and value of information deterministically.",
                        details={
                            "trace_id": state.decision_analysis_trace_id,
                            "model_hash": analysis.get("model_hash"),
                            "method": analysis.get("method"),
                            "seed": analysis.get("seed"),
                            "sample_count": analysis.get("sample_count"),
                        },
                    )
                )
                self._publish_decision_analysis_state(state)
            return {"analysis": analysis, "state": state}

    def propose_evidence_update(
        self,
        run_id: str,
        observation_payload: Dict[str, Any],
        *,
        actor: Optional[ActorContext] = None,
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            proposal = self.decision_analysis.propose_evidence_update(
                state,
                observation_payload,
                actor_id=actor.actor_id,
            )
            state.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{uuid4().hex[:16]}",
                    event_type="evidence_update_proposed",
                    summary="Stored a structured evidence mapping proposal without applying it.",
                    details={
                        "proposal_id": proposal["proposal_id"],
                        "source_evidence_id": proposal["observation"]["source_evidence_id"],
                        "variable_id": proposal["observation"]["variable_id"],
                        "actor_id": actor.actor_id,
                    },
                )
            )
            V2Storage.save_state(state)
            return {"proposal": proposal, "state": state}

    def confirm_evidence_update(
        self,
        run_id: str,
        proposal_id: str,
        *,
        confirmed: bool,
        actor: Optional[ActorContext] = None,
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(state, actor)
            outcome = self.decision_analysis.confirm_evidence_update(
                state,
                proposal_id,
                actor_id=actor.actor_id,
                confirmed=confirmed,
            )
            if outcome.get("status") == "needs_confirmation":
                return {"outcome": outcome, "state": state}
            proposal = outcome["proposal"]
            state.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{uuid4().hex[:16]}",
                    event_type="evidence_update_confirmed",
                    summary="Applied or safely retained a human-confirmed evidence mapping.",
                    details={
                        "proposal_id": proposal_id,
                        "status": proposal.get("status"),
                        "source_evidence_id": proposal["observation"]["source_evidence_id"],
                        "variable_id": proposal["observation"]["variable_id"],
                        "actor_id": actor.actor_id,
                    },
                )
            )
            self._publish_decision_analysis_state(state)
            return {"outcome": outcome, "state": state}

    def load_decision_trace(
        self,
        run_id: str,
        trace_id: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> Dict[str, Any]:
        state = V2Storage.load_state(run_id)
        RunAuthorization.assert_can_read(state, actor or local_actor())
        if state.decision_analysis_trace_id != trace_id:
            raise FileNotFoundError("calculation trace not found")
        return V2Storage.load_calculation_trace(run_id, trace_id)

    def _publish_decision_analysis_state(self, state: V2RunState) -> None:
        self._assert_local_decision_invariant(state)
        state.report = self.reports.generate(state)
        state.workflow_stage = state.decision_completion.get(
            "stage", "decision_model_completion"
        )
        self.decision.record_memo_generated(state)
        state.report = self.reports.generate(state)
        V2Storage.save_state(state)

    def answer(
        self,
        run_id: str,
        question: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> Dict:
        state = V2Storage.load_state(run_id)
        RunAuthorization.assert_can_read(state, actor or local_actor())
        return self.qa.answer(state, question)

    def load_state(
        self,
        run_id: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> V2RunState:
        state = V2Storage.load_state(run_id)
        RunAuthorization.assert_can_read(state, actor or local_actor())
        if state.run_type == "internal":
            with V2Storage.lock_run(run_id):
                state = V2Storage.load_state(run_id)
                if not state.hypotheses:
                    self.decision.initialize(state)
                    repaired = True
                else:
                    repaired = self.decision.ensure_valid_actions(state)
                reassessed = self.decision.reassess_retained_evidence(state)
                execution_upgrade = bool(
                    state.execution_plan is None
                    or state.execution_plan.version != self.reports.execution.VERSION
                )
                if repaired or reassessed or execution_upgrade:
                    self._assert_local_decision_invariant(state)
                    state.report = self.reports.generate(state)
                    self.decision.record_memo_generated(state)
                    state.report = self.reports.generate(state)
                    V2Storage.save_state(state)
        return state

    def fork_public_run(
        self,
        run_id: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> V2RunState:
        """Seal a public baseline and create an explicitly owned private child."""
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            parent = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_fork(parent, actor)
            if parent.internal_evidence:
                raise ValueError(
                    "A public baseline containing private evidence cannot be forked; migrate it as an internal run."
                )
            if not parent.sealed_at:
                parent.sealed_at = datetime.now().isoformat()
                parent.status = "sealed"
                parent.audit_trail.append(
                    AuditEvent(
                        event_id=f"audit_{len(parent.audit_trail) + 1:04d}",
                        event_type="public_baseline_sealed",
                        summary="The public baseline was sealed before private refinement began.",
                        details={"raw_private_evidence_logged": False},
                    )
                )
                V2Storage.save_state(parent)

            child = parent.model_copy(deep=True)
            child.run_id = V2Storage.create_run_id()
            child.run_type = "internal"
            child.parent_run_id = parent.run_id
            child.root_public_run_id = parent.root_public_run_id or parent.run_id
            child.root_run_id = None
            child.tenant_id = actor.tenant_id
            child.owner_actor_id = actor.actor_id
            child.owner_actor_ids = [actor.actor_id]
            child.created_by_actor_id = actor.actor_id
            child.sealed_at = None
            child.status = "active"
            child.state_revision = 0
            child.created_at = datetime.now().isoformat()
            child.updated_at = child.created_at
            child.workflow_stage = "internal_evidence_refinement"
            child.production_auth_blocker = actor.production_auth_blocker
            child.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{len(child.audit_trail) + 1:04d}",
                    event_type="internal_run_forked",
                    summary="Created an owned internal child from the sealed public baseline.",
                    details={
                        "parent_run_id": parent.run_id,
                        "root_public_run_id": child.root_public_run_id,
                        "actor_id": actor.actor_id,
                        "private_evidence_inherited": False,
                    },
                )
            )
            V2Storage.save_state(child)
            return child

    def lineage(
        self,
        run_id: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        state = V2Storage.load_state(run_id)
        RunAuthorization.assert_can_read(state, actor)

        ancestors: List[Dict[str, Any]] = []
        cursor = state
        visited = {state.run_id}
        while cursor.parent_run_id:
            parent = V2Storage.load_state(cursor.parent_run_id)
            RunAuthorization.assert_can_read(parent, actor)
            if parent.run_id in visited:
                raise ValueError("Run lineage contains a cycle.")
            visited.add(parent.run_id)
            ancestors.append(self._lineage_node(parent))
            cursor = parent
        ancestors.reverse()

        children: List[Dict[str, Any]] = []
        for candidate_id in V2Storage.list_run_ids():
            if candidate_id == run_id:
                continue
            try:
                candidate = V2Storage.load_state(candidate_id)
            except (FileNotFoundError, ValueError):
                continue
            if candidate.parent_run_id != run_id:
                continue
            try:
                RunAuthorization.assert_can_read(candidate, actor)
            except PermissionError:
                continue
            children.append(self._lineage_node(candidate))

        return {
            "current": self._lineage_node(state),
            "ancestors": ancestors,
            "children": children,
            "root_public_run_id": state.root_public_run_id or (
                state.run_id if state.run_type == "public" else None
            ),
            "production_auth_blocker": state.production_auth_blocker,
        }

    def compare_runs(
        self,
        parent_run_id: str,
        child_run_id: str,
        *,
        actor: Optional[ActorContext] = None,
    ) -> Dict[str, Any]:
        actor = actor or local_actor()
        parent = V2Storage.load_state(parent_run_id)
        child = V2Storage.load_state(child_run_id)
        RunAuthorization.assert_can_read(parent, actor)
        RunAuthorization.assert_can_read(child, actor)
        if child.parent_run_id != parent.run_id:
            raise ValueError("Runs are not a direct parent/child lineage pair.")

        parent_evidence = {item.evidence_id: item for item in parent.internal_evidence}
        child_evidence = {item.evidence_id: item for item in child.internal_evidence}
        added_ids = sorted(set(child_evidence) - set(parent_evidence))
        removed_ids = sorted(set(parent_evidence) - set(child_evidence))
        retracted_ids = sorted(
            evidence_id
            for evidence_id, evidence in child_evidence.items()
            if evidence.retracted
            and not getattr(parent_evidence.get(evidence_id), "retracted", False)
        )

        parent_recommendation = self.decision.recommendation(parent)
        child_recommendation = self.decision.recommendation(child)
        parent_analysis = self._calculated_analysis(parent)
        child_analysis = self._calculated_analysis(child)
        distribution_changes = self._distribution_changes(parent, child)
        parent_numeric_recommendation = parent_analysis.get("recommended_action")
        child_numeric_recommendation = child_analysis.get("recommended_action")
        return {
            "parent_run_id": parent.run_id,
            "child_run_id": child.run_id,
            "changed_evidence": {
                "added": [self._evidence_metadata(child_evidence[item]) for item in added_ids],
                "removed": removed_ids,
                "retracted": retracted_ids,
            },
            "changed_distributions": {
                "available": bool(
                    parent.decision_model is not None or child.decision_model is not None
                ),
                "changes": distribution_changes,
                "reason": (
                    None
                    if parent.decision_model is not None or child.decision_model is not None
                    else "No human-confirmed typed distribution is stored on either run."
                ),
            },
            "expected_utility": {
                "available": bool(parent_analysis or child_analysis),
                "parent": parent_analysis.get("expected_utility_by_action"),
                "child": child_analysis.get("expected_utility_by_action"),
            },
            "recommendation": {
                "parent": parent_numeric_recommendation or parent_recommendation,
                "child": child_numeric_recommendation or child_recommendation,
                "parent_source": (
                    "deterministic_decision_analysis"
                    if parent_numeric_recommendation
                    else "legacy_qualitative"
                ),
                "child_source": (
                    "deterministic_decision_analysis"
                    if child_numeric_recommendation
                    else "legacy_qualitative"
                ),
                "changed": (
                    parent_numeric_recommendation or parent_recommendation
                )
                != (child_numeric_recommendation or child_recommendation),
            },
            "expected_regret": {
                "available": bool(parent_analysis or child_analysis),
                "parent": parent_analysis.get("expected_regret_by_action"),
                "child": child_analysis.get("expected_regret_by_action"),
            },
            "evpi": {
                "available": bool(parent_analysis or child_analysis),
                "parent": parent_analysis.get("evpi"),
                "child": child_analysis.get("evpi"),
            },
            "remaining_evpi": child_analysis.get("evpi"),
            "decision_model_version": {
                "parent": parent.decision_model_version_id,
                "child": child.decision_model_version_id,
            },
            "calculation": {
                "parent_version": parent.calculation_version,
                "child_version": child.calculation_version,
                "parent_seed": parent.calculation_seed,
                "child_seed": child.calculation_seed,
                "parent_sample_count": parent.calculation_sample_count,
                "child_sample_count": child.calculation_sample_count,
                "parent_model_hash": parent_analysis.get("model_hash"),
                "child_model_hash": child_analysis.get("model_hash"),
            },
            "production_auth_blocker": child.production_auth_blocker,
        }

    def retract_internal_evidence(
        self,
        run_id: str,
        evidence_id: str,
        *,
        reason: str,
        actor: Optional[ActorContext] = None,
    ) -> V2RunState:
        """Retract evidence and deterministically replay the child from its parent."""
        actor = actor or local_actor()
        with V2Storage.lock_run(run_id, require_existing=True):
            current = V2Storage.load_state(run_id)
            RunAuthorization.assert_can_mutate(current, actor)
            if not current.parent_run_id:
                raise ValueError("Evidence replay requires an internal child with a parent baseline.")
            target = next(
                (item for item in current.internal_evidence if item.evidence_id == evidence_id),
                None,
            )
            if not target:
                raise ValueError("Evidence was not found in this internal run.")
            if target.retracted:
                raise ValueError("Evidence is already retracted.")

            parent = V2Storage.load_state(current.parent_run_id)
            RunAuthorization.assert_can_read(parent, actor)
            if parent.run_type != "public" or not parent.sealed_at:
                raise ValueError("Evidence replay requires a sealed public parent baseline.")
            if parent.internal_evidence:
                raise ValueError("The public parent is invalid because it contains private evidence.")

            records = [item.model_copy(deep=True) for item in current.internal_evidence]
            retracted_at = datetime.now().isoformat()
            for record in records:
                if record.evidence_id == evidence_id:
                    record.retracted = True
                    record.retracted_at = retracted_at
                    record.retracted_by_actor_id = actor.actor_id
                    record.retraction_reason = reason
                    record.distribution_application_status = "not_proposed"
                    record.applied_observation_ids = []

            replay = parent.model_copy(deep=True)
            replay.run_id = current.run_id
            replay.run_type = "internal"
            replay.parent_run_id = current.parent_run_id
            replay.root_public_run_id = current.root_public_run_id
            replay.root_run_id = None
            replay.tenant_id = current.tenant_id
            replay.owner_actor_id = current.owner_actor_id
            replay.owner_actor_ids = list(current.owner_actor_ids)
            replay.created_by_actor_id = current.created_by_actor_id
            replay.created_at = current.created_at
            replay.updated_at = current.updated_at
            replay.sealed_at = None
            replay.status = current.status
            replay.state_revision = current.state_revision
            replay.workflow_stage = "internal_evidence_refinement"
            replay.production_auth_blocker = current.production_auth_blocker
            replay.audit_trail = [
                item.model_copy(deep=True) for item in parent.audit_trail
            ]
            replay.audit_trail.extend(
                item.model_copy(deep=True)
                for item in current.audit_trail
                if item.event_type == "internal_run_forked"
            )

            # Recreate user-proposed private question wording before replaying
            # answers. Matching by category avoids relying on regenerated IDs.
            for proposed in current.internal_questions:
                if proposed.origin != "user_proposed":
                    continue
                try:
                    self.decision.propose_internal_question(
                        replay,
                        proposed.question,
                        proposed.category,
                        owner_hint=proposed.owner_hint,
                    )
                except ValueError:
                    # If the proposal is no longer material on the clean parent,
                    # it is intentionally left out of the replay.
                    continue

            question_categories = {
                item.question_id: item.category for item in current.internal_questions
            }
            generated: Dict[str, InternalEvidence] = {}
            for record in records:
                if record.retracted:
                    continue
                category = question_categories.get(record.question_id)
                replay_question = next(
                    (
                        item
                        for item in replay.internal_questions
                        if item.category == category and not item.answer_id
                    ),
                    None,
                )
                if not replay_question:
                    raise ValueError("Active evidence could not be mapped to the parent question model.")
                if replay_question.status != "requested":
                    for item in replay.internal_questions:
                        if item.status == "requested":
                            item.status = "pending"
                    replay_question.status = "requested"
                self.decision.submit_answer(
                    replay,
                    replay_question.question_id,
                    record.answer,
                    submitted_by=record.submitted_by,
                    confidential=record.confidential,
                    confidence=record.confidence,
                    interpretation=record.interpretation,
                    evidence_id=record.evidence_id,
                    submitted_by_actor_id=record.submitted_by_actor_id,
                    visibility=record.visibility,
                    classification=record.classification,
                    supersedes_evidence_id=record.supersedes_evidence_id,
                    retention_policy=record.retention_policy,
                    retention_until=record.retention_until,
                    created_at=record.created_at,
                )
                generated[record.evidence_id] = replay.internal_evidence[-1]

            replay.internal_evidence = [
                generated.get(record.evidence_id, record) for record in records
            ]
            active_ids = {
                item.evidence_id for item in replay.internal_evidence if not item.retracted
            }
            replay.targeted_reevaluations = [
                item.model_copy(deep=True)
                for item in current.targeted_reevaluations
                if item.evidence_id in active_ids
            ]
            decision_replay = self._replay_decision_analysis(
                current,
                replay,
                active_evidence_ids=active_ids,
                fallback_actor_id=actor.actor_id,
            )
            # Retraction is an append-only audit event. Replay operations above
            # may generate temporary audit rows while rebuilding qualitative
            # state; replace those with the original durable history before
            # recording the replay outcome.
            replay.audit_trail = [
                item.model_copy(deep=True) for item in current.audit_trail
            ]
            replay.audit_trail.append(
                AuditEvent(
                    event_id=f"audit_{uuid4().hex[:16]}",
                    event_type="internal_evidence_retracted",
                    summary="Retracted internal evidence and replayed the child from its public parent.",
                    details={
                        "evidence_id": evidence_id,
                        "actor_id": actor.actor_id,
                        "replay_method": "parent_plus_active_child_evidence",
                        "decision_analysis_replay": decision_replay,
                        "raw_answer_logged": False,
                    },
                )
            )
            self._assert_local_decision_invariant(replay)
            replay.report = self.reports.generate(replay)
            self.decision.record_memo_generated(replay)
            replay.report = self.reports.generate(replay)
            V2Storage.save_state(replay)
            return replay

    @staticmethod
    def _lineage_node(state: V2RunState) -> Dict[str, Any]:
        return {
            "run_id": state.run_id,
            "run_type": state.run_type,
            "parent_run_id": state.parent_run_id,
            "root_public_run_id": state.root_public_run_id,
            "status": state.status,
            "sealed_at": state.sealed_at,
            "decision_model_version_id": state.decision_model_version_id,
            "state_revision": state.state_revision,
        }

    @staticmethod
    def _evidence_metadata(evidence: InternalEvidence) -> Dict[str, Any]:
        return {
            "evidence_id": evidence.evidence_id,
            "question_id": evidence.question_id,
            "visibility": evidence.visibility,
            "classification": evidence.classification,
            "submitted_by_actor_id": evidence.submitted_by_actor_id,
            "supersedes_evidence_id": evidence.supersedes_evidence_id,
            "retracted": evidence.retracted,
            "retention_policy": evidence.retention_policy,
            "retention_until": evidence.retention_until,
            "outbound_external_use": evidence.outbound_external_use,
            "created_at": evidence.created_at,
        }

    @staticmethod
    def _calculated_analysis(state: V2RunState) -> Dict[str, Any]:
        result = state.decision_analysis_result or {}
        return result if result.get("status") == "calculated" else {}

    @staticmethod
    def _distribution_changes(
        parent: V2RunState,
        child: V2RunState,
    ) -> List[Dict[str, Any]]:
        def distributions(state: V2RunState) -> Dict[str, Any]:
            model = state.decision_model or {}
            variables = model.get("uncertain_variables") or []
            return {
                item["id"]: item.get("distribution")
                for item in variables
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }

        parent_items = distributions(parent)
        child_items = distributions(child)
        changes = []
        for variable_id in sorted(set(parent_items) | set(child_items)):
            if parent_items.get(variable_id) == child_items.get(variable_id):
                continue
            changes.append(
                {
                    "variable_id": variable_id,
                    "parent": parent_items.get(variable_id),
                    "child": child_items.get(variable_id),
                }
            )
        return changes

    def _replay_decision_analysis(
        self,
        current: V2RunState,
        replay: V2RunState,
        *,
        active_evidence_ids: set[str],
        fallback_actor_id: str,
    ) -> Dict[str, Any]:
        """Rebuild an approved model from its proposal plus active observations."""
        if current.decision_model is None:
            replay.decision_model_proposal = None
            replay.decision_model = None
            replay.decision_analysis_result = None
            replay.decision_analysis_options = {}
            replay.decision_analysis_trace_id = None
            replay.decision_analysis_trace = None
            replay.decision_analysis_audit = None
            replay.evidence_update_proposals = []
            return {"status": "not_configured", "replayed_observations": 0}

        proposal_record = deepcopy(current.decision_model_proposal)
        if not isinstance(proposal_record, dict) or not isinstance(
            proposal_record.get("model"), dict
        ):
            # A historical calculated model without its unapproved source
            # proposal cannot be safely reverse-mutated after retraction.
            replay.decision_model_proposal = None
            replay.decision_model = None
            replay.decision_analysis_result = None
            replay.decision_analysis_options = {}
            replay.decision_analysis_trace_id = None
            replay.decision_analysis_trace = None
            replay.decision_analysis_audit = None
            replay.evidence_update_proposals = []
            return {
                "status": "needs_model_reconfirmation",
                "replayed_observations": 0,
            }

        replay.decision_model_proposal = proposal_record
        confirmation_actor = str(
            proposal_record.get("confirmed_by_actor_id") or fallback_actor_id
        )
        confirmed = self.decision_analysis.confirm_model(
            replay,
            actor_id=confirmation_actor,
            proposal_id=proposal_record.get("proposal_id"),
            confirm_actions=True,
            confirm_consequence_unit=True,
            confirm_distributions=True,
            confirm_utility_model=True,
        )
        if isinstance(confirmed, dict):
            raise RuntimeError("Stored decision-model confirmations could not be replayed.")

        replay.evidence_update_proposals = []
        replayed_count = 0
        excluded_count = 0
        for old_proposal in sorted(
            current.evidence_update_proposals,
            key=lambda item: (str(item.get("created_at") or ""), str(item.get("proposal_id") or "")),
        ):
            observation = old_proposal.get("observation")
            if not isinstance(observation, dict):
                continue
            source_evidence_id = observation.get("source_evidence_id")
            if source_evidence_id not in active_evidence_ids:
                excluded = deepcopy(old_proposal)
                excluded["status"] = "source_retracted"
                replay.evidence_update_proposals.append(excluded)
                excluded_count += 1
                continue

            proposal = self.decision_analysis.propose_evidence_update(
                replay,
                observation,
                actor_id=str(
                    old_proposal.get("proposed_by_actor_id") or fallback_actor_id
                ),
            )
            if old_proposal.get("status") not in {
                "applied",
                "not_applied_to_distribution",
            }:
                continue
            outcome = self.decision_analysis.confirm_evidence_update(
                replay,
                proposal["proposal_id"],
                actor_id=str(
                    old_proposal.get("confirmed_by_actor_id") or fallback_actor_id
                ),
                confirmed=True,
            )
            if outcome.get("proposal", {}).get("status") in {
                "applied",
                "not_applied_to_distribution",
            }:
                replayed_count += 1

        options = deepcopy(current.decision_analysis_options or {})
        analysis = self.decision_analysis.evaluate(
            replay,
            seed=options.get("seed", current.calculation_seed or 0),
            sample_count=options.get("sample_count", 10_000),
            information_costs=options.get("information_costs"),
            evppi_groups=options.get("evppi_groups"),
            force_method=options.get("force_method"),
        )
        return {
            "status": analysis.get("status"),
            "replayed_observations": replayed_count,
            "excluded_retracted_observations": excluded_count,
            "model_hash": analysis.get("model_hash"),
            "seed": analysis.get("seed"),
            "sample_count": analysis.get("sample_count"),
        }

    def _assert_local_decision_invariant(self, state: V2RunState) -> None:
        if any(evidence.outbound_external_use for evidence in state.internal_evidence):
            raise RuntimeError(
                "Private-evidence invariant violated: internal evidence cannot be marked for outbound use."
            )
        if state.research_job and state.research_job.private_evidence_included:
            raise RuntimeError(
                "Private-evidence invariant violated: Deep Research cannot include internal evidence."
            )
        if state.workflow_origin == "core_mirofish_report":
            return
        usage = state.token_usage
        if (
            usage.processing_mode != "local_deterministic"
            or usage.external_llm_calls
            or usage.prompt_tokens
            or usage.completion_tokens
            or usage.total_tokens
        ):
            raise RuntimeError(
                "Decision-layer invariant violated: imported evidence analysis must not make model calls."
            )

    def run_demo(self, rounds: int = 3) -> V2RunState:
        root = Path(__file__).resolve().parents[3]
        sample = root / "test_inputs" / "v2_demo" / "cited_deep_research_report.md"
        return self.run_from_paths(
            [sample],
            question="Should Northstar commit to an immediate restructuring or stage a reversible plan?",
            project_name="Deep Research Decision Demo",
            rounds=rounds,
        )
