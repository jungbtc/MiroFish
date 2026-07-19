import json
import re
from pathlib import Path

import pytest

from app import create_app
from app.v2.decision import (
    EVIDENCE_RULE_VERSION,
    QUESTION_PRIORITY_FORMULA,
    DecisionIntelligenceService,
    is_executable_action_label,
)
from app.v2.extraction import ExtractionService
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.research_ingestion import ResearchIngestionService
from app.v2.schemas import InternalEvidence
from app.v2.storage import V2Storage
from decision_analysis_fixtures import binary_decision_model


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "test_inputs" / "v2_demo"
CITED_REPORT = FIXTURE_DIR / "cited_deep_research_report.md"
STRUCTURED_REPORT = FIXTURE_DIR / "structured_deep_research_report.json"
DECISION_QUESTION = "Should Northstar restructure now or stage a reversible pilot?"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_runs")
    return MiroFishV2Pipeline()


def run_cited_case(pipeline: MiroFishV2Pipeline):
    public_state = pipeline.run_from_paths(
        [CITED_REPORT],
        question=DECISION_QUESTION,
        project_name="Northstar Decision Verification",
    )
    return pipeline.fork_public_run(public_state.run_id)


ACTIONABLE_ANSWERS = {
    "strategic_success": (
        "The minimum success threshold is 10% revenue growth within 12 months.",
        "mixed",
    ),
    "constraints": (
        "Legal review confirmed that there are no legal blockers or policy constraints.",
        "favorable",
    ),
    "financial_capacity": (
        "Finance approved a $14.7 million budget, and the funding is sufficient within the downside limit.",
        "favorable",
    ),
    "execution_capacity": (
        "The operating owner is named, with 8 committed staff and sufficient delivery capacity.",
        "favorable",
    ),
    "risk_tolerance": (
        "The maximum acceptable downside loss is $2 million.",
        "mixed",
    ),
    "timing": (
        "The decision deadline is 2026-09-30 and dependencies are cleared for an October start.",
        "mixed",
    ),
}


def submit_favorable_requested_answer(pipeline: MiroFishV2Pipeline, state, index: int):
    requested = [question for question in state.internal_questions if question.status == "requested"]
    assert len(requested) == 1
    answer, interpretation = ACTIONABLE_ANSWERS[requested[0].category]
    return pipeline.submit_internal_answer(
        state.run_id,
        requested[0].question_id,
        f"Internal verification {index}: {answer}",
        submitted_by="verification-owner",
        confidential=True,
        confidence=1.0,
        interpretation=interpretation,
    )


def advance_to_stop(pipeline: MiroFishV2Pipeline, state):
    for index in range(1, len(state.internal_questions) + 1):
        if state.stop_evaluation and state.stop_evaluation.should_stop:
            break
        state = submit_favorable_requested_answer(pipeline, state, index)
    assert state.stop_evaluation is not None
    assert state.stop_evaluation.should_stop is True
    return state


def test_starbucks_prompt_extracts_management_actions_not_stakeholders():
    decision = (
        "Evaluate Starbucks Priority Pass for non-members, baristas, and store managers. "
        "Determine whether momentum builds toward national rollout, limited pilot, "
        "redesign, or cancellation."
    )

    options = DecisionIntelligenceService()._infer_decision_options(decision)

    assert options == [
        ("Proceed to a national rollout", "immediate"),
        ("Run a smaller, controlled pilot", "staged"),
        ("Redesign the benefit and operating model before launch", "redesign"),
        ("Cancel or postpone the initiative", "defer"),
    ]
    assert all(is_executable_action_label(label) for label, _role in options)
    assert is_executable_action_label("Recommend Store managers") is False
    assert is_executable_action_label("Select baristas") is False
    assert not any(
        stakeholder in label.lower()
        for label, _role in options
        for stakeholder in ("non-members", "baristas", "store managers")
    )
    relevant, _reason = DecisionIntelligenceService()._answer_relevance(
        "The pilot must improve paid conversion by at least 8% without increasing non-member churn above 2%.",
        "strategic_success",
    )
    assert relevant is True
    constraint_relevant, _reason = DecisionIntelligenceService()._answer_relevance(
        "Legal and Labor Relations will not approve a national rollout until a 50-store pilot completes review; a controlled pilot is permitted only if safeguards are protected.",
        "constraints",
    )
    assert constraint_relevant is True


