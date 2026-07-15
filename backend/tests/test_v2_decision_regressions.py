import json

import pytest

from app import create_app
from app.v2.decision import DecisionIntelligenceService
from app.v2.extraction import ExtractionService
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.research_ingestion import ResearchIngestionService
from app.v2.schemas import ExtractedClaim
from app.v2.storage import V2Storage


DECISION_QUESTION = "Should Northstar proceed now, stage a reversible pilot, or defer?"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_regression_runs")
    return MiroFishV2Pipeline()


def _run_inline(pipeline: MiroFishV2Pipeline, text: str, name: str = "Regression case"):
    return pipeline.run_from_inline_documents(
        [{"filename": "deep-research.md", "text": text}],
        question=DECISION_QUESTION,
        project_name=name,
    )


def _external_urls(claim):
    return {citation.url for citation in claim.citations if citation.url}


def _requested_question(state):
    requested = [question for question in state.internal_questions if question.status == "requested"]
    assert len(requested) == 1
    return requested[0]


ACTIONABLE_ANSWERS = {
    "strategic_success": (
        "The minimum success threshold is 10% revenue growth within 12 months.",
        "mixed",
    ),
    "constraints": (
        "Legal review confirmed there are no legal blockers or policy constraints.",
        "favorable",
    ),
    "financial_capacity": (
        "Finance approved a $14.7 million budget and funding is sufficient within the downside limit.",
        "favorable",
    ),
    "execution_capacity": (
        "The operating owner is named, with 8 committed staff and sufficient delivery capacity.",
        "favorable",
    ),
    "risk_tolerance": ("The maximum acceptable downside loss is $2 million.", "mixed"),
    "timing": (
        "The decision deadline is 2026-09-30 and dependencies are cleared for an October start.",
        "mixed",
    ),
}


def _submit_actionable_answer(pipeline, state):
    question = _requested_question(state)
    answer, interpretation = ACTIONABLE_ANSWERS[question.category]
    return pipeline.submit_internal_answer(
        state.run_id,
        question.question_id,
        answer,
        confidence=1.0,
        interpretation=interpretation,
    )


def _advance_to_category(pipeline, state, category):
    while _requested_question(state).category != category:
        state = _submit_actionable_answer(pipeline, state)
        assert not state.stop_evaluation.should_stop
    return state


def test_neighboring_inline_citations_attach_only_to_their_claim():
    growth_url = "https://evidence.example/reports/growth-source"
    risk_url = "https://evidence.example/reports/risk-source"
    markdown = f"""
Northstar reported that revenue growth increased by 31 percent during the pilot.
[Independent growth benchmark with comprehensive methodological details and supporting tables]({growth_url})

The supplier committee reported that debt risk increased after customer payment delays.
[Independent supplier-risk benchmark with comprehensive methodological details and supporting tables]({risk_url})
""".strip()

    documents = ResearchIngestionService(chunk_size=2_000, chunk_overlap=0).ingest_inline_documents(
        [{"filename": "neighboring-citations.md", "text": markdown}]
    )
    claims = ExtractionService().extract_claims(documents)
    growth_claim = next(claim for claim in claims if "revenue growth" in claim.text)
    risk_claim = next(claim for claim in claims if "debt risk" in claim.text)

    assert _external_urls(growth_claim) == {growth_url}
    assert _external_urls(risk_claim) == {risk_url}


def test_citation_only_markdown_lines_are_not_extracted_as_claims():
    markdown = """
Northstar reported that revenue growth increased by 31 percent during the pilot.
[Independent external source with comprehensive methodological details, supporting tables, and publication metadata](https://evidence.example/reports/source-only-line)
""".strip()
    documents = ResearchIngestionService(chunk_size=2_000, chunk_overlap=0).ingest_inline_documents(
        [{"filename": "citation-only-line.md", "text": markdown}]
    )
    claims = ExtractionService().extract_claims(documents)

    assert not any(
        claim.text.lstrip().startswith("[") or claim.text.lstrip().startswith(("http://", "https://"))
        for claim in claims
    )


def test_inline_citation_label_cannot_attach_a_claim_to_the_wrong_option(pipeline):
    source_url = "https://source.example/beta-risk"
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "cloud-risk.md",
                "text": (
                    "Beta Cloud increased severe migration risk "
                    f"[Alpha Cloud benchmark]({source_url})."
                ),
            }
        ],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Citation-label isolation regression",
    )

    claim = next(item for item in state.claims if "migration risk" in item.text.lower())
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert "Alpha Cloud benchmark" not in claim.text
    assert source_url in {citation.url for citation in claim.citations}
    assert alpha.opposing_claim_ids == []
    assert beta.opposing_claim_ids == [claim.claim_id]
    assert alpha.support_score > beta.support_score


