"""End-to-end MiroFish v2 orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .decision import DecisionIntelligenceService
from .extraction import ExtractionService
from .qa import FollowupQAService
from .report import ForecastReportService
from .research_ingestion import ResearchIngestionService
from .schemas import ResearchDocument, V2RunState
from .storage import V2Storage


class MiroFishV2Pipeline:
    def __init__(self):
        self.ingestion = ResearchIngestionService()
        self.extraction = ExtractionService()
        self.decision = DecisionIntelligenceService()
        self.reports = ForecastReportService()
        self.qa = FollowupQAService()

    def run_from_uploads(
        self,
        uploaded_files: Iterable,
        question: str,
        project_name: str = "MiroFish v2 Run",
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
        project_name: str = "MiroFish v2 Run",
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
        project_name: str = "MiroFish v2 Run",
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
        project_name: str = "MiroFish v2 Run",
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
    ) -> V2RunState:
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
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
            )
            self._assert_local_decision_invariant(state)
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def evaluate_stop(self, run_id: str) -> V2RunState:
        with V2Storage.lock_run(run_id, require_existing=True):
            state = V2Storage.load_state(run_id)
            if not state.hypotheses:
                self.decision.initialize(state)
            self.decision.refresh_stop_evaluation(state)
            self._assert_local_decision_invariant(state)
            state.report = self.reports.generate(state)
            self.decision.record_memo_generated(state)
            state.report = self.reports.generate(state)
            V2Storage.save_state(state)
            return state

    def answer(self, run_id: str, question: str) -> Dict:
        state = V2Storage.load_state(run_id)
        return self.qa.answer(state, question)

    def load_state(self, run_id: str) -> V2RunState:
        state = V2Storage.load_state(run_id)
        if not state.hypotheses:
            with V2Storage.lock_run(run_id):
                state = V2Storage.load_state(run_id)
                if not state.hypotheses:
                    self.decision.initialize(state)
                    self._assert_local_decision_invariant(state)
                    state.report = self.reports.generate(state)
                    self.decision.record_memo_generated(state)
                    state.report = self.reports.generate(state)
                    V2Storage.save_state(state)
        return state

    def _assert_local_decision_invariant(self, state: V2RunState) -> None:
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
