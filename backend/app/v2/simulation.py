"""Resumable multi-round simulation loop for MiroFish v2."""

from __future__ import annotations

import hashlib
from typing import Iterable, List

from .schemas import SimulationAction, SimulationRound, SourceCitation, StakeholderAgent


def _short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


class SimulationLoopService:
    def run_rounds(
        self,
        agents: Iterable[StakeholderAgent],
        scenario_theme: str,
        rounds: int = 3,
        existing_rounds: Iterable[SimulationRound] | None = None,
    ) -> List[SimulationRound]:
        """Run or resume a traceable stakeholder simulation."""
        existing = list(existing_rounds or [])
        round_list = existing[:]
        start = len(existing) + 1
        total_rounds = max(rounds, len(existing))
        agent_list = list(agents)[:10]

        for round_number in range(start, total_rounds + 1):
            actions: List[SimulationAction] = []
            for agent in agent_list:
                action_text = self._select_action(agent, round_number, scenario_theme)
                facts = agent.known_facts[:2]
                citations: List[SourceCitation] = []
                for fact in facts:
                    citations.extend(fact.citations[:1])
                if not citations and facts:
                    citations = facts[0].citations

                action = SimulationAction(
                    action_id=f"act_{round_number:03d}_{agent.agent_id}_{_short_hash(action_text)}",
                    agent_id=agent.agent_id,
                    action=action_text,
                    reasoning_summary=self._reasoning(agent, facts, scenario_theme),
                    cited_evidence=citations,
                    changed_assumptions=self._changed_assumptions(agent, round_number),
                    emerging_risks=self._emerging_risks(agent, round_number),
                )
                actions.append(action)

            round_summary = self._summarize_round(round_number, scenario_theme, actions)
            round_list.append(
                SimulationRound(
                    round_id=f"round_{round_number:03d}",
                    round_number=round_number,
                    scenario_theme=scenario_theme,
                    actions=actions,
                    summary=round_summary,
                    citations=[c for action in actions for c in action.cited_evidence[:1]][:10],
                )
            )
        return round_list

    def _select_action(self, agent: StakeholderAgent, round_number: int, scenario_theme: str) -> str:
        if not agent.likely_actions:
            return f"{agent.name} monitors the scenario and waits for more evidence."
        action = agent.likely_actions[(round_number - 1) % len(agent.likely_actions)]
        if round_number == 1:
            return f"{agent.name} begins by trying to {action} around '{scenario_theme}'."
        if round_number == 2:
            return f"{agent.name} escalates and tries to {action} as second-order reactions appear."
        return f"{agent.name} adjusts its position and tries to {action} while preserving optionality."

    def _reasoning(self, agent: StakeholderAgent, facts, scenario_theme: str) -> str:
        if not facts:
            return f"{agent.name} acts from its role incentives because the evidence base is thin."
        fact_text = facts[0].text[:180]
        return (
            f"{agent.name} weighs {agent.type} goals against '{scenario_theme}'. "
            f"The strongest cited fact is: {fact_text}"
        )

    def _changed_assumptions(self, agent: StakeholderAgent, round_number: int) -> List[str]:
        if round_number == 1:
            return [f"{agent.name} assumes stakeholders are still seeking negotiated outcomes."]
        if round_number == 2:
            return [f"{agent.name} updates toward faster coordination among high-exposure parties."]
        return [f"{agent.name} treats unresolved uncertainty as a source of bargaining leverage."]

    def _emerging_risks(self, agent: StakeholderAgent, round_number: int) -> List[str]:
        risks = {
            "low": "process delay",
            "medium": "confidence erosion",
            "high": "narrative acceleration",
        }
        return [f"{risks.get(agent.risk_tolerance, 'execution risk')} could intensify after round {round_number}."]

    def _summarize_round(self, round_number: int, scenario_theme: str, actions: List[SimulationAction]) -> str:
        active_agents = ", ".join(action.agent_id for action in actions[:4])
        return (
            f"Round {round_number} for '{scenario_theme}' produced {len(actions)} stakeholder moves. "
            f"Early pressure came from {active_agents}; risks concentrate around coordination speed, "
            "liquidity of trust, and unresolved source uncertainty."
        )