def test_reference_citation_label_cannot_attach_a_claim_to_the_wrong_option(pipeline):
    source_url = "https://source.example/reference-beta-risk"
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "cloud-reference-risk.md",
                "text": (
                    "Beta Cloud increased severe migration risk [Alpha Cloud benchmark][src].\n\n"
                    f"[src]: {source_url}"
                ),
            }
        ],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Reference-label isolation regression",
    )

    claim = next(item for item in state.claims if "migration risk" in item.text.lower())
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert "Alpha Cloud benchmark" not in claim.text
    assert source_url in {citation.url for citation in claim.citations}
    assert alpha.opposing_claim_ids == []
    assert beta.opposing_claim_ids == [claim.claim_id]
    assert alpha.support_score > beta.support_score


def test_two_pdf_uri_annotations_on_one_page_are_not_both_attached_to_each_claim(tmp_path):
    import fitz

    alpha_url = "https://evidence.example/pdf/alpha"
    beta_url = "https://evidence.example/pdf/beta"
    pdf_path = tmp_path / "two-citations-one-page.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Northstar reported revenue growth of twenty percent during the pilot.", fontsize=10)
    page.insert_text((72, 95), "Source Alpha", fontsize=10)
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(68, 82, 155, 101),
            "uri": alpha_url,
        }
    )
    page.insert_text((72, 172), "The supplier committee reported severe debt risk after payment delays.", fontsize=10)
    page.insert_text((72, 195), "Source Beta", fontsize=10)
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(68, 182, 150, 201),
            "uri": beta_url,
        }
    )
    pdf.save(pdf_path)
    pdf.close()

    documents = ResearchIngestionService(chunk_size=2_000, chunk_overlap=0).ingest_paths([pdf_path])
    claims = ExtractionService().extract_claims(documents)
    growth_claim = next(claim for claim in claims if "revenue growth" in claim.text)
    risk_claim = next(claim for claim in claims if "debt risk" in claim.text)

    assert _external_urls(growth_claim) == {alpha_url}
    assert _external_urls(risk_claim) == {beta_url}


def _retained_structured_claims(document):
    model_value = getattr(document, "structured_claims", None)
    if model_value:
        return model_value
    metadata = document.metadata
    if metadata.get("structured_claims"):
        return metadata["structured_claims"]
    if metadata.get("claims"):
        return metadata["claims"]
    structured_payload = metadata.get("structured_payload") or {}
    return structured_payload.get("claims")


def test_inline_and_path_structured_imports_retain_nested_claims_citations_and_original_ids(tmp_path):
    payload = {
        "title": "Structured provenance regression",
        "source_system": "OpenAI Deep Research",
        "text": "The executive summary says the decision remains sensitive to private constraints.",
        "claims": [
            {
                "id": "original-claim-growth",
                "text": "The market benchmark reported that demand growth increased by 27 percent.",
                "citations": [
                    {
                        "id": "original-citation-growth",
                        "title": "Demand benchmark",
                        "url": "https://evidence.example/structured/growth",
                        "quote": "The market benchmark reported that demand growth increased by 27 percent.",
                    }
                ],
            },
            {
                "id": "original-claim-risk",
                "text": "The implementation review reported that security delay increased execution risk.",
                "citations": [
                    {
                        "id": "original-citation-risk",
                        "title": "Implementation review",
                        "url": "https://evidence.example/structured/risk",
                        "quote": "The implementation review reported that security delay increased execution risk.",
                    }
                ],
            },
        ],
    }
    json_path = tmp_path / "structured-report.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    service = ResearchIngestionService(chunk_size=2_000, chunk_overlap=0)
    inline_document = service.ingest_inline_documents([payload])[0]
    path_document = service.ingest_paths([json_path])[0]

    for document in (inline_document, path_document):
        retained = _retained_structured_claims(document)
        assert retained is not None
        assert [claim["id"] for claim in retained] == [
            "original-claim-growth",
            "original-claim-risk",
        ]
        assert retained[0]["citations"][0]["id"] == "original-citation-growth"
        assert retained[0]["citations"][0]["url"] == "https://evidence.example/structured/growth"

        if "original_claim_id" in ExtractedClaim.model_fields:
            extracted = ExtractionService().extract_claims([document])
            growth_claim = next(claim for claim in extracted if "demand growth" in claim.text)
            risk_claim = next(claim for claim in extracted if "execution risk" in claim.text)
            assert growth_claim.original_claim_id == "original-claim-growth"
            assert risk_claim.original_claim_id == "original-claim-risk"


