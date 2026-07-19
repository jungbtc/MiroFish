"""Deprecated fixed-probability scenario scorer.

This compatibility module remains importable for older integrations, but its
subjective constants are not probabilities suitable for decision analysis and
must never be called by the active v2 pipeline.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from .schemas import ExtractedClaim, ScenarioScore, SimulationRound


class ScenarioScoringService:
    def score(self, claims: Iterable[ExtractedClaim], rounds: Iterable[SimulationRound]) -> List[ScenarioScore]:
        raise RuntimeError(
            "ScenarioScoringService is deprecated: fixed scenario weights are not approved probabilities."
        )

    def _risk_terms(self, claims: List[ExtractedClaim], rounds: List[SimulationRound]) -> List[str]:
        text = " ".join([claim.text for claim in claims] + [r.summary for r in rounds]).lower()
        terms = [
            "liquidity", "debt", "court", "regulator", "supplier", "customer",
            "employees", "media", "deadline", "lawsuit", "revenue", "confidence",
        ]
        counts = Counter({term: text.count(term) for term in terms})
        return [term for term, count in counts.most_common() if count > 0]
