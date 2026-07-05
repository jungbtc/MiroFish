"""Scenario scoring for MiroFish v2."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from .schemas import ExtractedClaim, ScenarioScore, SimulationRound


class ScenarioScoringService:
    def score(self, claims: Iterable[ExtractedClaim], rounds: Iterable[SimulationRound]) -> List[ScenarioScore]:
        claim_list = list(claims)
        round_list = list(rounds)
        evidence_count = len(claim_list)
        confidence = min(0.75, 0.35 + evidence_count * 0.01 + len(round_list) * 0.03)
        risk_terms = self._risk_terms(claim_list, round_list)

        return [
            ScenarioScore(
                name="base case",
                probability=0.52,
                confidence=round(confidence, 2),
                upside_impact="moderate stabilization if stakeholders coordinate quickly",
                downside_impact="continued uncertainty if key disclosures lag",
                key_drivers=risk_terms[:4] or ["stakeholder coordination", "evidence quality"],
                uncertainty_factors=["source coverage may be incomplete", "agent actions are simulated, not observed"],
                derivation=(
                    "Assigned as the central scenario because most rounds show negotiation and risk containment. "
                    "Probability is a subjective model output, not an objective forecast."
                ),
            ),
            ScenarioScore(
                name="upside case",
                probability=0.21,
                confidence=round(max(confidence - 0.08, 0.2), 2),
                upside_impact="faster resolution, lower stakeholder conflict, improved confidence",
                downside_impact="upside weakens if one major actor defects",
                key_drivers=["credible communication", "liquidity or operational relief", "aligned incentives"],
                uncertainty_factors=["positive catalysts may not materialize", "media framing can reverse quickly"],
                derivation=(
                    "Lower probability because the simulation requires several actors to cooperate at the same time."
                ),
            ),
            ScenarioScore(
                name="downside case",
                probability=0.27,
                confidence=round(max(confidence - 0.04, 0.2), 2),
                upside_impact="limited; downside path may force clarity",
                downside_impact="legal, financing, operational, or reputational stress compounds",
                key_drivers=risk_terms[:5] or ["legal pressure", "financing pressure", "trust erosion"],
                uncertainty_factors=["unknown private negotiations", "missing counterparty incentives"],
                derivation=(
                    "Raised above the upside case because several simulated rounds surface coordination and trust risks."
                ),
            ),
        ]

    def _risk_terms(self, claims: List[ExtractedClaim], rounds: List[SimulationRound]) -> List[str]:
        text = " ".join([claim.text for claim in claims] + [r.summary for r in rounds]).lower()
        terms = [
            "liquidity", "debt", "court", "regulator", "supplier", "customer",
            "employees", "media", "deadline", "lawsuit", "revenue", "confidence",
        ]
        counts = Counter({term: text.count(term) for term in terms})
        return [term for term, count in counts.most_common() if count > 0]