def test_saved_constraint_answer_is_reassessed_and_applied_after_rule_upgrade(pipeline):
    decision = (
        "Starbucks announces an $8-per-month Priority Pass at 500 US stores. "
        "Determine whether momentum builds toward national rollout, limited pilot, "
        "redesign, or cancellation."
    )
    public = pipeline.run_from_inline_documents(
        [{"filename": "starbucks.md", "text": "A pilot may contain labor and service-time risk."}],
        question=decision,
        project_name="Starbucks Priority Pass demo",
    )
    state = pipeline.fork_public_run(public.run_id)
    constraint = next(
        item for item in state.internal_questions if item.category == "constraints"
    )
    for question in state.internal_questions:
        if question.status == "requested":
            question.status = "pending"
    constraint.status = "requested"
    evidence = InternalEvidence(
        evidence_id="internal_legacy_constraint_answer",
        question_id=constraint.question_id,
        answer=(
            "Legal and Labor Relations will not approve a national rollout until a "
            "50-store pilot completes review. A controlled pilot is permitted only if "
            "service-time safeguards are protected and it can be suspended within 24 hours."
        ),
        interpretation="mixed",
        confidence=0.8,
        decision_usable=False,
        question_relevant=False,
        interpretation_method="deterministic_category_rules",
        confidential=True,
    )
    state.internal_evidence.append(evidence)
    V2Storage.save_state(state)

    migrated = pipeline.load_state(state.run_id)

    applied = next(
        item for item in migrated.internal_evidence if item.evidence_id == evidence.evidence_id
    )
    migrated_question = next(
        item for item in migrated.internal_questions if item.question_id == constraint.question_id
    )
    assert applied.decision_usable is True
    assert applied.question_relevant is True
    assert applied.interpretation_method == EVIDENCE_RULE_VERSION
    assert migrated_question.status == "answered"
    assert migrated_question.answer_id == evidence.evidence_id
    assert migrated.decision_impacts[-1].evidence_id == evidence.evidence_id
    changes_by_label = {
        hypothesis.label: change
        for hypothesis, change in zip(
            migrated.hypotheses,
            migrated.decision_impacts[-1].hypothesis_changes,
        )
    }
    assert changes_by_label["Proceed to a national rollout"].delta < 0
    assert changes_by_label["Run a smaller, controlled pilot"].delta > 0
    assert any(
        event.event_type == "retained_evidence_reassessed"
        for event in migrated.audit_trail
    )


