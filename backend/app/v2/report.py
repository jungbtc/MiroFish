"""Cited Markdown report generation for MiroFish v2."""

from __future__ import annotations

from typing import List

from .schemas import ForecastReport, SourceCitation, V2RunState


class ForecastReportService:
    def generate(self, state: V2RunState) -> ForecastReport:
        citations = self._collect_citations(state)
        md: List[str] = [
            f"# {state.project_name} Forecast",
            "",
            "## Executive Summary",
            self._executive_summary(state),
            "",
            "## Input Research Summary",
            f"- Documents: {len(state.documents)}",
            f"- Source chunks: {sum(len(doc.chunks) for doc in state.documents)}",
            f"- Extracted claims: {len(state.claims)}",
            f"- Extracted events: {len(state.events)}",
            "",
            "## Key Entities",
        ]

        for entity in state.entities[:12]:
            cite = self._cite(entity.citations)
            md.append(f"- **{entity.name}** ({entity.type}) {cite}".rstrip())

        md.extend(["", "## Stakeholder Map"])
        for agent in state.agents[:12]:
            facts = ", ".join(claim.claim_id for claim in agent.known_facts[:2]) or "no direct claim"
            md.append(f"- **{agent.name}** / {agent.type}: likely actions include {', '.join(agent.likely_actions[:2])}. Evidence: {facts}")

        md.extend(["", "## Simulation Timeline"])
        for round_state in state.rounds:
            md.append(f"### Round {round_state.round_number}")
            md.append(f"{round_state.summary} {self._cite(round_state.citations)}".rstrip())
            for action in round_state.actions[:5]:
                md.append(f"- {action.action} {self._cite(action.cited_evidence)}".rstrip())

        md.extend([
            "",
            "## Scenario Table",
            "| Scenario | Probability | Confidence | Key Drivers |",
            "| --- | ---: | ---: | --- |",
        ])
        for score in state.scores:
            md.append(
                f"| {score.name} | {score.probability:.0%} | {score.confidence:.0%} | "
                f"{', '.join(score.key_drivers[:4])} |"
            )

        md.extend(["", "## Score Derivations"])
        for score in state.scores:
            md.append(f"- **{score.name}:** {score.derivation}")

        md.extend(["", "## Key Evidence"])
        for claim in state.claims[:15]:
            md.append(f"- {claim.text} {self._cite(claim.citations)}".rstrip())

        md.extend([
            "",
            "## Citations",
        ])
        for citation in citations[:40]:
            label = citation.label or f"{citation.source_id}:{citation.chunk_id or 'source'}"
            quote = f" - {citation.quote}" if citation.quote else ""
            md.append(f"- `{label}`{quote}")

        md.extend([
            "",
            "## Limitations",
            "- Probabilities are subjective scenario scores derived from available evidence and simulated behavior.",
            "- Uploaded sources may be incomplete, stale, biased, or missing private negotiations.",
            "- The fallback extractor is heuristic. Configure an LLM-backed extractor later for richer extraction.",
            "",
            "## Follow-Up Questions",
            "- Which stakeholder has the most leverage?",
            "- What evidence most supports the downside case?",
            "- What would change the base case probability?",
        ])

        return ForecastReport(
            report_id=f"report_{state.run_id}",
            title=f"{state.project_name} Forecast",
            markdown="\n".join(md) + "\n",
            citations=citations,
        )

    def _executive_summary(self, state: V2RunState) -> str:
        top_score = state.scores[0] if state.scores else None
        top_entities = ", ".join(entity.name for entity in state.entities[:4]) or "the uploaded stakeholders"
        if not top_score:
            return f"MiroFish analyzed {top_entities}, but no scenario scores are available yet."
        return (
            f"MiroFish analyzed {top_entities} and generated {len(state.rounds)} simulation rounds. "
            f"The central scenario is **{top_score.name}** at {top_score.probability:.0%} subjective probability "
            f"with {top_score.confidence:.0%} confidence."
        )

    def _collect_citations(self, state: V2RunState) -> List[SourceCitation]:
        seen = set()
        result: List[SourceCitation] = []
        for claim in state.claims:
            for citation in claim.citations:
                key = (citation.source_id, citation.chunk_id, citation.quote)
                if key in seen:
                    continue
                seen.add(key)
                result.append(citation)
        for round_state in state.rounds:
            for citation in round_state.citations:
                key = (citation.source_id, citation.chunk_id, citation.quote)
                if key not in seen:
                    seen.add(key)
                    result.append(citation)
        return result

    def _cite(self, citations: List[SourceCitation]) -> str:
        if not citations:
            return ""
        labels = [c.label or f"{c.source_id}:{c.chunk_id or 'source'}" for c in citations[:2]]
        return " ".join(f"[{label}]" for label in labels)
