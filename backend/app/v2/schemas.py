"""Typed data contracts for the MiroFish v2 pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    source_id: str
    chunk_id: Optional[str] = None
    label: Optional[str] = None
    url: Optional[str] = None
    quote: Optional[str] = None


class ResearchChunk(BaseModel):
    chunk_id: str
    source_id: str
    text: str
    start_char: int = 0
    end_char: int = 0


class ResearchDocument(BaseModel):
    document_id: str
    filename: str
    content_hash: str
    text: str
    chunks: List[ResearchChunk] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedClaim(BaseModel):
    claim_id: str
    text: str
    source_document_id: str
    source_chunk_id: str
    confidence: float = 0.5
    timestamp: Optional[str] = None
    citations: List[SourceCitation] = Field(default_factory=list)


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


class V2RunState(BaseModel):
    run_id: str
    project_name: str
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
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat()