def test_starbucks_refinement_moves_actions_semantically_and_stops_before_approval(pipeline):
    decision = (
        "Evaluate Starbucks Priority Pass for non-members, baristas, and store managers. "
        "Determine whether momentum builds toward national rollout, limited pilot, "
        "redesign, or cancellation."
    )
    public = pipeline.run_from_inline_documents(
        [
            {
                "filename": "starbucks.md",
                "text": (
                    "Starbucks is evaluating Priority Pass. A controlled pilot can limit "
                    "exposure while measuring conversion, churn, labor minutes, and pickup time."
                ),
            }
        ],
        question=decision,
        project_name="Starbucks Priority Pass demo",
    )
    state = pipeline.fork_public_run(public.run_id)
    answers = {
        "strategic_success": (
            "The pilot must improve paid conversion by at least 8% without increasing "
            "non-member churn above 2%."
        ),
        "constraints": (
            "Legal and labor review confirmed there are no legal blockers or policy constraints."
        ),
        "financial_capacity": (
            "Finance approved only a $2 million 50-store pilot budget; national rollout "
            "funding is not approved."
        ),
        "execution_capacity": (
            "The operating owner has enough committed staff for 50 stores, but national "
            "rollout capacity is unavailable."
        ),
    }

    financial_changes = None
    while not state.stop_evaluation.should_stop:
        question = next(
            item for item in state.internal_questions if item.status == "requested"
        )
        state = pipeline.submit_internal_answer(
            state.run_id,
            question.question_id,
            answers[question.category],
            confidence=0.95,
        )
        assert state.internal_evidence[-1].decision_usable is True
        if question.category == "financial_capacity":
            financial_changes = {
                next(
                    hypothesis.decision_role
                    for hypothesis in state.hypotheses
                    if hypothesis.hypothesis_id == change.hypothesis_id
                ): change.delta
                for change in state.decision_impacts[-1].hypothesis_changes
            }

    assert len(state.internal_evidence) == 4
    assert financial_changes is not None
    assert financial_changes["immediate"] < 0
    assert financial_changes["staged"] > financial_changes["redesign"] > 0
    assert len(set(financial_changes.values())) == 4
    leader = next(
        item
        for item in state.hypotheses
        if item.hypothesis_id == state.stop_evaluation.leading_hypothesis_id
    )
    assert leader.label == "Run a smaller, controlled pilot"
    assert state.report.status == "blocked"
    assert state.decision_completion["internal_evidence_complete"] is True
    assert state.decision_completion["actions_confirmed"] is False
    assert state.decision_completion["final_approval_ready"] is False

    state = pipeline.confirm_decision_actions(
        state.run_id,
        [item.hypothesis_id for item in state.hypotheses],
        confirmed_by="starbucks-decision-owner",
    )
    qualitative_state = pipeline.waive_quantitative_decision_analysis(
        state.run_id,
        confirmed_by="starbucks-decision-owner",
    )
    assert qualitative_state.decision_completion["decision_model_waived"] is True
    assert qualitative_state.decision_completion["final_approval_ready"] is True
    assert qualitative_state.report.status == "final"
    assert "Run a smaller, controlled pilot" in qualitative_state.report.recommendation

    model = binary_decision_model().model_dump(mode="json")
    model["id"] = "starbucks_priority_pass_decision"
    model["question"] = state.question
    model["actions"] = [
        {"id": item.hypothesis_id, "label": item.label}
        for item in state.hypotheses
    ]
    states = [
        {"demand": demand, "regulatory": regulatory}
        for regulatory in (False, True)
        for demand in ("low", "high")
    ]
    consequences = {
        "immediate": 30.0,
        "staged": 60.0,
        "redesign": 40.0,
        "defer": 10.0,
    }
    model["utility_model"]["outcomes"] = [
        {
            "action_id": item.hypothesis_id,
            "state": scenario,
            "consequence": consequences[item.decision_role],
            "consequence_unit": "utility_points",
        }
        for scenario in states
        for item in state.hypotheses
    ]
    proposal = pipeline.propose_decision_model(
        state.run_id,
        model,
        proposed_by="planning-assistant",
    )["proposal"]
    reproposed = V2Storage.load_state(state.run_id)
    assert reproposed.decision_analysis_waiver is None
    assert reproposed.report.status == "blocked"
    result = pipeline.confirm_decision_model(
        state.run_id,
        {
            "proposal_id": proposal["proposal_id"],
            "confirm_actions": True,
            "confirm_consequence_unit": True,
            "confirm_distributions": True,
            "confirm_utility_model": True,
        },
        seed=0,
        sample_count=10_000,
    )
    final_state = result["state"]

    assert result["analysis"]["status"] == "calculated"
    assert final_state.decision_completion["decision_model_actions_aligned"] is True
    assert final_state.decision_completion["final_approval_ready"] is True
    assert final_state.workflow_stage == "final_approval_ready"
    assert final_state.report.status == "final"
    assert "Run a smaller, controlled pilot" in final_state.report.recommendation