def test_positive_and_negative_reports_change_hypothesis_scores_and_ranking(pipeline):
    positive_report = " ".join(
        [
            "The market study reported strong demand growth and increased customer benefit.",
            "The finance review announced approved funding and improved revenue opportunity.",
            "The operating benchmark reported increased capacity and strong execution gains.",
            "The customer analysis forecast growth, benefit, and improved retention.",
        ]
    )
    negative_report = " ".join(
        [
            "The market study reported severe revenue decline and increased debt risk.",
            "The finance review announced a funding shortfall and increased loss exposure.",
            "The operating benchmark reported supplier delay and weak execution capacity.",
            "The customer analysis forecast decline, loss, and increased operational risk.",
        ]
    )
    positive = _run_inline(pipeline, positive_report, "Positive evidence")
    negative = _run_inline(pipeline, negative_report, "Negative evidence")

    positive_scores = {item.hypothesis_id: item.support_score for item in positive.hypotheses}
    negative_scores = {item.hypothesis_id: item.support_score for item in negative.hypotheses}
    positive_ranking = [
        item.hypothesis_id
        for item in sorted(positive.hypotheses, key=lambda hypothesis: hypothesis.support_score, reverse=True)
    ]
    negative_ranking = [
        item.hypothesis_id
        for item in sorted(negative.hypotheses, key=lambda hypothesis: hypothesis.support_score, reverse=True)
    ]

    assert positive_scores != negative_scores
    assert positive_ranking != negative_ranking
    assert positive_scores["hypothesis_proceed"] > negative_scores["hypothesis_proceed"]
    assert negative_scores["hypothesis_defer"] > positive_scores["hypothesis_defer"]


def test_shared_option_words_do_not_cross_attach_alpha_and_beta_cloud_evidence(pipeline):
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "cloud-comparison.md",
                "text": " ".join(
                    [
                        "The benchmark reported Alpha Cloud improved reliability and reduced operational loss.",
                        "The benchmark reported Beta Cloud increased migration risk and caused severe delay.",
                    ]
                ),
            }
        ],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Shared option-word regression",
    )
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert alpha.support_score > beta.support_score
    assert alpha.supporting_claim_ids
    assert not alpha.opposing_claim_ids
    assert beta.opposing_claim_ids
    assert not beta.supporting_claim_ids


def test_citation_destination_tokens_never_attach_evidence_to_an_option(pipeline):
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "cloud-citation-regression.md",
                "text": (
                    "Beta Cloud increased severe migration risk "
                    "[source](https://alpha-cloud.example/report)."
                ),
            }
        ],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Citation destination option matching regression",
    )
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert alpha.opposing_claim_ids == []
    assert beta.opposing_claim_ids
    assert alpha.support_score > beta.support_score


def test_longest_option_phrase_prevents_standard_plan_plus_from_laundering_to_base(pipeline):
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "plan-comparison.md",
                "text": " ".join(
                    [
                        "The benchmark reported Standard Plan improved service reliability and reduced operating cost.",
                        "The benchmark reported Standard Plan Plus increased implementation risk and caused migration delay.",
                        "The benchmark reported Standard Plan Plus increased loss exposure and worsened delivery risk.",
                    ]
                ),
            }
        ],
        question="Should we choose Standard Plan or Standard Plan Plus?",
        project_name="Overlapping option-name regression",
    )
    base = next(item for item in state.hypotheses if item.label.lower().endswith("standard plan"))
    plus = next(item for item in state.hypotheses if "standard plan plus" in item.label.lower())
    claim_text = {claim.claim_id: claim.text for claim in state.claims}

    assert base.support_score > plus.support_score
    assert all("Plus" not in claim_text[claim_id] for claim_id in base.supporting_claim_ids)
    assert all("Plus" not in claim_text[claim_id] for claim_id in base.opposing_claim_ids)
    assert plus.opposing_claim_ids

    service = DecisionIntelligenceService()
    assert service._mentioned_option_indices(
        "Standard Plan is cheaper than Standard Plan Plus.",
        ["Standard Plan", "Standard Plan Plus"],
    ) == {0, 1}


