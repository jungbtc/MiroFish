import json

import pytest

from app import create_app
from app.config import Config
from app.v2.decision import DecisionIntelligenceService
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.schemas import InternalEvidence, V2RunState
from app.v2.storage import V2Storage
from decision_analysis_fixtures import binary_decision_model


@pytest.fixture
def decision_case(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "decision_runs")
    monkeypatch.setattr(Config, "CONFIDENTIAL_STORAGE_MODE", "local_development")
    public_id = "v2_20260718020202_abcd1234"
    public = V2RunState(
        run_id=public_id,
        run_type="public",
        root_public_run_id=public_id,
        status="awaiting_decision_confirmation",
        project_name="Decision analysis integration",
        question="Should we choose the safe or risky launch?",
    )
    DecisionIntelligenceService().initialize(public)
    V2Storage.save_state(public)
    child = MiroFishV2Pipeline().fork_public_run(public_id)

    app = create_app()
    app.config.update(TESTING=True, V2_REQUIRE_AUTH=False, V2_API_KEY="")
    return app.test_client(), public_id, child.run_id


def _model_payload():
    # Deliberately contains forged approval claims. The proposal endpoint must
    # discard all of them and require the separate confirmation operation.
    return binary_decision_model().model_dump(mode="json")


def _propose(client, run_id):
    response = client.post(
        f"/api/v2/runs/{run_id}/decision-model/proposals",
        json={"model": _model_payload(), "proposed_by": "planning_assistant"},
    )
    assert response.status_code == 201
    return response.get_json()["data"]["proposal"]


def _confirm(client, run_id, proposal_id):
    return client.post(
        f"/api/v2/runs/{run_id}/decision-model/confirm",
        json={
            "proposal_id": proposal_id,
            "confirm_actions": True,
            "confirm_consequence_unit": True,
            "confirm_distributions": True,
            "confirm_utility_model": True,
            "seed": 77,
            "sample_count": 10_000,
        },
    )


def test_proposal_confirmation_and_separate_trace_are_enforced(decision_case):
    client, _public_id, child_id = decision_case
    proposal = _propose(client, child_id)

    assert proposal["status"] == "proposed"
    assert proposal["model"]["approval_status"] == "proposed"
    assert all(action["status"] == "proposed" for action in proposal["model"]["actions"])
    assert all(
        variable["distribution"]["approval_status"] == "proposed"
        for variable in proposal["model"]["uncertain_variables"]
    )
    saved = V2Storage.load_state(child_id)
    assert saved.decision_model is None
    assert saved.decision_analysis_result is None

    incomplete = client.post(
        f"/api/v2/runs/{child_id}/decision-model/confirm",
        json={
            "proposal_id": proposal["proposal_id"],
            "confirm_actions": True,
            "confirm_consequence_unit": True,
            "confirm_distributions": False,
            "confirm_utility_model": True,
        },
    )
    assert incomplete.status_code == 200
    missing = incomplete.get_json()["data"]["analysis"]
    assert missing["status"] == "needs_confirmation"
    assert [item["field"] for item in missing["missing_confirmations"]] == [
        "distributions"
    ]
    assert V2Storage.load_state(child_id).decision_model is None

    confirmed = _confirm(client, child_id, proposal["proposal_id"])
    assert confirmed.status_code == 200
    analysis = confirmed.get_json()["data"]["analysis"]
    assert analysis["status"] == "calculated"
    assert analysis["method"] == "exact_enumeration"
    assert analysis["sample_count"] == 0
    assert analysis["expected_utility_by_action"] == pytest.approx(
        {"safe": 40.0, "risky": 30.0}
    )
    assert analysis["evpi"] == pytest.approx(18.0)
    assert "trace" not in analysis

    state = V2Storage.load_state(child_id)
    assert state.decision_model["approval_status"] == "approved"
    assert state.decision_analysis_trace_id
    trace_path = V2Storage.calculation_trace_path(
        child_id, state.decision_analysis_trace_id
    )
    assert trace_path.is_file()
    state_json = json.loads(V2Storage.state_path(child_id).read_text(encoding="utf-8"))
    assert "trace" not in state_json["decision_analysis_result"]
    assert state_json.get("decision_analysis_trace") is None

    trace_response = client.get(
        f"/api/v2/runs/{child_id}/decision-analysis/traces/"
        f"{state.decision_analysis_trace_id}"
    )
    assert trace_response.status_code == 200
    assert trace_response.get_json()["data"]["trace_id"] == state.decision_analysis_trace_id


def test_public_evaluation_requires_fork_and_unmodeled_child_lists_confirmations(
    decision_case,
):
    client, public_id, child_id = decision_case
    public_response = client.post(
        f"/api/v2/runs/{public_id}/decision-analysis/evaluate",
        json={},
    )
    assert public_response.status_code == 409
    assert public_response.get_json()["code"] == "needs_fork"

    child_response = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evaluate",
        json={},
    )
    assert child_response.status_code == 200
    outcome = child_response.get_json()["data"]["analysis"]
    assert outcome["status"] == "needs_confirmation"
    assert [item["field"] for item in outcome["missing_confirmations"]] == [
        "actions",
        "consequence_unit",
        "uncertain_variables",
        "utility_model",
    ]