def test_markdown_citations_preserve_external_urls_and_report_anchors(pipeline):
    documents = ResearchIngestionService().ingest_paths([CITED_REPORT])
    assert len(documents) == 1
    document = documents[0]
    assert document.document_format == "md"

    urls = {citation.url for citation in document.imported_citations}
    assert urls == {
        "https://evidence.example/northstar/liquidity-filing",
        "https://evidence.example/northstar/lender-letter",
        "https://evidence.example/research/restructuring-benchmark",
        "https://evidence.example/research/supplier-survey",
        "https://evidence.example/northstar/labor-agreement",
    }
    assert all(citation.source_type == "external_source" for citation in document.imported_citations)
    assert all(citation.provenance_status == "preserved_from_import" for citation in document.imported_citations)

    claims = ExtractionService().extract_claims(documents)
    assert claims
    assert all(claim.kind == "sourced_fact" for claim in claims)
    assert all(claim.is_generated is False for claim in claims)
    assert any(any(citation.url for citation in claim.citations) for claim in claims)
    assert all(any(citation.url is None for citation in claim.citations) for claim in claims)

    state = run_cited_case(pipeline)
    assert any(citation.url for citation in state.report.citations)
    assert any(citation.url is None for citation in state.report.citations)
    assert "[Northstar liquidity filing](https://evidence.example/northstar/liquidity-filing)" in state.report.markdown
    assert "[report anchor:" in state.report.markdown


def test_structured_json_import_retains_sections_claims_and_citations(pipeline):
    documents = ResearchIngestionService().ingest_paths([STRUCTURED_REPORT])
    assert len(documents) == 1
    document = documents[0]
    assert document.document_format == "structured_json"
    assert document.metadata["source_system"] == "OpenAI Deep Research"
    assert "## External opportunity" in document.text
    assert "The market benchmark reported 24% annual demand growth" in document.text

    urls = {citation.url for citation in document.imported_citations}
    assert urls == {
        "https://evidence.example/atlas/market-benchmark",
        "https://evidence.example/atlas/implementation-benchmark",
        "https://evidence.example/atlas/operating-filing",
    }

    state = pipeline.run_from_paths(
        [STRUCTURED_REPORT],
        question="Should Atlas expand now, stage a pilot, or defer?",
        project_name="Atlas Structured Import Verification",
    )
    assert state.documents[0].document_format == "structured_json"
    assert any(
        citation.url == "https://evidence.example/atlas/market-benchmark"
        for claim in state.claims
        for citation in claim.citations
    )


def test_pdf_import_preserves_pages_uri_annotation_and_report_anchor_locator(
    pipeline,
    tmp_path,
):
    import fitz

    pdf_path = tmp_path / "two-page-deep-research.pdf"
    source_url = "https://evidence.example/northstar/pdf-source"
    page_one_text = " ".join(
        [
            "Northstar reported that liquidity declined and debt risk increased during the review period.",
            "The board announced that a staged restructuring could protect supplier continuity while approvals remain open.",
            "The external report said public evidence cannot verify the approved budget or internal risk tolerance.",
        ]
        * 3
    )
    page_two_text = " ".join(
        [
            "The lender committee reported that funded vendor support could improve restructuring execution.",
            "The benchmark said delayed security approval could increase operational risk and reduce available capacity.",
            "Management expects a reversible pilot to preserve options while the decision owner confirms private constraints.",
        ]
        * 3
    )

    pdf = fitz.open()
    first_page = pdf.new_page()
    assert first_page.insert_textbox(fitz.Rect(50, 50, 545, 720), page_one_text, fontsize=10) >= 0
    second_page = pdf.new_page()
    assert second_page.insert_textbox(fitz.Rect(50, 50, 545, 680), page_two_text, fontsize=10) >= 0
    link_rect = fitz.Rect(50, 700, 310, 725)
    second_page.insert_text((50, 716), "Open the preserved source for this page", fontsize=10)
    second_page.insert_link({"kind": fitz.LINK_URI, "from": link_rect, "uri": source_url})
    pdf.save(pdf_path)
    pdf.close()

    pipeline.ingestion = ResearchIngestionService(chunk_size=320, chunk_overlap=0)
    state = pipeline.run_from_paths(
        [pdf_path],
        question="Should Northstar proceed now, stage a pilot, or defer?",
        project_name="PDF Provenance Verification",
    )
    document = state.documents[0]

    assert document.document_format == "pdf"
    assert document.metadata["page_count"] == 2
    assert [span["page_number"] for span in document.metadata["page_spans"]] == [1, 2]
    assert document.metadata["page_spans"][0]["start_char"] == 0
    assert document.metadata["page_spans"][0]["end_char"] < document.metadata["page_spans"][1]["start_char"]
    assert {chunk.page_number for chunk in document.chunks} >= {1, 2}

    preserved = next(citation for citation in document.imported_citations if citation.url == source_url)
    assert preserved.page_number == 2
    assert preserved.source_type == "external_source"
    assert any(
        citation.url == source_url and citation.page_number == 2
        for claim in state.claims
        for citation in claim.citations
    )

    report_anchor = next(
        citation
        for citation in state.report.citations
        if citation.provenance_status == "report_anchor" and citation.page_number == 2
    )
    assert report_anchor.url is None
    assert report_anchor.chunk_id


