"""Executive decision memo generation with explicit evidence provenance."""

from __future__ import annotations

from typing import List

from .decision import build_decision_completion, is_executable_action_label
from .execution import DecisionExecutionCompiler
from .schemas import ForecastReport, SourceCitation, V2RunState


class ForecastReportService:
    """Generate an interim or final decision memo from the current case state."""

    def __init__(self) -> None:
        self.execution = DecisionExecutionCompiler()

    def generate(self, state: V2RunState) -> ForecastReport:
        state.execution_plan = self.execution.compile(state)
        citations = self._collect_citations(state)
        completion = build_decision_completion(state)
        state.decision_completion = completion
        state.workflow_stage = completion["stage"]
        evidence_complete = completion["internal_evidence_complete"]
        status = "final" if completion["final_approval_ready"] else (
            "blocked" if evidence_complete else "interim"
        )
        recommendation = self._recommendation(state, completion)
        stop_reason = (
            state.stop_evaluation.reason
            if state.stop_evaluation
            else "Continue: stop evaluation has not run."
        )
        if evidence_complete:
            stop_reason = stop_reason.replace("Stop:", "Internal fact collection complete:", 1)

        md: List[str] = [
            f"# {state.project_name} Executive Decision Report",
            "",
            f"**Memo status:** {status.title()}",
            "",
            "## 1. Decision Status and Recommendation",
            recommendation,
            "",
            "## 1A. Decision Execution Plan",
            *self._execution_plan_lines(state),
            "",
            "## 2. Deterministic Decision-Analysis Result",
            *self._decision_analysis_lines(state),
            "",
            "## 3. Differences and Reasons",
            *self._decision_difference_lines(state, recommendation),
            "",
            "## 4. Missing Human Confirmations",
            *self._missing_confirmation_lines(state),
            "",
            "## 5. Information Priorities by EVPPI",
            *self._information_priority_lines(state),
            "",
            "## 6. Legacy Question Priority Score (Heuristic)",
            *self._question_priority_lines(state),
            "",
            "## Decision",
            state.question or "No decision question was provided.",
            "",
            "## External Evidence Used and Provenance",
            (
                "The report keeps initial FOREFOLD simulation findings, preserved source citations, "
                "generated interpretations, and confidential internal facts distinct. Relative support scores are "
                "decision aids, not probabilities."
            ),
        ]

        for claim in state.claims[:18]:
            if claim.kind in {"simulation_derived_fact", "simulated_stakeholder_reaction"}:
                provenance = "simulated stakeholder reaction — not a verified fact or direct quotation"
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

        md.extend(["", "## FOREFOLD Interpretations and Assumptions"])
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
                f"- **#{question.rank} / Question Priority {question.question_priority_score:.1f} / {question.status}:** "
                f"{question.question} Owner: {question.owner_hint}. Why it matters: {question.rationale}"
            )
            if question.answer_id and question.answer_id in evidence_by_id:
                evidence = evidence_by_id[question.answer_id]
                confidentiality = "confidential " if evidence.confidential else ""
                line += (
                    f" A {confidentiality}internal answer was recorded and interpreted as "
                    f"**{evidence.interpretation}**; raw text is not duplicated into this report."
                )
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
                f"- Remaining private uncertainty (Question Priority {question.question_priority_score:.1f}): {question.question}"
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
            "- The completed FOREFOLD simulation report is reused as the evidence base; this refinement stage does not launch another public research process.",
            "- Confidential internal answers remain local and are used only for bounded branch updates.",
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
            "- Question Priority Score only decides which bounded internal question is shown first; it is not probability, utility, EVPI, EVPPI, or EVSI.",
            "- EVPPI estimates the maximum decision value of perfectly resolving one approved variable; net information value subtracts confirmed acquisition and delay costs.",
            "- EVSI is unavailable because this version has no approved sampling or likelihood model for what an information source could report conditional on the true state.",
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

    def _execution_plan_lines(self, state: V2RunState) -> List[str]:
        plan = state.execution_plan
        if not plan or not plan.actions:
            return ["- No executable plan can be compiled until a management action exists."]
        score = plan.executability.get("score", 0)
        lines = [
            f"- **Executability:** {score:.0f}/100 — {'decision-ready' if plan.ready else 'gaps remain'}.",
            f"- **Evidence-to-action coverage:** {plan.coverage.get('coverage_percent', 0):.0f}% of high-clarity binding facts operationalized.",
        ]
        for action in plan.actions:
            lines.extend([
                "",
                f"### {action.action_id} · {action.action_type} · {action.stage}",
                f"**{action.title}**",
                f"- **Purpose:** {action.purpose}",
                f"- **Owner:** {action.owner}; accountable executive: {action.accountable_executive}.",
                f"- **Deliverable:** {action.deliverable}",
                f"- **Timing:** Start when {action.start_condition}; due {action.deadline}.",
                f"- **Resource boundary:** {action.budget_or_capacity}",
                "- **Acceptance criteria:**",
                *[f"  - {item}" for item in action.acceptance_criteria],
                f"- **Failure response:** {action.failure_response}",
                "- **Why this exists:** " + (
                    ", ".join(f"`{item}`" for item in action.evidence_source_ids)
                    if action.evidence_source_ids else "required execution contract"
                ),
            ])
        failures = plan.executability.get("hard_failures") or []
        if failures:
            lines.extend(["", "### Execution gaps that block decision-ready status"])
            lines.extend(f"- {item}" for item in failures)
        return lines

    def _decision_analysis_lines(self, state: V2RunState) -> List[str]:
        analysis = state.decision_analysis_result or {}
        if analysis.get("status") != "calculated":
            if (state.decision_completion or {}).get("decision_model_waived"):
                waiver = state.decision_analysis_waiver or {}
                return [
                    "- **Decision method:** Evidence-backed qualitative judgment, explicitly approved by the decision owner.",
                    "- No expected-utility, probability, EVPI, or EVPPI claim is made.",
                    f"- **Approved by:** {waiver.get('confirmed_by') or 'Decision owner'}.",
                ]
            return [
                "Decision analysis unavailable until actions, consequences, utilities, and distributions are confirmed."
            ]

        lines = [
            f"- **Recommended action:** `{analysis.get('recommended_action')}`",
            (
                f"- **Method:** `{analysis.get('method')}`; engine "
                f"`{analysis.get('calculation_engine_version')}`; model hash "
                f"`{analysis.get('model_hash')}`; seed `{analysis.get('seed')}`; "
                f"sample count `{analysis.get('sample_count')}`."
            ),
            f"- **EVPI:** {self._metric(analysis.get('evpi'))}",
        ]
        expected_utilities = analysis.get("expected_utility_by_action") or {}
        expected_regrets = analysis.get("expected_regret_by_action") or {}
        for action_id in sorted(expected_utilities):
            lines.append(
                f"- `{action_id}` — expected utility "
                f"{self._metric(expected_utilities[action_id])}; expected regret "
                f"{self._metric(expected_regrets.get(action_id))}."
            )
        warnings = analysis.get("warnings") or []
        for warning in warnings:
            lines.append(f"- **Calculation warning:** {warning}")
        return lines

    def _decision_difference_lines(
        self,
        state: V2RunState,
        qualitative_recommendation: str,
    ) -> List[str]:
        analysis = state.decision_analysis_result or {}
        if analysis.get("status") != "calculated":
            if (state.decision_completion or {}).get("decision_model_waived"):
                return [
                    "- The decision owner explicitly selected the qualitative method; no numeric comparison is claimed.",
                    f"- **Approved qualitative result:** {qualitative_recommendation}",
                ]
            return [
                "- No numeric comparison is claimed. The qualitative recommendation remains visible in shadow mode while the explicit decision model awaits confirmation."
            ]
        return [
            f"- **Qualitative result:** {qualitative_recommendation}",
            f"- **Deterministic result:** `{analysis.get('recommended_action')}`.",
            (
                "- The qualitative path uses cited evidence, assumptions, and relative branch-support heuristics. "
                "The deterministic path uses only human-confirmed actions, probability distributions, "
                "consequences, and a risk-neutral utility model. Neither numeric system is substituted for the other."
            ),
            "- Shadow mode is active: the deterministic result is displayed beside, and does not silently replace, the qualitative recommendation.",
        ]

    def _missing_confirmation_lines(self, state: V2RunState) -> List[str]:
        completion = state.decision_completion or build_decision_completion(state)
        if completion.get("decision_model_waived"):
            return [
                "- None. Management confirmed the action set and explicitly approved the qualitative decision method."
            ]
        lines: List[str] = []
        if not completion.get("actions_confirmed"):
            lines.append("- Confirm that every scored path is a real management action considered in the decision.")
        if (
            completion.get("decision_model_complete")
            and not completion.get("decision_model_actions_aligned")
        ):
            lines.append(
                "- Align the calculated model actions with the confirmed management action set."
            )
        if state.decision_model:
            if not lines:
                return ["- None. The stored decision model records explicit human approval metadata."]
            return lines
        prefix = "Confirm" if state.decision_model_proposal else "Propose and confirm"
        lines.extend([
            f"- {prefix} every action that is actually available.",
            f"- {prefix} the common consequence and utility unit.",
            f"- {prefix} every uncertain variable and probability distribution.",
            f"- {prefix} the payoff definitions and risk-neutral utility model.",
        ])
        return lines

    def _information_priority_lines(self, state: V2RunState) -> List[str]:
        analysis = state.decision_analysis_result or {}
        priorities = analysis.get("evppi_by_variable") or {}
        if analysis.get("status") != "calculated" or not priorities:
            if (state.decision_completion or {}).get("decision_model_waived"):
                return [
                    "- Not calculated. The approved qualitative method makes no numeric value-of-information claim."
                ]
            return [
                "- EVPPI is unavailable until a complete human-confirmed decision model is calculated."
            ]
        costs = analysis.get("information_costs") or {}
        net_values = analysis.get("net_information_value_by_variable") or {}
        lines = []
        for variable_id, evppi in sorted(
            priorities.items(), key=lambda item: (-float(item[1]), item[0])
        ):
            cost = costs.get(variable_id) or {}
            lines.append(
                f"- `{variable_id}` — EVPPI {self._metric(evppi)}; confirmed total information cost "
                f"{self._metric(cost.get('total_cost', 0.0))}; net information value "
                f"{self._metric(net_values.get(variable_id))}."
            )
        return lines

    def _question_priority_lines(self, state: V2RunState) -> List[str]:
        lines = [
            "- This legacy score ranks which of at most four material internal questions appears first. It does not participate in probability, expected utility, regret, EVPI, or EVPPI calculations.",
            "- Formula: `100 × (0.40 sensitivity + 0.30 uncertainty + 0.20 answerability + 0.10 urgency)`.",
        ]
        for question in sorted(
            state.internal_questions,
            key=lambda item: (-item.question_priority_score, item.question_id),
        ):
            lines.append(
                f"- **{question.question_priority_score:.1f} / {question.status}:** {question.question}"
            )
        if not state.internal_questions:
            lines.append("- No bounded internal question is currently material.")
        return lines

    @staticmethod
    def _metric(value) -> str:
        if isinstance(value, (int, float)):
            return f"{float(value):.6g}"
        return "unavailable"

    def _recommendation(self, state: V2RunState, completion: dict) -> str:
        if not state.hypotheses:
            return "No recommendation is available because no decision path could be generated."
        invalid = [
            item.label for item in state.hypotheses
            if not is_executable_action_label(item.label)
        ]
        if invalid:
            return (
                "Decision blocked: imported simulation signals were rejected because they are not "
                "executable management actions. Reconstruct and confirm the available actions before scoring."
            )
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
        if not completion.get("internal_evidence_complete"):
            return (
                f"Working direction: **{leader.label}**. Internal fact collection is still in progress; "
                "do not treat this as an approval recommendation."
            )
        if not completion.get("actions_confirmed"):
            return (
                "Evidence refinement complete; decision blocked pending management confirmation of the "
                f"considered actions. Current leading action signal: **{leader.label}**."
            )
        if not completion.get("decision_model_complete"):
            return (
                "Actions confirmed; decision blocked until consequences, uncertainty distributions, and "
                "the utility model are confirmed and calculated."
            )
        if not completion.get("decision_model_actions_aligned"):
            return (
                "Decision blocked: the calculated model actions do not match the confirmed management "
                "action set. Align and reconfirm the model before releasing a recommendation."
            )
        if not completion.get("critical_conflicts_resolved"):
            return "Decision blocked until the remaining high-severity evidence conflict is resolved."

        if completion.get("decision_model_waived"):
            return f"Recommend **{leader.label}** for: {state.question}"

        analysis_action_id = (state.decision_analysis_result or {}).get("recommended_action")
        approved_actions = (state.decision_model or {}).get("actions") or []
        approved_label = next(
            (
                item.get("label")
                for item in approved_actions
                if item.get("id") == analysis_action_id
            ),
            analysis_action_id,
        )
        if approved_label:
            return f"Recommend **{approved_label}** for: {state.question}"
        return (
            "Decision analysis completed without a resolvable approved action label; approval remains blocked."
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