def test_confirmation_preserves_all_explicit_calculation_options(decision_case):
    client, _public_id, child_id = decision_case
    proposal = _propose(client, child_id)
    response = client.post(
        f"/api/v2/runs/{child_id}/decision-model/confirm",
        json={
            "proposal_id": proposal["proposal_id"],
            "confirm_actions": True,
            "confirm_consequence_unit": True,
            "confirm_distributions": True,
            "confirm_utility_model": True,
            "seed": 91,
            "sample_count": 4_000,
            "force_method": "monte_carlo",
            "information_costs": {"demand": {"cash_cost": 5.0}},
            "evppi_groups": {"market": ["demand", "regulatory"]},
        },
    )

    assert response.status_code == 200
    analysis = response.get_json()["data"]["analysis"]
    assert analysis["method"] == "monte_carlo"
    assert analysis["seed"] == 91
    assert analysis["sample_count"] == 4_000
    state = V2Storage.load_state(child_id)
    options = state.decision_analysis_options
    assert options["seed"] == 91
    assert options["sample_count"] == 4_000
    assert options["force_method"] == "monte_carlo"
    assert options["evppi_groups"] == {"market": ["demand", "regulatory"]}
    assert options["information_costs"]["demand"]["total_cost"] == 5.0
    assert options["information_costs"]["regulatory"]["total_cost"] == 0.0


def test_confirmed_internal_observation_updates_distribution_then_recalculates(
    decision_case,
):
    client, public_id, child_id = decision_case
    proposal = _propose(client, child_id)
    assert _confirm(client, child_id, proposal["proposal_id"]).status_code == 200

    state = V2Storage.load_state(child_id)
    state.internal_evidence.append(
        InternalEvidence(
            evidence_id="evidence_confirmed_demand",
            question_id="question_confirmed_demand",
            answer="The signed commitments support the high-demand case.",
            interpretation="A structured distribution proposal may be reviewed.",
            confidential=True,
            visibility="restricted",
            classification="commercial_confidential",
            outbound_external_use=False,
        )
    )
    V2Storage.save_state(state)

    proposed = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evidence-proposals",
        json={
            "observation": {
                "variable_id": "demand",
                "observation_type": "categorical_probabilities",
                "value": {"low": 0.2, "high": 0.8},
                "effective_date": "2026-07-18",
                "reliability_model": "Human-confirmed contract coverage",
                "source_evidence_id": "evidence_confirmed_demand",
            }
        },
    )
    assert proposed.status_code == 201
    update_proposal = proposed.get_json()["data"]["proposal"]
    before = V2Storage.load_state(child_id)
    assert before.decision_model["uncertain_variables"][0]["distribution"]["parameters"][
        "probabilities"
    ] == {"low": 0.7, "high": 0.3}

    confirmed = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evidence-proposals/"
        f"{update_proposal['proposal_id']}/confirm",
        json={"confirmed": True},
    )
    assert confirmed.status_code == 200
    outcome = confirmed.get_json()["data"]["outcome"]
    assert outcome["proposal"]["status"] == "applied"
    assert outcome["analysis"]["recommended_action"] == "risky"
    assert outcome["analysis"]["expected_utility_by_action"]["risky"] == pytest.approx(80.0)
    after = V2Storage.load_state(child_id)
    assert after.internal_evidence[-1].distribution_application_status == "applied"
    assert after.decision_model["uncertain_variables"][0]["evidence_ids"] == [
        "evidence_confirmed_demand"
    ]
    comparison = client.get(
        f"/api/v2/runs/{public_id}/compare/{child_id}"
    ).get_json()["data"]
    assert comparison["changed_distributions"]["available"] is True
    assert comparison["changed_distributions"]["changes"][0]["variable_id"] == "demand"
    assert comparison["expected_utility"]["child"] == pytest.approx(
        {"safe": 40.0, "risky": 80.0}
    )
    assert comparison["recommendation"]["child"] == "risky"
    assert comparison["expected_regret"]["child"] == pytest.approx(
        {"safe": 48.0, "risky": 8.0}
    )
    assert comparison["remaining_evpi"] == pytest.approx(8.0)
    assert comparison["calculation"]["child_seed"] == 77
    assert comparison["calculation"]["child_model_hash"]