def test_sourced_facts_and_generated_assumptions_are_explicitly_separated(pipeline):
    state = run_cited_case(pipeline)

    assert state.claims
    assert all((claim.kind, claim.is_generated) == ("sourced_fact", False) for claim in state.claims)
    assert state.assumptions
    assert {assumption.status for assumption in state.assumptions} == {"unresolved"}
    assert all(assumption.rationale for assumption in state.assumptions)
    assert all(not assumption.source_claim_ids for assumption in state.assumptions)

    node_types = {node["type"] for node in state.graph["nodes"]}
    assert {"sourced_fact", "assumption", "hypothesis", "internal_question"} <= node_types
    assert "## External Evidence Used" in state.report.markdown
    assert "## FOREFOLD Interpretations and Assumptions" in state.report.markdown
    assert "Generated interpretation" in state.report.markdown


def test_question_priority_formula_ranking_and_top_question_request(pipeline):
    state = run_cited_case(pipeline)
    questions = state.internal_questions

    assert [question.rank for question in questions] == list(range(1, len(questions) + 1))
    assert [question.question_priority_score for question in questions] == sorted(
        (question.question_priority_score for question in questions), reverse=True
    )
    for question in questions:
        components = question.value_components
        expected = round(
            100
            * (
                0.40 * components.decision_sensitivity
                + 0.30 * components.uncertainty
                + 0.20 * components.answerability
                + 0.10 * components.urgency
            ),
            1,
        )
        assert question.question_priority_score == expected
        assert components.formula == QUESTION_PRIORITY_FORMULA

    requested = [question for question in questions if question.status == "requested"]
    assert requested == [questions[0]]
    assert requested[0].category in {question.category for question in questions}
    assert requested[0].maximum_plausible_swing > 0
    assert (
        f"Modeled maximum branch swing: {requested[0].maximum_plausible_swing:.0%}."
        in requested[0].expected_change
    )
    ranking_event = next(event for event in state.audit_trail if event.event_type == "questions_ranked")
    assert ranking_event.details["top_question_id"] == requested[0].question_id
    assert ranking_event.details["formula"] == QUESTION_PRIORITY_FORMULA


