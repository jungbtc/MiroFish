"""End-to-end MiroFish v2 orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .agents import StakeholderAgentService
from .extraction import ExtractionService
from .graph import RelationshipGraphService
from .qa import FollowupQAService
from .report import ForecastReportService
from .research_ingestion import ResearchIngestionService
from .schemas import ResearchDocument, V2RunState
from .scoring import ScenarioScoringService
from .simulation import SimulationLoopService
from .storage import V2Storage


class MiroFishV2Pipeline:
    def __init__(self):
        self.ingestion = ResearchIngestionService()
        self.extraction = ExtractionService()
        self.graph = RelationshipGraphService()
        self.agents = StakeholderAgentService()
        self.simulation = SimulationLoopService()
        self.scoring = ScenarioScoringService()
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
        documents = self.ingestion.ingest_uploads(run_id, uploaded_files)
        return self.run_from_documents(
            documents=documents,
            question=question,
            project_name=project_name,
            rounds=rounds,
            scenario_theme=scenario_theme,
            run_id=run_id,
        )

    def run_from_inline_documents(
        self,
        document_items: Iterable[Dict[str, str]],
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
        graph = self.graph.build_graph(entities, relationships)
        agents = self.agents.generate_agents(entities, claims)
        theme = scenario_theme or question or "base scenario"
        round_states = self.simulation.run_rounds(agents, theme, rounds=max(3, rounds))
        scores = self.scoring.score(claims, round_states)

        state = V2RunState(
            run_id=run_id,
            project_name=project_name,
            question=question,
            documents=documents,
            claims=claims,
            entities=entities,
            events=events,
            relationships=relationships,
            agents=agents,
            rounds=round_states,
            scores=scores,
            graph=graph,
        )
        state.report = self.reports.generate(state)
        V2Storage.save_state(state)
        return state

    def resume_rounds(self, run_id: str, target_rounds: int) -> V2RunState:
        state = V2Storage.load_state(run_id)
        state.rounds = self.simulation.run_rounds(
            state.agents,
            state.question,
            rounds=max(target_rounds, len(state.rounds)),
            existing_rounds=state.rounds,
        )
        state.scores = self.scoring.score(state.claims, state.rounds)
        state.report = self.reports.generate(state)
        V2Storage.save_state(state)
        return state

    def answer(self, run_id: str, question: str) -> Dict:
        state = V2Storage.load_state(run_id)
        return self.qa.answer(state, question)

    def load_state(self, run_id: str) -> V2RunState:
        return V2Storage.load_state(run_id)

    def run_demo(self, rounds: int = 3) -> V2RunState:
        root = Path(__file__).resolve().parents[3]
        sample = root / "test_inputs" / "v2_demo" / "fictional_restructuring_case.md"
        return self.run_from_paths(
            [sample],
            question="Forecast how stakeholders will react to the restructuring over the next 90 days.",
            project_name="Fictional Restructuring Demo",
            rounds=rounds,
            scenario_theme="90-day restructuring response",
        )
