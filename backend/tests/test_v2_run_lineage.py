import pytest

from app import create_app
from app.v2.authorization import ActorContext, PublicRunRequiresFork
from app.v2.decision import DecisionIntelligenceService
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.schemas import V2RunState
from app.v2.storage import ImmutableRunError, V2Storage


ACTIONABLE_ANSWERS = {
    "strategic_success": "The verified minimum outcome is 20% growth and the staged path meets it.",
    "constraints": "The immediate path is blocked by contract and cannot proceed.",
    "financial_capacity": "Only the staged pilot budget is approved; immediate commitment has no approved budget.",
    "execution_capacity": "The staged pilot has a confirmed owner and sufficient capacity.",
    "risk_tolerance": "The organization accepts only the reversible staged downside.",
    "timing": "The verified deadline allows a staged pilot before commitment.",
}


@pytest.fixture
def public_state(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "lineage_runs")
    run_id = "v2_20260718010101_abcde123"
    state = V2RunState(
        run_id=run_id,
        run_type="public",
        root_public_run_id=run_id,
        status="awaiting_decision_confirmation",
        project_name="Lineage test",
        question="Should the organization choose an immediate or staged commitment?",
        workflow_origin="core_mirofish_report",
    )
    DecisionIntelligenceService().initialize(state)
    V2Storage.save_state(state)
    return V2Storage.load_state(run_id)


def _requested(state):
    return next(item for item in state.internal_questions if item.status == "requested")


def test_public_mutation_requires_explicit_fork_and_sealed_state_is_immutable(public_state):
    question = _requested(public_state)
    with pytest.raises(PublicRunRequiresFork):
        MiroFishV2Pipeline().submit_internal_answer(
            public_state.run_id,
            question.question_id,
            ACTIONABLE_ANSWERS[question.category],
        )

    child = MiroFishV2Pipeline().fork_public_run(public_state.run_id)
    parent = V2Storage.load_state(public_state.run_id)
    assert parent.sealed_at
    assert parent.status == "sealed"
    assert child.run_type == "internal"
    assert child.parent_run_id == parent.run_id
    assert child.root_public_run_id == parent.run_id

    parent.project_name = "attempted overwrite"
    with pytest.raises(ImmutableRunError):
        V2Storage.save_state(parent)


def test_internal_ownership_is_enforced_for_reads_and_lineage(public_state):
    owner = ActorContext(actor_id="shared-key:owner")
    outsider = ActorContext(actor_id="shared-key:outsider")
    pipeline = MiroFishV2Pipeline()
    child = pipeline.fork_public_run(public_state.run_id, actor=owner)

    assert pipeline.load_state(child.run_id, actor=owner).run_id == child.run_id
    with pytest.raises(PermissionError):
        pipeline.load_state(child.run_id, actor=outsider)
    assert pipeline.load_state(public_state.run_id, actor=outsider).run_type == "public"

    lineage = pipeline.lineage(child.run_id, actor=owner)
    assert lineage["root_public_run_id"] == public_state.run_id
    assert [item["run_id"] for item in lineage["ancestors"]] == [public_state.run_id]


def test_compare_and_retraction_replay_from_parent_plus_active_evidence(public_state):
    pipeline = MiroFishV2Pipeline()
    child = pipeline.fork_public_run(public_state.run_id)
    question = _requested(child)
    answered = pipeline.submit_internal_answer(
        child.run_id,
        question.question_id,
        ACTIONABLE_ANSWERS[question.category],
        confidence=1.0,
    )
    evidence_id = answered.internal_evidence[-1].evidence_id

    comparison = pipeline.compare_runs(public_state.run_id, child.run_id)
    assert [item["evidence_id"] for item in comparison["changed_evidence"]["added"]] == [
        evidence_id
    ]
    assert "changed_distributions" in comparison
    assert "expected_utility" in comparison
    assert "expected_regret" in comparison
    assert "evpi" in comparison

    replayed = pipeline.retract_internal_evidence(
        child.run_id,
        evidence_id,
        reason="The source owner withdrew the value.",
    )
    retracted = next(item for item in replayed.internal_evidence if item.evidence_id == evidence_id)
    assert retracted.retracted is True
    assert retracted.retracted_at
    assert retracted.outbound_external_use is False
    assert all(item.evidence_id != evidence_id for item in replayed.decision_impacts)

    parent = V2Storage.load_state(public_state.run_id)
    assert [item.support_score for item in replayed.hypotheses] == [
        item.support_score for item in parent.hypotheses
    ]
    assert any(
        item.event_type == "internal_evidence_retracted" for item in replayed.audit_trail
    )


def test_public_answer_api_returns_structured_needs_fork(public_state):
    app = create_app()
    app.config.update(TESTING=True, V2_REQUIRE_AUTH=False, V2_API_KEY="")
    question = _requested(public_state)
    response = app.test_client().post(
        f"/api/v2/runs/{public_state.run_id}/answers",
        json={
            "question_id": question.question_id,
            "answer": ACTIONABLE_ANSWERS[question.category],
        },
    )
    assert response.status_code == 409
    assert response.get_json()["code"] == "needs_fork"