def test_evidence_recalculation_preserves_nondefault_analysis_options(decision_case):
    client, _public_id, child_id = decision_case
    proposal = _propose(client, child_id)
    assert _confirm(client, child_id, proposal["proposal_id"]).status_code == 200

    evaluated = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evaluate",
        json={
            "seed": 313,
            "sample_count": 500,
            "force_method": "monte_carlo",
            "information_costs": {"demand": {"cash_cost": 3.0}},
            "evppi_groups": {"joint": ["demand", "regulatory"]},
        },
    )
    assert evaluated.status_code == 200
    initial = evaluated.get_json()["data"]["analysis"]
    assert initial["method"] == "monte_carlo"
    assert initial["seed"] == 313
    assert initial["sample_count"] == 500
    assert initial["information_costs"]["demand"]["total_cost"] == pytest.approx(3.0)
    assert "joint" in initial["evppi_by_group"]

    state = V2Storage.load_state(child_id)
    state.internal_evidence.append(
        InternalEvidence(
            evidence_id="evidence_option_replay",
            question_id="question_option_replay",
            answer="Confirmed demand evidence for the replay test.",
            interpretation="A structured probability update may be reviewed.",
            confidential=True,
            visibility="restricted",
            classification="commercial_confidential",
            outbound_external_use=False,
        )
    )
    V2Storage.save_state(state)

    update = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evidence-proposals",
        json={
            "observation": {
                "variable_id": "demand",
                "observation_type": "categorical_probabilities",
                "value": {"low": 0.2, "high": 0.8},
                "source_evidence_id": "evidence_option_replay",
            }
        },
    )
    assert update.status_code == 201
    update_id = update.get_json()["data"]["proposal"]["proposal_id"]

    confirmed = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evidence-proposals/"
        f"{update_id}/confirm",
        json={"confirmed": True},
    )
    assert confirmed.status_code == 200
    replayed = confirmed.get_json()["data"]["outcome"]["analysis"]
    assert replayed["method"] == "monte_carlo"
    assert replayed["seed"] == 313
    assert replayed["sample_count"] == 500
    assert replayed["information_costs"]["demand"]["total_cost"] == pytest.approx(3.0)
    assert "joint" in replayed["evppi_by_group"]

    saved = V2Storage.load_state(child_id)
    assert saved.decision_analysis_options["force_method"] == "monte_carlo"
    assert saved.decision_analysis_options["seed"] == 313
    assert saved.decision_analysis_options["sample_count"] == 500
    assert saved.decision_analysis_options["evppi_groups"] == {
        "joint": ["demand", "regulatory"]
    }
    assert saved.decision_analysis_options["information_costs"]["demand"][
        "total_cost"
    ] == pytest.approx(3.0)


def test_retraction_replays_base_model_plus_only_active_confirmed_observations(
    decision_case,
):
    client, _public_id, child_id = decision_case
    proposal = _propose(client, child_id)
    assert _confirm(client, child_id, proposal["proposal_id"]).status_code == 200

    state_payload = client.get(f"/api/v2/runs/{child_id}").get_json()["data"]
    question = next(
        item for item in state_payload["internal_questions"] if item["status"] == "requested"
    )
    answer_response = client.post(
        f"/api/v2/runs/{child_id}/answers",
        json={
            "question_id": question["question_id"],
            "answer": "The signed commitments confirm this fact is approved and sufficient.",
            "confidence": 1.0,
            "confidential": True,
        },
    )
    assert answer_response.status_code == 200
    evidence_id = answer_response.get_json()["data"]["internal_evidence"][-1][
        "evidence_id"
    ]

    update = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evidence-proposals",
        json={
            "observation": {
                "variable_id": "demand",
                "observation_type": "categorical_probabilities",
                "value": {"low": 0.2, "high": 0.8},
                "source_evidence_id": evidence_id,
            }
        },
    ).get_json()["data"]["proposal"]
    applied = client.post(
        f"/api/v2/runs/{child_id}/decision-analysis/evidence-proposals/"
        f"{update['proposal_id']}/confirm",
        json={"confirmed": True},
    )
    assert applied.status_code == 200
    assert applied.get_json()["data"]["outcome"]["analysis"]["recommended_action"] == "risky"

    retracted = client.post(
        f"/api/v2/runs/{child_id}/evidence/{evidence_id}/retract",
        json={"reason": "The commitment record was withdrawn."},
    )
    assert retracted.status_code == 200
    replayed = V2Storage.load_state(child_id)
    distribution = replayed.decision_model["uncertain_variables"][0]["distribution"]
    assert distribution["parameters"]["probabilities"] == {"low": 0.7, "high": 0.3}
    assert replayed.decision_analysis_result["recommended_action"] == "safe"
    assert replayed.decision_analysis_result["expected_utility_by_action"] == pytest.approx(
        {"safe": 40.0, "risky": 30.0}
    )
    evidence = next(
        item for item in replayed.internal_evidence if item.evidence_id == evidence_id
    )
    assert evidence.retracted is True
    assert evidence.distribution_application_status == "not_proposed"
    assert any(
        item.get("status") == "source_retracted"
        for item in replayed.evidence_update_proposals
    )
    replay_event = next(
        item
        for item in reversed(replayed.audit_trail)
        if item.event_type == "internal_evidence_retracted"
    )
    assert replay_event.details["decision_analysis_replay"]["status"] == "calculated"
    assert replay_event.details["decision_analysis_replay"][
        "excluded_retracted_observations"
    ] == 1
