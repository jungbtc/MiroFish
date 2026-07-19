import json

import pytest

from app import create_app
from app.utils.llm_client import LLMClient
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.storage import V2Storage


VENDOR_REPORT = """
Vendor A reported strong implementation readiness and approved operating capacity.
Vendor A also reported that customer growth increased during its reference deployment.
Vendor B reported strong security controls and improved service reliability.
Vendor B also reported that migration delay and debt risk remain material concerns.
""".strip()


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_invariant_runs")
    return MiroFishV2Pipeline()


def _run_vendor_case(
    pipeline: MiroFishV2Pipeline,
    *,
    question: str = "Should we choose Vendor A or Vendor B?",
):
    public_state = pipeline.run_from_inline_documents(
        [{"filename": "vendor-research.md", "text": VENDOR_REPORT}],
        question=question,
        project_name="Vendor decision invariants",
    )
    return pipeline.fork_public_run(public_state.run_id)


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


def test_vendor_a_vs_vendor_b_creates_named_non_generic_decision_paths(pipeline):
    state = _run_vendor_case(pipeline)

    vendor_a = next(
        hypothesis for hypothesis in state.hypotheses if "vendor a" in hypothesis.label.lower()
    )
    vendor_b = next(
        hypothesis for hypothesis in state.hypotheses if "vendor b" in hypothesis.label.lower()
    )

    assert vendor_a.hypothesis_id != vendor_b.hypothesis_id
    assert vendor_a.decision_role == vendor_b.decision_role == "alternative"
    assert "vendor a" in vendor_a.description.lower()
    assert "vendor b" in vendor_b.description.lower()
    assert {vendor_a.label.lower(), vendor_b.label.lower()}.isdisjoint(
        {
            "proceed with the proposed decision",
            "stage a reversible pilot",
            "defer decision",
        }
    )


def test_conflicting_explicit_interpretation_is_rejected_without_persisting_answer(pipeline):
    state = _run_vendor_case(pipeline)
    requested = _requested_question(state)
    run_dir = V2Storage.run_dir(state.run_id)
    state_before = (run_dir / "state.json").read_bytes()
    audit_before = (run_dir / "audit_trail.jsonl").read_bytes()
    revision_before = state.state_revision

    with pytest.raises(ValueError, match="conflicts with the answer"):
        pipeline.submit_internal_answer(
            state.run_id,
            requested.question_id,
            "Vendor A cannot proceed because it is prohibited by policy.",
            confidence=1.0,
            interpretation="favorable",
        )

    persisted = V2Storage.load_state(state.run_id)
    persisted_question = next(
        question for question in persisted.internal_questions if question.question_id == requested.question_id
    )
    assert persisted.state_revision == revision_before
    assert persisted.internal_evidence == []
    assert persisted.decision_impacts == []
    assert persisted_question.status == "requested"
    assert persisted_question.answer_id is None
    assert (run_dir / "state.json").read_bytes() == state_before
    assert (run_dir / "audit_trail.jsonl").read_bytes() == audit_before


def test_explicit_high_confidence_disqualifier_prunes_once_and_cannot_be_reversed(pipeline):
    state = _run_vendor_case(
        pipeline,
        question="Should we select Acme or Globex?",
    )
    acme = next(hypothesis for hypothesis in state.hypotheses if "acme" in hypothesis.label.lower())
    state = _advance_to_category(pipeline, state, "constraints")

    state = pipeline.submit_internal_answer(
        state.run_id,
        _requested_question(state).question_id,
        "Acme is prohibited by policy and cannot proceed.",
        confidence=0.95,
        interpretation="unfavorable",
    )
    pruned = next(
        hypothesis for hypothesis in state.hypotheses if hypothesis.hypothesis_id == acme.hypothesis_id
    )
    assert pruned.status == "pruned"
    assert pruned.prune_rule == "explicit_high_confidence_disqualifier"
    assert pruned.pruned_by_evidence_id == state.internal_evidence[-1].evidence_id
    pruned_score = pruned.support_score
    pruning_evidence_id = pruned.pruned_by_evidence_id

    # Whether another material question remains or collection closes, the
    # disqualified action is immutable.
    if state.stop_evaluation.should_stop:
        assert not any(question.status == "requested" for question in state.internal_questions)
        state = pipeline.load_state(state.run_id)
    else:
        state = _submit_actionable_answer(pipeline, state)
    still_pruned = next(
        hypothesis for hypothesis in state.hypotheses if hypothesis.hypothesis_id == acme.hypothesis_id
    )
    assert still_pruned.status == "pruned"
    assert still_pruned.support_score == pruned_score
    assert still_pruned.pruned_by_evidence_id == pruning_evidence_id
    assert still_pruned.prune_rule == "explicit_high_confidence_disqualifier"


