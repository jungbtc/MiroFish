"""Core-report-linked decision refinement orchestration."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from openai import OpenAI

from ..config import Config
from ..utils.private_data import assert_private_data_allowed
from .decision import (
    DecisionIntelligenceService,
    EVIDENCE_RULE_VERSION,
    MATERIALITY_THRESHOLD,
    MAX_INTERNAL_QUESTIONS,
    is_executable_action_label,
)
from .extraction import ExtractionService
from .report import ForecastReportService
from .research_ingestion import ResearchIngestionService
from .schemas import (
    AuditEvent,
    CoreWorkflowLineage,
    ForecastReport,
    ResearchJobState,
    SourceCitation,
    TokenUsageSummary,
    V2RunState,
)
from .storage import V2Storage


ACTIVE_RESEARCH_STATUSES = {"queued", "in_progress"}
TERMINAL_RESEARCH_STATUSES = {"completed", "failed", "cancelled"}


def _now() -> str:
    return datetime.now().isoformat()


def _object_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    return {}


def summarize_case_title(question: str, project_name: str = "") -> str:
    """Return a stable display title without exposing the raw simulation prompt."""
    project = re.sub(r"\s+", " ", (project_name or "").strip())
    if project.lower() not in {"", "unnamed project", "untitled project", "new project"}:
        return project[:80].rstrip()

    text = re.sub(r"\s+", " ", (question or "").strip())
    lower = text.lower()
    if "samsung" in lower and "hbm4" in lower:
        return "Samsung HBM4 Capacity Strategy"

    subject_match = re.search(
        r"\b(?:if|whether)\s+([A-Z][A-Za-z0-9&.-]+(?:\s+[A-Z][A-Za-z0-9&.-]+){0,2})\s+"
        r"(?:announces|adopts|chooses|decides|plans|expands)",
        text,
    )
    subject = subject_match.group(1) if subject_match else "Decision"
    focus = next(
        (label for term, label in (
            ("advanced packaging", "Advanced Packaging Strategy"),
            ("capacity", "Capacity Strategy"),
            ("acquire", "Acquisition Decision"),
            ("launch", "Launch Strategy"),
            ("supplier", "Supplier Strategy"),
            ("expansion", "Expansion Strategy"),
        ) if term in lower),
        "Strategy Review",
    )
    title = f"{subject} {focus}" if subject != "Decision" else focus
    return title[:80].rstrip()


class CoreRefinementService:
    """Continue a completed FOREFOLD report into durable decision refinement."""

    def __init__(self, client: Optional[OpenAI] = None):
        self.client = client
        self.ingestion = ResearchIngestionService()
        self.extraction = ExtractionService()
        self.decision = DecisionIntelligenceService()
        self.reports = ForecastReportService()

    def initialize_from_core_report(
        self,
        *,
        project_id: str,
        graph_id: str,
        simulation_id: str,
        report_id: str,
        project_name: str,
        decision_question: str,
        report_markdown: str,
        graph_evidence: Optional[Dict[str, Any]] = None,
        simulation_metadata: Optional[Dict[str, Any]] = None,
        existing_run_id: Optional[str] = None,
    ) -> V2RunState:
        """Create the refinement state once, preserving primary workflow lineage."""
        if existing_run_id:
            return V2Storage.load_state(existing_run_id)
        if not all((project_id, graph_id, simulation_id, report_id)):
            raise ValueError("Core project, graph, simulation, and report IDs are required.")
        if not (report_markdown or "").strip():
            raise ValueError("A completed initial report is required before refinement.")

        graph_evidence = self._bounded_mapping(graph_evidence or {}, 120_000)
        simulation_metadata = self._bounded_mapping(simulation_metadata or {}, 40_000)
        document = self.ingestion.ingest_inline_documents(
            [
                {
                    "filename": f"{report_id}_initial_simulation_report.md",
                    "title": "Initial FOREFOLD Simulation Report",
                    "text": report_markdown,
                    "format": "mirofish_initial_report",
                    "source_type": "simulation_derived",
                    "project_id": project_id,
                    "graph_id": graph_id,
                    "simulation_id": simulation_id,
                    "report_id": report_id,
                }
            ]
        )[0]
        self._label_document(document, "simulation_derived", "core_report_lineage")
        claims, entities, events, relationships = self.extraction.extract([document])
        for claim in claims:
            claim.kind = "simulated_stakeholder_reaction"
            claim.provenance_status = "simulation_derived"

        run_id = V2Storage.create_run_id()
        case_title = summarize_case_title(decision_question, project_name)
        display_project_name = (
            case_title
            if (project_name or "").strip().lower() in {"", "unnamed project", "untitled project", "new project"}
            else project_name
        )
        state = V2RunState(
            run_id=run_id,
            run_type="public",
            root_public_run_id=run_id,
            status="awaiting_decision_confirmation",
            project_name=display_project_name,
            case_title=case_title,
            question=decision_question,
            documents=[document],
            claims=claims,
            entities=entities,
            events=events,
            relationships=relationships,
            report=ForecastReport(
                report_id=report_id,
                title="Initial FOREFOLD Simulation Report",
                markdown=report_markdown,
                status="initial",
            ),
            workflow_origin="core_mirofish_report",
            workflow_stage="internal_evidence_refinement",
            core_lineage=CoreWorkflowLineage(
                project_id=project_id,
                graph_id=graph_id,
                simulation_id=simulation_id,
                initial_report_id=report_id,
                decision_question=decision_question,
                graph_evidence_included=bool(graph_evidence),
                simulation_metadata_included=bool(simulation_metadata),
            ),
            initial_report_markdown=report_markdown,
            public_research_context={},
            research_job=None,
            ingestion_status="Initial FOREFOLD report analyzed; decision-critical internal facts ranked by question priority.",
            token_usage=TokenUsageSummary(
                processing_mode="local_report_analysis_plus_bounded_internal_refinement",
                notes=(
                    "The completed FOREFOLD report is reused as the evidence base. Internal answers "
                    "remain local and only update the bounded decision refinement."
                ),
            ),
        )
        self.decision.initialize(state)
        state.report = self.reports.generate(state)
        self._audit(
            state,
            "core_report_linked",
            "The completed simulation report entered bounded decision refinement.",
            {
                "project_id": project_id,
                "graph_id": graph_id,
                "simulation_id": simulation_id,
                "report_id": report_id,
            },
        )
        V2Storage.save_state(state)
        return state

    def migrate_core_state(self, state: V2RunState) -> V2RunState:
        """Upgrade a saved research-gated core run into report-first refinement."""
        if state.workflow_origin != "core_mirofish_report":
            return state
        oversized_questions = any(
            len(question.question) > 320 for question in state.internal_questions
        )
        invalid_actions = bool(state.hypotheses) and not all(
            is_executable_action_label(item.label) for item in state.hypotheses
        )
        has_legacy_retained_evidence = any(
            not item.decision_usable
            and not item.retracted
            and item.interpretation_method != EVIDENCE_RULE_VERSION
            for item in state.internal_evidence
        )
        needs_migration = (
            not state.case_title
            or state.research_job is not None
            or state.workflow_stage.startswith("deep_research")
            or oversized_questions
            or invalid_actions
            or has_legacy_retained_evidence
            or state.execution_plan is None
            or state.execution_plan.version != self.reports.execution.VERSION
            or not state.decision_completion
        )
        if not needs_migration:
            return state

        state.case_title = summarize_case_title(state.question, state.project_name)
        if (state.project_name or "").strip().lower() in {
            "", "unnamed project", "untitled project", "new project"
        }:
            state.project_name = state.case_title
        state.research_job = None
        state.public_research_context = {}
        state.workflow_stage = "internal_evidence_refinement"
        state.ingestion_status = (
            "Initial FOREFOLD report analyzed; decision-critical internal facts ranked by question priority."
        )
        state.token_usage.processing_mode = "local_report_analysis_plus_bounded_internal_refinement"
        state.token_usage.notes = (
            "The completed FOREFOLD report is reused as the evidence base. Internal answers remain "
            "local and only update the bounded decision refinement."
        )
        if not state.hypotheses or not state.internal_questions or oversized_questions:
            self.decision.initialize(state)
        else:
            self.decision.ensure_valid_actions(state)
        self.decision.reassess_retained_evidence(state)
        state.report = self.reports.generate(state)
        state.workflow_stage = state.decision_completion.get(
            "stage", "internal_evidence_refinement"
        )
        self._audit(
            state,
            "core_refinement_migrated",
            "Removed the public-research gate and opened bounded internal-information refinement.",
            {
                "max_internal_questions": MAX_INTERNAL_QUESTIONS,
                "materiality_threshold": MATERIALITY_THRESHOLD,
            },
        )
        V2Storage.save_state(state)
        return state

    def start_research(self, run_id: str, *, retry: bool = False) -> V2RunState:
        """Idempotently start one durable background Responses API job."""
        if not Config.ENABLE_LEGACY_DEEP_RESEARCH:
            raise ValueError("Legacy Deep Research is disabled.")
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            job = state.research_job
            if job and job.status in ACTIVE_RESEARCH_STATUSES:
                return state
            if job and job.status == "completed":
                return state
            if job and job.status in {"failed", "cancelled"} and not retry:
                return state
            if not state.core_lineage:
                raise ValueError("Deep Research can only auto-start from a linked core report.")

            attempt = (job.attempt + 1) if job else 1
            if not job or job.status in {"failed", "cancelled"}:
                job = ResearchJobState(
                    job_id=f"research_{uuid4().hex[:16]}",
                    model=Config.DEEP_RESEARCH_MODEL,
                    attempt=attempt,
                )
                state.research_job = job

            job.status = "queued"
            job.progress = 2.0
            job.message = "Submitting durable public Deep Research job."
            job.started_at = _now()
            job.updated_at = _now()
            job.error = None
            state.workflow_stage = "deep_research_running"
            V2Storage.save_state(state)

            try:
                response = self._client().responses.create(
                    model=job.model,
                    input=self._research_prompt(state),
                    background=True,
                    tools=[{"type": "web_search_preview"}],
                    max_tool_calls=max(1, Config.DEEP_RESEARCH_MAX_TOOL_CALLS),
                )
            except Exception as exc:
                state = V2Storage.load_state(run_id)
                state.research_job.status = "failed"
                state.research_job.progress = 0.0
                state.research_job.message = "Public Deep Research could not be started."
                state.research_job.error = type(exc).__name__
                state.research_job.updated_at = _now()
                state.workflow_stage = "deep_research_failed"
                self._audit(
                    state,
                    "deep_research_failed",
                    "The background research request failed before a provider job was created.",
                    {"error_type": type(exc).__name__, "private_evidence_sent": False},
                )
                V2Storage.save_state(state)
                return state

            state = V2Storage.load_state(run_id)
            state.research_job.provider_response_id = getattr(response, "id", None)
            state.research_job.status = self._provider_status(getattr(response, "status", "queued"))
            state.research_job.progress = 8.0
            state.research_job.message = "Public Deep Research is running in the background."
            state.research_job.updated_at = _now()
            state.research_job.private_evidence_included = False
            state.token_usage.external_llm_calls += 1
            self._audit(
                state,
                "deep_research_started",
                "Started cited public research from the initial FOREFOLD evidence set.",
                {
                    "provider_response_id": state.research_job.provider_response_id,
                    "model": state.research_job.model,
                    "background": True,
                    "private_evidence_sent": False,
                },
            )
            V2Storage.save_state(state)
            return state

    def sync_research(self, run_id: str) -> V2RunState:
        """Poll the provider and durably materialize a completed response once."""
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            job = state.research_job
            if not job or not job.provider_response_id:
                return state
            if job.status == "completed" and job.research_document_id:
                return state
            try:
                response = self._client().responses.retrieve(job.provider_response_id)
            except Exception as exc:
                job.last_polled_at = _now()
                job.updated_at = _now()
                job.message = "Research status is temporarily unavailable; the provider job ID is preserved."
                job.error = type(exc).__name__
                V2Storage.save_state(state)
                return state

            provider_status = self._provider_status(getattr(response, "status", "in_progress"))
            job.status = provider_status
            job.last_polled_at = _now()
            job.updated_at = _now()
            if provider_status in ACTIVE_RESEARCH_STATUSES:
                job.progress = max(job.progress, 35.0 if provider_status == "in_progress" else 12.0)
                job.message = "Deep Research is gathering and synthesizing public sources."
                V2Storage.save_state(state)
                return state
            if provider_status == "cancelled":
                job.cancelled_at = _now()
                job.message = "Public Deep Research was cancelled safely."
                state.workflow_stage = "deep_research_cancelled"
                V2Storage.save_state(state)
                return state
            if provider_status == "failed":
                job.error = self._response_error_type(response)
                job.message = "Public Deep Research failed; retry is available."
                state.workflow_stage = "deep_research_failed"
                self._audit(
                    state,
                    "deep_research_failed",
                    "The provider background job ended without a usable cited report.",
                    {"error_type": job.error, "private_evidence_sent": False},
                )
                V2Storage.save_state(state)
                return state

            return self._materialize_completed_research(state, response)

    def cancel_research(self, run_id: str) -> V2RunState:
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            job = state.research_job
            if not job or job.status not in ACTIVE_RESEARCH_STATUSES:
                return state
            if job.provider_response_id:
                try:
                    self._client().responses.cancel(job.provider_response_id)
                except Exception as exc:
                    job.error = type(exc).__name__
                    job.message = "Cancellation was requested but not yet confirmed."
                    job.updated_at = _now()
                    V2Storage.save_state(state)
                    return state
            job.status = "cancelled"
            job.cancelled_at = _now()
            job.updated_at = _now()
            job.message = "Public Deep Research was cancelled safely."
            state.workflow_stage = "deep_research_cancelled"
            self._audit(
                state,
                "deep_research_cancelled",
                "Cancelled the background public research job without changing core evidence.",
                {"provider_response_id": job.provider_response_id},
            )
            V2Storage.save_state(state)
            return state

    def _materialize_completed_research(self, state: V2RunState, response: Any) -> V2RunState:
        text, citations = self._response_text_and_citations(response)
        if not text.strip():
            state.research_job.status = "failed"
            state.research_job.error = "EmptyResearchOutput"
            state.research_job.message = "Deep Research completed without a usable report."
            state.workflow_stage = "deep_research_failed"
            V2Storage.save_state(state)
            return state

        document = self.ingestion.ingest_inline_documents(
            [
                {
                    "filename": f"{state.research_job.provider_response_id}_deep_research.md",
                    "title": "OpenAI Deep Research Enrichment",
                    "text": text,
                    "citations": citations,
                    "format": "openai_responses_deep_research",
                    "source_type": "external_research",
                    "provider_response_id": state.research_job.provider_response_id,
                }
            ]
        )[0]
        self._label_document(document, "external_research", "openai_responses_citation")
        state.documents = [
            existing
            for existing in state.documents
            if existing.metadata.get("source_type") != "external_research"
        ] + [document]
        state.claims, state.entities, state.events, state.relationships = self.extraction.extract(
            state.documents
        )
        simulation_document_ids = {
            item.document_id
            for item in state.documents
            if item.metadata.get("source_type") == "simulation_derived"
        }
        for claim in state.claims:
            if claim.source_document_id in simulation_document_ids:
                claim.kind = "simulated_stakeholder_reaction"
                claim.provenance_status = "simulation_derived"
            else:
                claim.kind = "external_researched_fact"
                if claim.provenance_status == "report_only":
                    claim.provenance_status = "external_research_report_anchor"

        state.assumptions = []
        state.contradictions = []
        state.hypotheses = []
        state.internal_questions = []
        state.stop_evaluation = None
        self.decision.initialize(state)
        state.research_job.status = "completed"
        state.research_job.progress = 100.0
        state.research_job.message = "Cited public research completed; private-fact refinement is ready."
        state.research_job.completed_at = _now()
        state.research_job.updated_at = _now()
        state.research_job.citation_count = len(citations)
        state.research_job.research_document_id = document.document_id
        state.ingestion_status = "Initial simulation evidence and cited public research are linked."
        state.workflow_stage = "internal_evidence_refinement"
        state.report = self.reports.generate(state)
        self.decision.record_memo_generated(state)
        state.report = self.reports.generate(state)
        self._audit(
            state,
            "deep_research_completed",
            "Cited external evidence was added without exposing internal evidence.",
            {
                "provider_response_id": state.research_job.provider_response_id,
                "citations_preserved": len(citations),
                "research_document_id": document.document_id,
                "private_evidence_sent": False,
            },
        )
        V2Storage.save_state(state)
        return state

    def _research_prompt(self, state: V2RunState) -> str:
        context = state.public_research_context
        # This serialization is deliberately built from the public context only.
        # It never reads state.internal_evidence.
        assert_private_data_allowed(context, sink="external_research")
        prompt = "\n".join(
            [
                "You are enriching an existing FOREFOLD multi-agent simulation for an executive decision.",
                "Research current public evidence that can validate, contradict, or bound the simulated scenarios.",
                "Use primary and authoritative sources where possible. Include inline citations for every material external claim.",
                "Do not invent URLs or claim access to confidential organizational information.",
                "Clearly distinguish observed public facts from your interpretations.",
                "Return a formal English research report that identifies contradictions, missing private facts, and decision implications.",
                "",
                f"DECISION QUESTION:\n{context.get('decision_question', state.question)}",
                "",
                f"INITIAL FOREFOLD SIMULATION REPORT:\n{context.get('initial_report_markdown', '')}",
                "",
                "PUBLIC GRAPH EVIDENCE AND ONTOLOGY SNAPSHOT:",
                json.dumps(context.get("graph_evidence", {}), ensure_ascii=False, sort_keys=True),
                "",
                "SIMULATION METADATA:",
                json.dumps(context.get("simulation_metadata", {}), ensure_ascii=False, sort_keys=True),
            ]
        )
        assert_private_data_allowed(
            {"input": prompt, "internal_evidence": []},
            sink="web_search",
        )
        return prompt

    def _response_text_and_citations(self, response: Any) -> tuple[str, List[Dict[str, Any]]]:
        payload = _object_dict(response)
        text_parts: List[str] = []
        citations: List[Dict[str, Any]] = []
        for item in payload.get("output") or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                for content in item.get("content") or []:
                    if not isinstance(content, dict) or content.get("type") != "output_text":
                        continue
                    text_value = str(content.get("text") or "")
                    if text_value:
                        text_parts.append(text_value)
                    for annotation in content.get("annotations") or []:
                        citation = self._annotation_citation(annotation, text_value)
                        if citation:
                            citations.append(citation)
            if item.get("type") == "web_search_call":
                action = item.get("action") or {}
                for source in action.get("sources") or []:
                    if isinstance(source, dict) and source.get("url"):
                        citations.append(
                            {
                                "label": source.get("title") or source.get("url"),
                                "url": source.get("url"),
                                "marker": source.get("title") or source.get("url"),
                            }
                        )
        if not text_parts:
            output_text = getattr(response, "output_text", None) or payload.get("output_text")
            if output_text:
                text_parts.append(str(output_text))
        return "\n\n".join(text_parts).strip(), self._dedupe_citations(citations)

    def _annotation_citation(self, annotation: Any, text: str) -> Optional[Dict[str, Any]]:
        if not isinstance(annotation, dict):
            return None
        nested = annotation.get("url_citation") if isinstance(annotation.get("url_citation"), dict) else {}
        url = annotation.get("url") or nested.get("url")
        if not url:
            return None
        start = annotation.get("start_index", nested.get("start_index"))
        end = annotation.get("end_index", nested.get("end_index"))
        quote = None
        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
            quote = text[start:end]
        title = annotation.get("title") or nested.get("title") or url
        return {"label": title, "url": url, "marker": title, "quote": quote}

    def _dedupe_citations(self, citations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()
        for citation in citations:
            key = (str(citation.get("url") or "").strip(), str(citation.get("quote") or "").strip())
            if not key[0] or key in seen:
                continue
            seen.add(key)
            result.append(citation)
        return result

    def _label_document(self, document, source_type: str, provenance_status: str) -> None:
        document.metadata["source_type"] = source_type
        document.provenance_summary = (
            "FOREFOLD simulation-derived evidence linked through the core report."
            if source_type == "simulation_derived"
            else "Cited external evidence returned by OpenAI Deep Research."
        )
        for citation in document.imported_citations:
            citation.source_type = source_type
            citation.provenance_status = provenance_status
        for chunk in document.chunks:
            for citation in chunk.citations:
                citation.source_type = source_type
                citation.provenance_status = provenance_status

    def _client(self) -> OpenAI:
        if self.client is None:
            if Config._is_placeholder_secret(Config.OPENAI_API_KEY):
                raise ValueError("OPENAI_API_KEY is required for Deep Research.")
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY, base_url=Config.LLM_BASE_URL)
        return self.client

    def _provider_status(self, status: Any) -> str:
        raw_status = getattr(status, "value", status)
        normalized = str(raw_status or "").strip().lower()
        if "." in normalized:
            normalized = normalized.rsplit(".", 1)[-1]
        if normalized in {"queued", "in_progress"}:
            return normalized
        if normalized == "completed":
            return "completed"
        if normalized in {"cancelled", "canceled"}:
            return "cancelled"
        if normalized in {"failed", "incomplete", "expired"}:
            return "failed"
        return "in_progress"

    def _response_error_type(self, response: Any) -> str:
        payload = _object_dict(response)
        error = payload.get("error") or payload.get("incomplete_details") or {}
        if isinstance(error, dict):
            return str(error.get("code") or error.get("reason") or error.get("type") or "ProviderFailure")
        return type(error).__name__ if error else "ProviderFailure"

    def _bounded_mapping(self, value: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
        try:
            encoded = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return {"summary": str(value)[:max_chars], "truncated": True}
        if len(encoded) <= max_chars:
            return json.loads(encoded)
        return {"summary": encoded[:max_chars], "truncated": True}

    def _audit(
        self,
        state: V2RunState,
        event_type: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        state.audit_trail.append(
            AuditEvent(
                event_id=f"audit_{len(state.audit_trail) + 1:04d}",
                event_type=event_type,
                summary=summary,
                details=details or {},
            )
        )