def test_named_immediate_option_uses_only_its_evidence_and_beats_generated_defer(pipeline):
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "product-comparison.md",
                "text": " ".join(
                    [
                        "The benchmark reported Product A delivered strong growth and improved reliability.",
                        "The benchmark reported Product B caused severe implementation risk and loss.",
                        "The finance review reported Product B increased debt and operating cost.",
                        "The delivery review reported Product B caused severe migration delay and capacity shortfall.",
                        "The customer review reported Product B decreased retention and delivered no benefit.",
                    ]
                ),
            }
        ],
        question="Should we launch Product A now or Product B now?",
        project_name="Named immediate-option regression",
    )
    product_a = next(item for item in state.hypotheses if "product a" in item.label.lower())
    product_b = next(item for item in state.hypotheses if "product b" in item.label.lower())
    defer = next(item for item in state.hypotheses if item.decision_role == "defer")
    claim_text = {claim.claim_id: claim.text for claim in state.claims}

    assert product_a.support_score > defer.support_score > product_b.support_score
    assert product_a.status == "leading"
    assert product_a.supporting_claim_ids
    assert product_a.opposing_claim_ids == []
    assert all("Product A" in claim_text[claim_id] for claim_id in product_a.supporting_claim_ids)
    assert len(product_b.opposing_claim_ids) == 4
    assert all("Product B" in claim_text[claim_id] for claim_id in product_b.opposing_claim_ids)


@pytest.mark.parametrize(
    ("claim", "expected"),
    [
        ("Alpha Cloud reduced loss and risk, improved reliability, and eliminated delay.", 1),
        ("Alpha Cloud did not improve reliability and delivered no growth or benefit.", -1),
        ("Revenue decreased while risk increased.", -1),
        ("Alpha Cloud's risk did not increase.", 0),
        ("Alpha Cloud had no increase in risk.", 0),
        ("Alpha Cloud's risk was not severe.", 0),
        ("Alpha Cloud did not suffer a loss.", 0),
        ("Alpha Cloud avoided no risk.", 0),
        ("Alpha Cloud has no severe migration risk.", 0),
        ("No material loss was found for Alpha Cloud.", 0),
        ("Alpha Cloud did not have severe risk.", 0),
        ("Alpha Cloud has no risk.", 0),
        ("Alpha Cloud is free of implementation risk.", 0),
        ("Alpha Cloud can proceed without delay or loss.", 0),
        ("Alpha Cloud didn't increase risk.", 0),
        ("Alpha Cloud doesn't increase risk.", 0),
        ("Alpha Cloud isn't high risk.", 0),
        ("Alpha Cloud is not a high-risk option.", 0),
        ("Alpha Cloud has low risk.", 1),
        ("Alpha Cloud risk is low.", 1),
        ("Alpha Cloud has minimal loss exposure.", 1),
        ("Alpha Cloud risk is manageable.", 0),
        ("Alpha Cloud risk stayed flat.", 0),
        ("There is no evidence that Alpha Cloud increased risk.", 0),
        ("The review did not find evidence that Alpha Cloud improved reliability.", 0),
        ("It is unclear whether Alpha Cloud increased risk.", 0),
        ("The committee could not confirm Alpha Cloud improved reliability.", 0),
        ("Alpha Cloud may not increase risk.", 0),
        ("Alpha Cloud may not improve reliability.", 0),
    ],
)
def test_claim_polarity_handles_direction_and_negation(claim, expected):
    assert DecisionIntelligenceService()._claim_polarity(claim) == expected


@pytest.mark.parametrize(
    "claim_text",
    [
        "Alpha Cloud has lower implementation risk than Beta Cloud.",
        "Alpha Cloud improved reliability more than Beta Cloud.",
        "Alpha Cloud reduced loss compared with Beta Cloud.",
    ],
)
def test_comparative_claim_supports_only_the_directional_subject(pipeline, claim_text):
    state = pipeline.run_from_inline_documents(
        [{"filename": "comparison.md", "text": claim_text}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Comparative direction regression",
    )
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert alpha.support_score > beta.support_score
    assert alpha.supporting_claim_ids
    assert beta.supporting_claim_ids == []


def test_multi_option_claim_uses_clause_local_polarity(pipeline):
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "mixed-options.md",
                "text": (
                    "Alpha Cloud improved reliability while "
                    "Beta Cloud increased severe migration risk."
                ),
            }
        ],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Clause-local polarity regression",
    )
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert alpha.support_score > beta.support_score
    assert alpha.supporting_claim_ids
    assert alpha.opposing_claim_ids == []
    assert beta.supporting_claim_ids == []
    assert beta.opposing_claim_ids


def test_neutral_option_mention_gets_no_coverage_bonus_or_unique_recommendation(pipeline):
    state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "neutral-review.md",
                "text": "The committee evaluated Alpha Cloud during its scheduled review.",
            }
        ],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Neutral mention regression",
    )
    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())

    assert alpha.support_score == beta.support_score
    assert alpha.supporting_claim_ids == alpha.opposing_claim_ids == []
    assert state.stop_evaluation.leading_hypothesis_id is None
    assert "No unique recommendation" in DecisionIntelligenceService().recommendation(state)


