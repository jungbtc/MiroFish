"""Stakeholder-agent generation for MiroFish v2."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from .schemas import Entity, ExtractedClaim, StakeholderAgent


DEFAULT_AGENT_TYPES = [
    "company",
    "creditor",
    "investor",
    "regulator",
    "court/legal actor",
    "employee group",
    "competitor",
    "customer/audience",
    "media/advertiser",
]


TYPE_PLAYBOOK = {
    "company": {
        "goals": ["protect continuity", "preserve valuation", "control the narrative"],
        "constraints": ["cash runway", "contract obligations", "public trust"],
        "incentives": ["avoid disorderly outcomes", "retain customers and employees"],
        "actions": ["issue clarification", "negotiate concessions", "prioritize stabilizing stakeholders"],
        "risk": "medium",
    },
    "creditor": {
        "goals": ["recover principal", "improve collateral position"],
        "constraints": ["legal priority", "coordination with other creditors"],
        "incentives": ["push restructuring terms", "avoid value-destructive liquidation"],
        "actions": ["demand updated disclosures", "seek tighter covenants", "coordinate with peers"],
        "risk": "low",
    },
    "investor": {
        "goals": ["protect downside", "identify upside optionality"],
        "constraints": ["information asymmetry", "market volatility"],
        "incentives": ["rebalance exposure", "pressure management"],
        "actions": ["reprice risk", "request guidance", "watch liquidity indicators"],
        "risk": "medium",
    },
    "regulator": {
        "goals": ["protect market order", "enforce compliance"],
        "constraints": ["statutory authority", "evidence threshold"],
        "incentives": ["avoid systemic spillover", "maintain public confidence"],
        "actions": ["request filings", "open review", "signal compliance expectations"],
        "risk": "low",
    },
    "court/legal actor": {
        "goals": ["preserve process integrity", "resolve disputes"],
        "constraints": ["procedural timetable", "submitted evidence"],
        "incentives": ["reduce contested uncertainty"],
        "actions": ["set hearing schedule", "evaluate claims", "approve or reject motions"],
        "risk": "low",
    },
    "employee group": {
        "goals": ["protect jobs", "secure wages and benefits"],
        "constraints": ["bargaining power", "limited visibility"],
        "incentives": ["organize pressure", "seek commitments"],
        "actions": ["ask for guarantees", "coordinate public response", "prepare contingency plans"],
        "risk": "medium",
    },
    "competitor": {
        "goals": ["capture customers", "avoid reputational blowback"],
        "constraints": ["capacity", "regulatory scrutiny"],
        "incentives": ["offer alternatives", "recruit talent"],
        "actions": ["approach vulnerable accounts", "monitor pricing", "hire displaced talent"],
        "risk": "medium",
    },
    "customer/audience": {
        "goals": ["reduce disruption", "protect service quality"],
        "constraints": ["switching costs", "contract terms"],
        "incentives": ["seek assurances", "diversify suppliers"],
        "actions": ["request continuity plans", "delay purchases", "consider alternatives"],
        "risk": "medium",
    },
    "media/advertiser": {
        "goals": ["surface credible story", "manage brand exposure"],
        "constraints": ["verification", "audience attention"],
        "incentives": ["amplify new facts", "avoid association risk"],
        "actions": ["publish timeline", "ask for comment", "pause or shift campaigns"],
        "risk": "high",
    },
}


class StakeholderAgentService:
    def generate_agents(self, entities: Iterable[Entity], claims: Iterable[ExtractedClaim], max_agents: int = 12) -> List[StakeholderAgent]:
        entity_list = list(entities)
        claim_list = list(claims)
        claims_by_entity: Dict[str, List[ExtractedClaim]] = defaultdict(list)

        for claim in claim_list:
            lower = claim.text.lower()
            for entity in entity_list:
                if entity.name.lower() in lower:
                    claims_by_entity[entity.entity_id].append(claim)

        prioritized = sorted(
            entity_list,
            key=lambda entity: len(claims_by_entity.get(entity.entity_id, [])) + len(entity.citations),
            reverse=True,
        )

        agents: List[StakeholderAgent] = []
        used_types = set()
        for entity in prioritized:
            agent_type = entity.type if entity.type != "unknown" else self._fallback_type(entity.name)
            playbook = TYPE_PLAYBOOK.get(agent_type, TYPE_PLAYBOOK["company"])
            agents.append(
                StakeholderAgent(
                    agent_id=f"agent_{len(agents) + 1:03d}",
                    name=entity.name,
                    type=agent_type,
                    goals=playbook["goals"],
                    constraints=playbook["constraints"],
                    incentives=playbook["incentives"],
                    risk_tolerance=playbook["risk"],
                    known_facts=claims_by_entity.get(entity.entity_id, claim_list[:2])[:5],
                    likely_actions=playbook["actions"],
                )
            )
            used_types.add(agent_type)
            if len(agents) >= max_agents:
                break

        for agent_type in DEFAULT_AGENT_TYPES:
            if len(agents) >= max_agents:
                break
            if agent_type in used_types:
                continue
            playbook = TYPE_PLAYBOOK[agent_type]
            agents.append(
                StakeholderAgent(
                    agent_id=f"agent_{len(agents) + 1:03d}",
                    name=agent_type.title(),
                    type=agent_type,
                    goals=playbook["goals"],
                    constraints=playbook["constraints"],
                    incentives=playbook["incentives"],
                    risk_tolerance=playbook["risk"],
                    known_facts=claim_list[:3],
                    likely_actions=playbook["actions"],
                )
            )

        return agents

    def _fallback_type(self, name: str) -> str:
        lower = name.lower()
        for agent_type in DEFAULT_AGENT_TYPES:
            if any(piece and piece in lower for piece in agent_type.replace("/", " ").split()):
                return agent_type
        return "company"