def test_answers_persist_privacy_flags_and_only_explicit_disqualifiers_prune(pipeline):
    state = run_cited_case(pipeline)
    requested = next(question for question in state.internal_questions if question.status == "requested")
    raw_answer = f"Internal verification 1: {ACTIONABLE_ANSWERS[requested.category][0]}"
    state = submit_favorable_requested_answer(pipeline, state, 1)

    persisted = V2Storage.load_state(state.run_id)
    evidence = persisted.internal_evidence[0]
    assert evidence.answer == raw_answer
    assert evidence.submitted_by == "verification-owner"
    assert evidence.confidential is True
    assert evidence.source_type == "internal_user_supplied"
    assert evidence.outbound_external_use is False
    assert persisted.graph["revision"] == 1

    first_changes = persisted.decision_impacts[0].hypothesis_changes
    assert any(change.delta > 0 for change in first_changes)
    assert any(change.delta < 0 for change in first_changes)
    answer_event = next(event for event in persisted.audit_trail if event.event_type == "internal_answer_received")
    assert answer_event.details["raw_answer_logged"] is False
    assert answer_event.details["outbound_external_use"] is False
    assert raw_answer not in json.dumps(answer_event.details)
    assert raw_answer not in json.dumps(persisted.graph)
    assert raw_answer not in json.dumps(
        [event.model_dump(mode="json") for event in persisted.audit_trail]
    )
    assert raw_answer not in persisted.report.markdown
    assert raw_answer not in V2Storage.report_path(persisted.run_id).read_text(encoding="utf-8")
    assert "raw text is not duplicated into this report" in persisted.report.markdown

    state = submit_favorable_requested_answer(pipeline, persisted, 2)
    assert state.graph["revision"] == 2
    assert not any(hypothesis.status == "pruned" for hypothesis in state.hypotheses)

    disqualified = run_cited_case(pipeline)
    constraint_question = next(
        question for question in disqualified.internal_questions if question.status == "requested"
    )
    assert constraint_question.category == "constraints"
    disqualified = pipeline.submit_internal_answer(
        disqualified.run_id,
        constraint_question.question_id,
        "A non-negotiable legal hard blocker prohibits and disqualifies proceeding now.",
        confidence=1.0,
        interpretation="unfavorable",
    )
    assert any(hypothesis.status == "pruned" for hypothesis in disqualified.hypotheses)
    assert any(
        change.after_status == "pruned"
        for change in disqualified.decision_impacts[-1].hypothesis_changes
    )
    graph_revision = (
        V2Storage.run_dir(disqualified.run_id)
        / "graph_revisions"
        / f"revision_{disqualified.state_revision:03d}.json"
    )
    assert graph_revision.exists()


def test_stop_reason_final_memo_sections_and_no_evpi_claim(pipeline):
    state = advance_to_stop(pipeline, run_cited_case(pipeline))

    assert state.stop_evaluation.should_stop is True
    assert "Stop:" in state.stop_evaluation.reason
    assert (
        "every ranked decision-critical internal question has been resolved" in state.stop_evaluation.reason
        or "below the materiality threshold" in state.stop_evaluation.reason
    )
    assert state.report.status == "blocked"
    assert state.report.recommendation.startswith(
        "Evidence refinement complete; decision blocked"
    )
    assert state.decision_completion["research_complete"] is True
    assert state.decision_completion["internal_evidence_complete"] is True
    assert state.decision_completion["actions_valid"] is True
    assert state.decision_completion["actions_confirmed"] is False
    assert state.decision_completion["decision_model_complete"] is False
    assert state.decision_completion["final_approval_ready"] is False
    assert state.decision_completion["stage"] == "action_confirmation"

    required_sections = [
        "## 1. Decision Status and Recommendation",
        "## 2. Deterministic Decision-Analysis Result",
        "## 3. Differences and Reasons",
        "## 4. Missing Human Confirmations",
        "## 5. Information Priorities by EVPPI",
        "## 6. Legacy Question Priority Score (Heuristic)",
        "## External Evidence Used",
        "## FOREFOLD Interpretations and Assumptions",
        "## Competing Decision Paths",
        "## Decision-Critical Internal Facts Requested",
        "## How Internal Evidence Changed the Decision",
        "## Alternatives Rejected or Weakened",
        "## Contradictions and Remaining Uncertainty",
        "## Continue-or-Stop Evaluation",
        "## Token and Privacy Boundary",
        "## Audit Trail",
        "## Preserved Sources",
        "## Method Note",
    ]
    for section in required_sections:
        assert section in state.report.markdown

    assert (
        "Decision analysis unavailable until actions, consequences, utilities, and distributions are confirmed."
        in state.report.markdown
    )
    assert not re.search(
        r"(?:we\s+)?(?:calculated|computed|estimate|estimated)\s+(?:an?\s+)?EVPI|EVPI\s*[:=]\s*[\d$]",
        state.report.markdown,
        re.IGNORECASE,
    )
    assert "Branch support scores are relative decision support, not calibrated probabilities." in state.report.markdown

    assert all(question.status in {"answered", "deferred"} for question in state.internal_questions)
    assert any(question.status == "answered" for question in state.internal_questions)

    confirmed = pipeline.confirm_decision_actions(
        state.run_id,
        [item.hypothesis_id for item in state.hypotheses],
        confirmed_by="decision-owner",
    )
    assert confirmed.decision_completion["actions_confirmed"] is True
    assert confirmed.decision_completion["decision_model_complete"] is False
    assert confirmed.decision_completion["stage"] == "decision_model_completion"
    assert confirmed.report.status == "blocked"
    assert "management_actions_confirmed" in {
        event.event_type for event in confirmed.audit_trail
    }

    finalized = pipeline.waive_quantitative_decision_analysis(
        confirmed.run_id,
        confirmed_by="decision-owner",
        reason="The owner accepts the qualitative evidence record without numeric utility claims.",
    )
    assert finalized.decision_completion["decision_model_calculated"] is False
    assert finalized.decision_completion["decision_model_waived"] is True
    assert finalized.decision_completion["decision_model_complete"] is True
    assert "No expected-utility, probability, EVPI, or EVPPI claim is made." in finalized.report.markdown
    assert "quantitative_decision_analysis_waived" in {
        event.event_type for event in finalized.audit_trail
    }


