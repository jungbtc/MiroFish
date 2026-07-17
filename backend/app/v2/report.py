"""Executive decision memo generation with explicit evidence provenance."""

from __future__ import annotations

from typing import List

from .schemas import ForecastReport, SourceCitation, V2RunState


class ForecastReportService:
    """Generate an interim or final decision memo from the current case state."""

    def generate(self, state: V2RunState) -> ForecastReport:
        citations = self._collect_citations(state)
        stopped = bool(state.stop_evaluation and state.stop_evaluation.should_stop)
        status = "final" if stopped else "interim"
        recommendation = self._recommendation(state, stopped)
        stop_reason = (
            state.stop_evaluation.reason
            if state.stop_evaluation
            else "Continue: stop evaluation has not run."
        )

        md: List[str] = [
            f"# {state.project_name} Executive Decision Report",
            "",
            f"**Memo status:** {status.title()}",
            "",
            "## Executive Recommendation",
            recommendation,
            "",
            "## Decision",
            state.question or "No decision question was provided.",
            "",
            "## External Evidence Used and Provenance",
            (
                "The report keeps three evidence classes distinct: initial MiroFish simulation findings, "
                "cited external research, and confidential internal facts. Relative support scores are "
                "decision aids, not probabilities."
            ),
        ]

        for claim in state.claims[:18]:
            if claim.kind == "simulation_derived_fact":
                provenance = "initial simulation finding"
            elif claim.kind == "external_researched_fact":
                provenance = (
                    "cited external research"
                    if claim.citations
                    else "external research synthesis / report anchor"
                )
            else:
                provenance = "extracted evidence"
            md.append(f"- **{provenance}:** {claim.text} {self._cite(claim.citations)}".rstrip())
        if len(state.claims) > 18:
            md.append(
                f"- Executive view shows 18 of {len(state.claims)} extracted claims; "
                "the complete claim and provenance inventory remains in the case graph and artifacts."
            )
        if not state.claims:
            md.append("- No claim could be extracted from the imported report.")

        md.extend(["", "## MiroFish Interpretations and Assumptions"])
        for assumption in state.assumptions:
            md.append(
                f"- **Generated interpretation — {assumption.category.replace('_', ' ')} "
                f"({assumption.status}):** {assumption.text}"
            )
        if not state.assumptions:
            md.append("- No generated assumptions are recorded.")

        md.extend(["", "## Competing Decision Paths"])
        for hypothesis in sorted(state.hypotheses, key=lambda item: item.support_score, reverse=True):
            md.append(
                f"- **{hypothesis.label} — {hypothesis.status} — {hypothesis.support_score:.0%} relative support:** "
                f"{hypothesis.description} {hypothesis.rationale}"
            )
        if not state.hypotheses:
            md.append("- No competing paths are recorded.")

        md.extend(["", "## Decision-Critical Internal Facts Requested"])
        evidence_by_id = {item.evidence_id: item for item in state.internal_evidence}
        for question in sorted(state.internal_questions, key=lambda item: item.rank):
            line = (
                f"- **#{question.rank} / IVS {question.information_value_score:.1f} / {question.status}:** "
                f"{question.question} Owner: {question.owner_hint}. Why it matters: {question.rationale}"
            )
            if question.answer_id and question.answer_id in evidence_by_id:
                evidence = evidence_by_id[question.answer_id]
                if evidence.confidential:
                    line += (
                        f" Answer recorded as confidential and interpreted as **{evidence.interpretation}**; "
                        "raw text remains in the local case only."
                    )
                else:
                    line += f" Answer: {evidence.answer} (interpreted as **{evidence.interpretation}**)."
            md.append(line)

        md.extend(["", "## How Internal Evidence Changed the Decision"])
        for impact in state.decision_impacts:
            md.append(f"### {impact.impact_id}")
            md.append(impact.summary)
            for change in impact.hypothesis_changes:
                sign = "+" if change.delta >= 0 else ""
                md.append(
                    f"- `{change.hypothesis_id}`: {change.before_score:.0%} → {change.after_score:.0%} "
                    f"({sign}{change.delta:.0%}); {change.before_status} → {change.after_status}. {change.explanation}"
                )
        if not state.decision_impacts:
            md.append("- No internal answer has changed the decision graph yet.")

        md.extend(["", "## Targeted Re-evaluation Record"])
        for reevaluation in state.targeted_reevaluations:
            affected = ", ".join(reevaluation.affected_hypothesis_ids) or "no material branch"
            md.append(
                f"- **{reevaluation.status} / {reevaluation.mode}:** affected {affected}. "
                f"{reevaluation.rationale}"
            )
        if not state.targeted_reevaluations:
            md.append("- No private fact has triggered targeted scenario re-evaluation yet.")

        md.extend(["", "## Alternatives Rejected or Weakened"])
        rejected = [item for item in state.hypotheses if item.status in {"pruned", "weakened", "unsupported"}]
        for hypothesis in rejected:
            reason = hypothesis.prune_reason or hypothesis.rationale
            md.append(f"- **{hypothesis.label} ({hypothesis.status}):** {reason}")
        if not rejected:
            md.append("- No alternative has been pruned yet; the decision is still information-sensitive.")

        md.extend(["", "## Contradictions and Remaining Uncertainty"])
        for contradiction in state.contradictions:
            md.append(
                f"- **{contradiction.severity} / {contradiction.status}:** {contradiction.summary} "
                f"{self._cite(contradiction.citations)}".rstrip()
            )
        unanswered = [
            item
            for item in state.internal_questions
            if item.status in {"pending", "requested", "deferred"}
        ]
        for question in unanswered:
            md.append(
                f"- Remaining private uncertainty (IVS {question.information_value_score:.1f}): {question.question}"
            )
        if not state.contradictions and not unanswered:
            md.append("- No open contradiction or ranked internal question remains.")

        md.extend([
            "",
            "## Continue-or-Stop Evaluation",
            stop_reason,
            "",
            "## Token and Privacy Boundary",
            (
                f"- Processing mode: `{state.token_usage.processing_mode}`. External model calls: "
                f"{state.token_usage.external_llm_calls}. Total incremental model tokens: "
                f"{state.token_usage.total_tokens}."
            ),
            "- OpenAI Deep Research runs through the Responses API with a public web-search tool and preserves source citations.",
            "- Deep Research receives only the initial public/simulation context. Confidential internal answers are never sent to web search.",
            "- Private facts use deterministic local interpretation unless model-backed interpretation is explicitly enabled with consent.",
            "",
            "## Audit Trail",
        ])
        for event in state.audit_trail:
            md.append(f"- `{event.event_id}` / **{event.event_type}** / {event.created_at}: {event.summary}")

        md.extend(["", "## Preserved Sources"])
        direct_sources = [citation for citation in citations if citation.url]
        preserved_without_url = [
            citation
            for citation in citations
            if not citation.url
            and (
                citation.source_type == "external_source"
                or citation.provenance_status == "preserved_from_import"
            )
        ]
        report_anchors = [
            citation
            for citation in citations
            if not citation.url and citation not in preserved_without_url
        ]
        for citation in direct_sources:
            label = citation.label or citation.url or citation.source_id
            md.append(f"- [{label}]({citation.url})")
        for citation in preserved_without_url:
            label = citation.label or citation.original_source_id or citation.source_id
            md.append(
                f"- **Preserved cited source without a URL:** {label}. "
                "Its imported source identity and supporting quote remain in the case graph."
            )
        if report_anchors:
            md.append(
                f"- {len(report_anchors)} report chunk anchor(s) are retained in the case for traceability; "
                "they are not presented as external URLs."
            )
        if not citations:
            md.append("- The imported report supplied no resolvable citations.")

        md.extend([
            "",
            "## Method Note",
            "- Information Value Score is an explainable prioritization heuristic, not rigorous EVPI.",
            "- Branch support scores are relative decision support, not calibrated probabilities.",
            "- Generated interpretations are explicitly labelled and never converted into fake external citations.",
        ])

        return ForecastReport(
            report_id=f"memo_{state.run_id}",
            title=f"{state.project_name} Executive Decision Report",
            markdown="\n".join(md) + "\n",
            citations=citations,
            status=status,
            recommendation=recommendation,
            stop_reason=stop_reason,
        )

    def _recommendation(self, state: V2RunState, stopped: bool) -> str:
        if not state.hypotheses:
            return "No recommendation is available because no decision path could be generated."
        ranked = sorted(
            (item for item in state.hypotheses if item.status != "pruned"),
            key=lambda item: item.support_score,
            reverse=True,
        )
        if not ranked:
            return "No recommendation is available because every decision path is explicitly disqualified."
        leader = ranked[0]
        if len(ranked) > 1 and leader.support_score - ranked[1].support_score <= 0.015:
            tied = [
                item.label
                for item in ranked
                if leader.support_score - item.support_score <= 0.015
            ]
            labels = (
                tied[0]
                if len(tied) == 1
                else f"{', '.join(tied[:-1])} and {tied[-1]}"
            )
            return (
                f"No unique evidence-backed recommendation yet: **{labels}** remain effectively tied. "
                "Record a branch-specific internal fact or make the residual trade-off explicit."
            )
        if stopped:
            return f"Recommend **{leader.label}** for: {state.question}"
        return (
            f"Working recommendation: **{leader.label}**. This is not final because at least one "
            "decision-critical internal fact could still materially change the path."
        )

    def _collect_citations(self, state: V2RunState) -> List[SourceCitation]:
        seen = set()
        result: List[SourceCitation] = []
        for document in state.documents:
            for citation in document.imported_citations:
                key = citation.citation_id or (
                    citation.source_id,
                    citation.chunk_id,
                    citation.url,
                    citation.quote,
                    citation.original_marker,
                    citation.page_number,
                )
                if key not in seen:
                    seen.add(key)
                    result.append(citation)
        for claim in state.claims:
            for citation in claim.citations:
                key = citation.citation_id or (
                    citation.source_id,
                    citation.chunk_id,
                    citation.url,
                    citation.quote,
                    citation.original_marker,
                    citation.page_number,
                )
                if key not in seen:
                    seen.add(key)
                    result.append(citation)
        return result

    def _cite(self, citations: List[SourceCitation]) -> str:
        if not citations:
            return ""
        rendered = []
        for citation in citations[:3]:
            label = citation.label or f"{citation.source_id}:{citation.chunk_id or 'source'}"
            if citation.url:
                rendered.append(f"[{label}]({citation.url})")
            elif (
                citation.source_type == "external_source"
                or citation.provenance_status == "preserved_from_import"
            ):
                rendered.append(f"[preserved source without URL: {label}]")
            else:
                rendered.append(f"[report anchor: {label}]")
        if len(citations) > 3:
            rendered.append(f"[+{len(citations) - 3} additional preserved source(s)]")
        return " ".join(rendered)