def test_graph_has_opposing_claim_edges_and_internal_evidence_effect_edges(pipeline):
    state = _run_vendor_case(
        pipeline,
        question="Should we select Acme or Globex?",
    )
    node_types = {node["id"]: node["type"] for node in state.graph["nodes"]}
    opposing = [edge for edge in state.graph["edges"] if edge["type"] == "opposes"]

    assert opposing
    assert all(node_types[edge["source"]] == "sourced_fact" for edge in opposing)
    assert all(node_types[edge["target"]] == "hypothesis" for edge in opposing)

    state = _submit_actionable_answer(pipeline, state)
    evidence_id = state.internal_evidence[-1].evidence_id
    node_types = {node["id"]: node["type"] for node in state.graph["nodes"]}
    causal_edges = [
        edge
        for edge in state.graph["edges"]
        if edge["source"] == evidence_id and edge["type"] in {"supports", "opposes", "no_material_effect"}
    ]

    assert node_types[evidence_id] == "internal_evidence"
    assert causal_edges
    assert {edge["target"] for edge in causal_edges} == {
        hypothesis.hypothesis_id for hypothesis in state.hypotheses
    }
    assert all(node_types[edge["target"]] == "hypothesis" for edge in causal_edges)
    assert all({"delta", "before_score", "after_score", "revision"} <= edge.keys() for edge in causal_edges)


def test_api_rejects_malformed_json_root_document_and_question_shapes(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_api_shape_runs")
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    responses = {
        "malformed_json": client.post(
            "/api/v2/run",
            data='{"documents":',
            content_type="application/json",
        ),
        "array_root": client.post("/api/v2/run", json=[]),
        "scalar_document": client.post(
            "/api/v2/run",
            json={"question": "Should we proceed?", "documents": ["not-an-object"]},
        ),
        "array_question": client.post(
            "/api/v2/run",
            json={
                "question": ["Should we proceed?"],
                "documents": [{"filename": "report.md", "text": VENDOR_REPORT}],
            },
        ),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "malformed_json": 400,
        "array_root": 400,
        "scalar_document": 400,
        "array_question": 400,
    }


@pytest.mark.parametrize(
    "bad_confidence",
    ["not-a-number", None, [], {"unexpected": "object"}, 1.01, float("nan")],
    ids=["text", "null", "array", "object", "out-of-range", "nan"],
)
def test_api_rejects_malformed_confidence_as_client_error(
    tmp_path,
    monkeypatch,
    bad_confidence,
):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_api_confidence_runs")
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    created = client.post(
        "/api/v2/run",
        json={
            "question": "Should we choose Vendor A or Vendor B?",
            "documents": [{"filename": "report.md", "text": VENDOR_REPORT}],
        },
    )
    assert created.status_code == 200
    state = created.get_json()["data"]
    requested = next(
        question for question in state["internal_questions"] if question["status"] == "requested"
    )

    response = client.post(
        f"/api/v2/runs/{state['run_id']}/answers",
        json={
            "question_id": requested["question_id"],
            "answer": "The approved budget and committed capacity are sufficient.",
            "confidence": bad_confidence,
            "interpretation": "favorable",
        },
    )

    assert response.status_code == 400
    assert V2Storage.load_state(state["run_id"]).internal_evidence == []


def test_audit_jsonl_is_prefix_preserving_and_state_snapshots_are_monotonic(pipeline):
    state = _run_vendor_case(pipeline)
    run_dir = V2Storage.run_dir(state.run_id)
    audit_path = run_dir / "audit_trail.jsonl"
    first_prefix = audit_path.read_bytes()
    first_revision = state.state_revision

    state = _submit_actionable_answer(pipeline, state)
    second_prefix = audit_path.read_bytes()
    second_revision = state.state_revision
    assert second_prefix.startswith(first_prefix)
    assert len(second_prefix) > len(first_prefix)
    assert second_revision > first_revision

    unchanged_audit_state = V2Storage.load_state(state.run_id)
    V2Storage.save_state(unchanged_audit_state)
    third_prefix = audit_path.read_bytes()
    third_revision = unchanged_audit_state.state_revision
    assert third_prefix == second_prefix
    assert third_revision > second_revision

    snapshot_paths = sorted((run_dir / "graph_revisions").glob("revision_*.json"))
    snapshot_revisions = [int(path.stem.rsplit("_", 1)[1]) for path in snapshot_paths]
    assert snapshot_revisions == list(range(first_revision, third_revision + 1))
    snapshot_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in snapshot_paths]
    assert [payload["state_revision"] for payload in snapshot_payloads] == snapshot_revisions
    assert [payload["revision"] for payload in snapshot_payloads] == sorted(
        payload["revision"] for payload in snapshot_payloads
    )

    event_ids = [
        json.loads(line)["event_id"]
        for line in third_prefix.decode("utf-8").splitlines()
    ]
    assert len(event_ids) == len(set(event_ids))


def test_import_and_internal_answer_never_call_model_entrypoints(pipeline, monkeypatch):
    def fail_model_call(*_args, **_kwargs):
        raise AssertionError("v2 decision-layer code attempted to call a model entrypoint")

    monkeypatch.setattr(LLMClient, "__init__", fail_model_call)
    monkeypatch.setattr(LLMClient, "chat", fail_model_call)
    monkeypatch.setattr(LLMClient, "chat_json", fail_model_call)
    monkeypatch.setattr("app.utils.llm_client.OpenAI", fail_model_call)

    state = _run_vendor_case(pipeline)
    state = _submit_actionable_answer(pipeline, state)

    assert state.token_usage.processing_mode == "local_deterministic"
    assert state.token_usage.external_llm_calls == 0
    assert state.token_usage.total_tokens == 0