def test_stopped_case_has_no_outstanding_requested_question(pipeline):
    state = advance_to_stop(pipeline, run_cited_case(pipeline))
    assert [question for question in state.internal_questions if question.status == "requested"] == []


def test_action_confirmation_api_requires_the_complete_current_action_set(pipeline):
    state = advance_to_stop(pipeline, run_cited_case(pipeline))
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    action_ids = [item.hypothesis_id for item in state.hypotheses]

    partial = client.post(
        f"/api/v2/runs/{state.run_id}/actions/confirm",
        json={"action_ids": action_ids[:1], "confirmed_by": "decision-owner"},
    )
    assert partial.status_code == 400

    accepted = client.post(
        f"/api/v2/runs/{state.run_id}/actions/confirm",
        json={"action_ids": action_ids, "confirmed_by": "decision-owner"},
    )
    assert accepted.status_code == 200
    payload = accepted.get_json()["data"]["run"]
    assert payload["decision_completion"]["actions_confirmed"] is True
    assert payload["decision_completion"]["decision_model_complete"] is False
    assert payload["decision_completion"]["stage"] == "decision_model_completion"


def test_loading_a_legacy_stakeholder_run_reconstructs_actions_and_replays_state(pipeline):
    state = run_cited_case(pipeline)
    legacy_labels = ["Non-members", "Baristas", "Store managers"]
    for hypothesis, label in zip(state.hypotheses, legacy_labels):
        hypothesis.label = label
        hypothesis.decision_role = "alternative"
    state.decision_completion = {}
    V2Storage.save_state(state)

    repaired = pipeline.load_state(state.run_id)

    assert all(is_executable_action_label(item.label) for item in repaired.hypotheses)
    assert not any(item.label in legacy_labels for item in repaired.hypotheses)
    repair_event = next(
        event
        for event in repaired.audit_trail
        if event.event_type == "invalid_actions_reconstructed"
    )
    assert repair_event.details["rejected_labels"] == legacy_labels