def test_no_evidence_keeps_every_path_equal_unsupported_and_names_all_ties(pipeline):
    state = pipeline.run_from_inline_documents(
        [{"filename": "empty-report.md", "text": "Appendix."}],
        question="Should we proceed now, stage a reversible pilot, or defer?",
        project_name="No evidence regression",
    )

    assert state.claims == []
    assert {hypothesis.support_score for hypothesis in state.hypotheses} == {0.35}
    assert {hypothesis.status for hypothesis in state.hypotheses} == {"unsupported"}
    assert state.stop_evaluation.leading_hypothesis_id is None
    recommendation = DecisionIntelligenceService().recommendation(state)
    assert "No unique recommendation" in recommendation
    assert f"all {len(state.hypotheses)} tied paths" in recommendation
    assert all(hypothesis.label in recommendation for hypothesis in state.hypotheses)


def test_temporally_distinct_metric_values_are_not_contradictions():
    service = DecisionIntelligenceService()
    claims = [
        ExtractedClaim(
            claim_id="claim_2024",
            text="The market benchmark reported revenue growth increased 10% in 2024.",
            source_document_id="doc",
            source_chunk_id="chunk_1",
        ),
        ExtractedClaim(
            claim_id="claim_2025",
            text="The market benchmark reported revenue growth increased 20% in 2025.",
            source_document_id="doc",
            source_chunk_id="chunk_2",
        ),
    ]

    assert service._detect_contradictions(claims) == []
    assert claims[0].contradicts_claim_ids == []
    assert claims[1].contradicts_claim_ids == []


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Yes", "uncertain"),
        ("No", "uncertain"),
        ("The approved budget is not sufficient for this commitment.", "unfavorable"),
        ("There are no non-negotiable constraints that disqualify the pilot.", "favorable"),
    ],
)
def test_negation_and_low_information_answers_are_interpreted_conservatively(answer, expected):
    assert DecisionIntelligenceService()._normalize_interpretation(None, answer) == expected


def test_constraint_interpretation_masks_negations_and_honors_explicit_conflicts():
    service = DecisionIntelligenceService()

    assert service._interpret_answer(
        "No blocker is known because legal has not reviewed it.",
        "constraints",
    )[0] == "uncertain"
    assert service._interpret_answer(
        "Alpha Cloud is not illegal and is not prohibited by policy.",
        "constraints",
    )[0] == "favorable"
    assert service._interpret_answer(
        "Alpha Cloud is not currently prohibited by policy.",
        "constraints",
    )[0] == "favorable"
    assert service._interpret_answer(
        "There is no legal constraint that disqualifies Alpha Cloud.",
        "constraints",
    )[0] == "favorable"
    assert service._interpret_answer(
        "There are no legal blockers, but a security constraint prohibits Alpha Cloud deployment.",
        "constraints",
    )[0] == "unfavorable"


@pytest.mark.parametrize(
    ("answer", "category"),
    [
        ("Finance approved a $0 budget.", "financial_capacity"),
        ("There are 0 staff available.", "execution_capacity"),
    ],
)
def test_zero_internal_capacity_is_never_interpreted_as_favorable_support(answer, category):
    service = DecisionIntelligenceService()
    interpretation, _rationale = service._interpret_answer(answer, category)
    relevant, _relevance_rationale = service._answer_relevance(answer, category)

    assert relevant is True
    assert interpretation == "unfavorable"


@pytest.mark.parametrize(
    ("answer", "category"),
    [
        (
            "None of the 8 staff are unavailable; all are committed and capacity is sufficient.",
            "execution_capacity",
        ),
        (
            "None of the approved budget is unavailable; all $10m is funded and sufficient.",
            "financial_capacity",
        ),
        (
            "None of the budget is unapproved; all $10m is funded and sufficient.",
            "financial_capacity",
        ),
        ("The approved budget is not zero; $10m is fully funded and sufficient.", "financial_capacity"),
        ("Staff is not zero; 8 people are available and capacity is sufficient.", "execution_capacity"),
        ("Budget is greater than zero and sufficient.", "financial_capacity"),
    ],
)
def test_explicit_nonzero_capacity_is_not_misread_as_zero(answer, category):
    service = DecisionIntelligenceService()
    interpretation, _rationale = service._interpret_answer(answer, category)
    relevant, _relevance_rationale = service._answer_relevance(answer, category)

    assert relevant is True
    assert interpretation == "favorable"


@pytest.mark.parametrize(
    ("answer", "category"),
    [
        ("Finance approved a $14.7 million budget and funding is sufficient.", "constraints"),
        ("Legal review confirmed there are no policy blockers.", "strategic_success"),
        ("The implementation deadline is 2026-09-30 and dependencies are cleared.", "risk_tolerance"),
    ],
)
def test_answers_for_the_wrong_private_fact_slot_are_not_relevant(answer, category):
    relevant, _rationale = DecisionIntelligenceService()._answer_relevance(answer, category)
    assert relevant is False


def test_irrelevant_answer_mutates_graph_revision_but_not_decision_branches(pipeline):
    state = _run_inline(
        pipeline,
        "The report found growth opportunity while private legal constraints remain unknown.",
    )
    requested = _requested_question(state)
    assert requested.category == "constraints"
    before_scores = {item.hypothesis_id: item.support_score for item in state.hypotheses}
    before_revision = state.graph_revision

    secret_answer = (
        "BOARD-SECRET-2026: Finance approved a $14.7 million budget and funding is sufficient."
    )
    state = pipeline.submit_internal_answer(
        state.run_id,
        requested.question_id,
        secret_answer,
        confidence=1.0,
        interpretation="favorable",
    )

    evidence = state.internal_evidence[-1]
    assert evidence.question_relevant is False
    assert evidence.decision_usable is False
    assert _requested_question(state).question_id == requested.question_id
    assert {item.hypothesis_id: item.support_score for item in state.hypotheses} == before_scores
    assert state.graph_revision == before_revision + 1
    assert state.graph["revision"] == state.graph_revision
    assert any(
        edge["source"] == evidence.evidence_id and edge["type"] == "attempted_answer"
        for edge in state.graph["edges"]
    )
    graph_events = [event for event in state.audit_trail if event.event_type == "decision_graph_updated"]
    assert graph_events[-1].details["revision"] == state.graph_revision
    assert graph_events[-1].details["decision_usable"] is False
    assert state.internal_evidence[-1].answer == secret_answer
    assert secret_answer not in json.dumps(state.graph)
    assert secret_answer not in json.dumps(
        [event.model_dump(mode="json") for event in state.audit_trail]
    )


def test_unverified_no_blocker_answer_does_not_resolve_or_prune(pipeline):
    state = _run_inline(
        pipeline,
        "The report found growth opportunity while private legal constraints remain unknown.",
    )
    requested = _requested_question(state)
    before_scores = {item.hypothesis_id: item.support_score for item in state.hypotheses}

    state = pipeline.submit_internal_answer(
        state.run_id,
        requested.question_id,
        "No blocker is known because legal has not reviewed it.",
        confidence=1.0,
        interpretation="uncertain",
    )

    assert state.internal_evidence[-1].decision_usable is False
    assert _requested_question(state).question_id == requested.question_id
    assert {item.hypothesis_id: item.support_score for item in state.hypotheses} == before_scores
    assert not any(item.status == "pruned" for item in state.hypotheses)