def test_audit_events_are_ordered_and_token_usage_stays_zero(pipeline):
    state = advance_to_stop(pipeline, run_cited_case(pipeline))
    event_types = [event.event_type for event in state.audit_trail]

    assert event_types[:9] == [
        "import_completed",
        "evidence_classified",
        "contradictions_detected",
        "hypotheses_created",
        "questions_ranked",
        "stop_evaluated",
        "memo_generated",
        "public_baseline_sealed",
        "internal_run_forked",
    ]
    expected_answer_events = [
        "internal_answer_received",
        "decision_graph_updated",
        "stop_evaluated",
        "memo_generated",
    ] * len(state.decision_impacts)
    assert event_types[9:] == expected_answer_events
    assert [event.event_id for event in state.audit_trail] == [
        f"audit_{index:04d}" for index in range(1, len(state.audit_trail) + 1)
    ]
    assert state.token_usage.processing_mode == "local_deterministic"
    assert state.token_usage.external_llm_calls == 0
    assert state.token_usage.prompt_tokens == 0
    assert state.token_usage.completion_tokens == 0
    assert state.token_usage.total_tokens == 0

    audit_jsonl = V2Storage.run_dir(state.run_id) / "audit_trail.jsonl"
    persisted_events = [json.loads(line) for line in audit_jsonl.read_text(encoding="utf-8").splitlines()]
    assert [event["event_id"] for event in persisted_events] == [event.event_id for event in state.audit_trail]


def test_flask_api_structured_import_get_answer_stop_and_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "api_runs")
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    structured_document = json.loads(STRUCTURED_REPORT.read_text(encoding="utf-8"))

    assert client.post("/api/v2/run", json={"question": DECISION_QUESTION}).status_code == 400
    assert client.post("/api/v2/run", json={"documents": [structured_document]}).status_code == 400
    assert client.get("/api/v2/runs/not-a-run").status_code == 404

    response = client.post(
        "/api/v2/run",
        json={
            "project_name": "API Decision Verification",
            "question": "Should Atlas expand now, stage a pilot, or defer?",
            "documents": [structured_document],
        },
    )
    assert response.status_code == 200
    state = response.get_json()["data"]
    run_id = state["run_id"]
    requested = next(question for question in state["internal_questions"] if question["status"] == "requested")

    loaded = client.get(f"/api/v2/runs/{run_id}")
    assert loaded.status_code == 200
    assert loaded.get_json()["data"]["run_id"] == run_id
    questions = client.get(f"/api/v2/runs/{run_id}/internal-questions")
    assert questions.status_code == 200
    assert questions.get_json()["data"]["questions"][0]["rank"] == 1

    forked = client.post(f"/api/v2/runs/{run_id}/fork", json={})
    assert forked.status_code == 201
    state = forked.get_json()["data"]
    run_id = state["run_id"]
    requested = next(
        question for question in state["internal_questions"] if question["status"] == "requested"
    )

    assert client.post(f"/api/v2/runs/{run_id}/answers", json={"answer": "yes"}).status_code == 400
    assert client.post(
        f"/api/v2/runs/{run_id}/answers", json={"question_id": requested["question_id"]}
    ).status_code == 400
    assert client.post(
        f"/api/v2/runs/{run_id}/answers",
        json={"question_id": "question_unknown", "answer": "yes"},
    ).status_code == 400

    answer_text, answer_interpretation = ACTIONABLE_ANSWERS[requested["category"]]
    answer_payload = {
        "question_id": requested["question_id"],
        "answer": answer_text,
        "interpretation": answer_interpretation,
        "confidence": 1.0,
        "confidential": True,
    }
    accepted = client.post(f"/api/v2/runs/{run_id}/answers", json=answer_payload)
    assert accepted.status_code == 200
    accepted_state = accepted.get_json()["data"]
    assert accepted_state["internal_evidence"][0]["confidential"] is True
    assert accepted_state["internal_evidence"][0]["outbound_external_use"] is False
    assert client.post(f"/api/v2/runs/{run_id}/answers", json=answer_payload).status_code == 409

    evaluated = client.post(f"/api/v2/runs/{run_id}/stop/evaluate")
    assert evaluated.status_code == 200
    assert evaluated.get_json()["data"]["stop_evaluation"]["reason"]
    audit = client.get(f"/api/v2/runs/{run_id}/audit")
    assert audit.status_code == 200
    assert audit.get_json()["data"][0]["event_type"] == "import_completed"
    memo = client.get(f"/api/v2/runs/{run_id}/memo.md")
    assert memo.status_code == 200
    assert "## 1. Decision Status and Recommendation" in memo.get_data(as_text=True)