def test_negated_constraint_with_intervening_adverb_never_prunes(pipeline):
    state = pipeline.run_from_inline_documents(
        [{"filename": "cloud.md", "text": "The benchmark reported Alpha Cloud improved reliability."}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Negated constraint regression",
    )
    state = _advance_to_category(pipeline, state, "constraints")
    state = pipeline.submit_internal_answer(
        state.run_id,
        _requested_question(state).question_id,
        "Alpha Cloud is not currently prohibited by policy.",
        confidence=1.0,
        interpretation="favorable",
    )

    assert state.internal_evidence[-1].decision_usable is True
    assert not any(item.status == "pruned" for item in state.hypotheses)


@pytest.mark.parametrize(
    ("answer", "expected_interpretation"),
    [
        ("Alpha Cloud may be prohibited by policy pending legal review.", "mixed"),
        ("Alpha Cloud is potentially prohibited by policy.", "mixed"),
        ("Alpha Cloud could be prohibited if the regulator changes its position.", "mixed"),
        ("Alpha Cloud is temporarily prohibited unless a waiver is approved.", "mixed"),
        ("There is no evidence that Alpha Cloud is prohibited.", "uncertain"),
        ("Legal has not confirmed whether Alpha Cloud is prohibited.", "uncertain"),
        ("It is false that Alpha Cloud is prohibited.", "favorable"),
        ("Neither Alpha Cloud nor Beta Cloud is prohibited by policy.", "favorable"),
        ("Alpha Cloud is by no means prohibited.", "favorable"),
        ("Alpha Cloud was prohibited last year, but the prohibition has been lifted.", "mixed"),
        ("Alpha Cloud was blocked during the pilot, but it is now cleared.", "mixed"),
    ],
)
def test_only_confirmed_unconditional_blockers_can_prune(
    pipeline,
    answer,
    expected_interpretation,
):
    state = pipeline.run_from_inline_documents(
        [{"filename": "cloud.md", "text": "Alpha Cloud and Beta Cloud have comparable evidence."}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Qualified blocker regression",
    )
    state = _advance_to_category(pipeline, state, "constraints")
    state = pipeline.submit_internal_answer(
        state.run_id,
        _requested_question(state).question_id,
        answer,
        confidence=1.0,
        interpretation=expected_interpretation,
    )

    assert state.internal_evidence[-1].interpretation == expected_interpretation
    assert not any(item.status == "pruned" for item in state.hypotheses)
    assert not any(item.pruned_by_evidence_id for item in state.hypotheses)


def test_explicit_conflicting_constraint_prunes_target_and_pruned_path_is_not_leader(pipeline):
    state = pipeline.run_from_inline_documents(
        [{"filename": "cloud.md", "text": "Alpha Cloud improved reliability while Beta Cloud improved capacity."}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Constraint dominance regression",
    )
    state = _advance_to_category(pipeline, state, "constraints")
    requested = _requested_question(state)
    state = pipeline.submit_internal_answer(
        state.run_id,
        requested.question_id,
        "There are no legal blockers, but a security constraint prohibits Alpha Cloud deployment.",
        confidence=1.0,
        interpretation="unfavorable",
    )

    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    assert alpha.status == "pruned"
    assert state.stop_evaluation.leading_hypothesis_id != alpha.hypothesis_id
    assert f"Recommend **{alpha.label}**" not in DecisionIntelligenceService().recommendation(state)


@pytest.mark.parametrize(
    ("category", "answer"),
    [
        ("constraints", "Policy prohibits all cloud deployment and cannot proceed."),
        ("constraints", "Policy prohibits cloud deployment and cannot proceed."),
        ("constraints", "No option can proceed."),
        ("constraints", "None of the options can proceed."),
        ("constraints", "Neither Alpha Cloud nor Beta Cloud can proceed."),
        ("constraints", "All options are unable to proceed."),
        ("financial_capacity", "No approved budget exists."),
        ("execution_capacity", "There is no execution owner and no capacity."),
    ],
)
def test_global_hard_blocker_prunes_every_named_actionable_alternative(
    pipeline,
    category,
    answer,
):
    state = pipeline.run_from_inline_documents(
        [{"filename": "cloud.md", "text": "Alpha Cloud and Beta Cloud have comparable evidence."}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Global blocker regression",
    )
    state = _advance_to_category(pipeline, state, category)
    state = pipeline.submit_internal_answer(
        state.run_id,
        _requested_question(state).question_id,
        answer,
        confidence=1.0,
        interpretation="unfavorable",
    )

    actionable = [item for item in state.hypotheses if item.decision_role != "defer"]
    defer = next(item for item in state.hypotheses if item.decision_role == "defer")
    assert actionable
    assert all(item.status == "pruned" for item in actionable)
    assert defer.status != "pruned"
    assert state.stop_evaluation.leading_hypothesis_id == defer.hypothesis_id


@pytest.mark.parametrize(
    "answer",
    [
        "Alpha Cloud is approved and Beta Cloud is prohibited.",
        "Alpha Cloud is not prohibited, Beta Cloud is prohibited.",
    ],
)
def test_disqualifier_targets_only_its_local_option_clause(pipeline, answer):
    state = pipeline.run_from_inline_documents(
        [{"filename": "cloud.md", "text": "Alpha Cloud and Beta Cloud have comparable evidence."}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Local blocker subject regression",
    )
    state = _advance_to_category(pipeline, state, "constraints")
    before_scores = {item.hypothesis_id: item.support_score for item in state.hypotheses}
    state = pipeline.submit_internal_answer(
        state.run_id,
        _requested_question(state).question_id,
        answer,
        confidence=1.0,
        interpretation="unfavorable",
    )

    alpha = next(item for item in state.hypotheses if "alpha cloud" in item.label.lower())
    beta = next(item for item in state.hypotheses if "beta cloud" in item.label.lower())
    assert alpha.status != "pruned"
    assert alpha.support_score >= before_scores[alpha.hypothesis_id]
    assert beta.status == "pruned"


def test_early_stop_is_reachable_when_only_one_feasible_path_remains(pipeline):
    state = pipeline.run_from_inline_documents(
        [{"filename": "cloud.md", "text": "Alpha Cloud and Beta Cloud have comparable public evidence."}],
        question="Should we choose Alpha Cloud or Beta Cloud?",
        project_name="Early stop reachability",
    )
    state = _advance_to_category(pipeline, state, "constraints")
    answered_before = sum(item.status == "answered" for item in state.internal_questions)
    state = pipeline.submit_internal_answer(
        state.run_id,
        _requested_question(state).question_id,
        "Alpha Cloud and Beta Cloud are prohibited by policy and cannot proceed.",
        confidence=1.0,
        interpretation="unfavorable",
    )

    assert sum(item.status == "pruned" for item in state.hypotheses) == 2
    assert state.stop_evaluation.should_stop is True
    assert sum(item.status == "answered" for item in state.internal_questions) == answered_before + 1
    assert sum(item.status == "answered" for item in state.internal_questions) < len(state.internal_questions)
    assert any(item.status == "deferred" for item in state.internal_questions)
    assert state.stop_evaluation.leading_hypothesis_id == "hypothesis_defer"


def test_zero_confidence_unknown_does_not_resolve_decay_or_stop(pipeline):
    state = _run_inline(
        pipeline,
        "The report said market growth increased, but execution risk and private constraints remain unresolved.",
    )
    requested = _requested_question(state)
    before_scores = {item.hypothesis_id: item.support_score for item in state.hypotheses}
    before_question_state = {
        item.question_id: (item.status, item.answer_id, item.information_value_score)
        for item in state.internal_questions
    }

    try:
        pipeline.submit_internal_answer(
            state.run_id,
            requested.question_id,
            "Unknown; the owner could not verify this fact.",
            confidence=0.0,
            interpretation="uncertain",
        )
    except ValueError:
        pass

    after = pipeline.load_state(state.run_id)
    assert {item.hypothesis_id: item.support_score for item in after.hypotheses} == before_scores
    assert {
        item.question_id: (item.status, item.answer_id, item.information_value_score)
        for item in after.internal_questions
    } == before_question_state
    assert after.stop_evaluation.should_stop is False


def test_only_currently_requested_highest_ranked_question_can_be_answered(pipeline):
    state = _run_inline(
        pipeline,
        "The report said demand growth increased while debt risk and execution uncertainty remain.",
    )
    requested = _requested_question(state)
    pending = next(question for question in state.internal_questions if question.status == "pending")
    assert requested.rank < pending.rank

    with pytest.raises(ValueError):
        pipeline.submit_internal_answer(
            state.run_id,
            pending.question_id,
            "This lower-ranked fact is favorable.",
            confidence=1.0,
            interpretation="favorable",
        )

    persisted = pipeline.load_state(state.run_id)
    assert persisted.internal_evidence == []
    assert _requested_question(persisted).question_id == requested.question_id


def test_should_stop_requires_effective_remaining_value_below_threshold_or_no_questions(pipeline):
    state = _run_inline(
        pipeline,
        "The report found strong growth and approved opportunity, while private constraints remain unknown.",
    )
    for _index in range(len(state.internal_questions)):
        if state.stop_evaluation.should_stop:
            break
        state = _submit_actionable_answer(pipeline, state)

    assert state.stop_evaluation.should_stop is True
    unresolved = [question for question in state.internal_questions if question.status != "answered"]
    if unresolved:
        assert state.stop_evaluation.remaining_information_value < state.stop_evaluation.materiality_threshold
        assert max(question.information_value_score for question in unresolved) < state.stop_evaluation.materiality_threshold


def test_api_redacts_confidential_answer_from_answer_and_run_responses(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "redaction_runs")
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    created = client.post(
        "/api/v2/run",
        json={
            "project_name": "Confidential response regression",
            "question": DECISION_QUESTION,
            "documents": [
                {
                    "filename": "report.md",
                    "text": "The report said demand growth increased while internal capacity remains unknown.",
                }
            ],
        },
    )
    assert created.status_code == 200
    created_state = created.get_json()["data"]
    run_id = created_state["run_id"]
    requested = next(
        question for question in created_state["internal_questions"] if question["status"] == "requested"
    )
    answer, interpretation = ACTIONABLE_ANSWERS[requested["category"]]
    secret = f"BOARD-SECRET-2026 {answer}"

    answered = client.post(
        f"/api/v2/runs/{run_id}/answers",
        json={
            "question_id": requested["question_id"],
            "answer": secret,
            "confidence": 1.0,
            "interpretation": interpretation,
            "confidential": True,
        },
    )
    assert answered.status_code == 200
    assert secret not in answered.get_data(as_text=True)

    loaded = client.get(f"/api/v2/runs/{run_id}")
    assert loaded.status_code == 200
    assert secret not in loaded.get_data(as_text=True)
    assert V2Storage.load_state(run_id).internal_evidence[0].answer == secret
