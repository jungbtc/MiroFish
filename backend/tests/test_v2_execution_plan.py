import pytest

from app import create_app
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.storage import V2Storage


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_runs")
    return MiroFishV2Pipeline()


def test_binding_evidence_compiles_into_complete_execution_contract(pipeline):
    public = pipeline.run_from_inline_documents(
        [{
            "filename": "priority-pass.md",
            "text": (
                "A subscription pilot could affect labor workload, customer wait time, "
                "conversion, contribution margin, and union consultation."
            ),
        }],
        question=(
            "Should Starbucks redesign Priority Pass, run a controlled pilot, "
            "proceed nationally, or cancel the initiative?"
        ),
        project_name="Priority Pass execution compiler",
    )
    state = pipeline.fork_public_run(public.run_id)
    answers = {
        "strategic_success": (
            "Expansion requires at least 3% incremental subscriber transactions, 4% paid "
            "conversion, and $1.25 contribution for each $1 of incremental cost. Non-member "
            "wait may not increase by more than 45 seconds."
        ),
        "constraints": (
            "Union stores are not permitted until Labor Relations clearance is complete. "
            "Orders already in preparation must not be displaced. A store manager may suspend "
            "the benefit immediately after a compliance incident."
        ),
        "financial_capacity": (
            "Finance approved $6.5 million total, but only a $2.25 million initial 30-day tranche. "
            "Expansion is blocked if projected pilot loss exceeds $3 million."
        ),
        "execution_capacity": (
            "SVP U.S. Store Operations owns delivery. Stage one is capped at 75 stores and "
            "10 incremental labor hours per store per week."
        ),
    }
    submitters = {
        "strategic_success": "Chief Strategy Officer",
        "constraints": "Chief Legal Officer",
        "financial_capacity": "Chief Financial Officer",
        "execution_capacity": "SVP U.S. Store Operations",
    }

    for _ in range(4):
        if state.stop_evaluation.should_stop:
            break
        question = next(item for item in state.internal_questions if item.status == "requested")
        state = pipeline.submit_internal_answer(
            state.run_id,
            question.question_id,
            answers[question.category],
            submitted_by=submitters[question.category],
            confidence=1.0,
        )
        assert state.internal_evidence[-1].decision_usable is True, question.category
    assert state.stop_evaluation.should_stop is True

    state = pipeline.confirm_decision_actions(
        state.run_id,
        [item.hypothesis_id for item in state.hypotheses],
        confirmed_by="Chief Strategy Officer",
    )
    state = pipeline.waive_quantitative_decision_analysis(
        state.run_id,
        confirmed_by="Chief Strategy Officer",
    )

    plan = state.execution_plan
    assert plan is not None
    assert [item.action_type for item in plan.actions] == [
        "COMMIT",
        "DESIGN",
        "BUILD",
        "VALIDATE",
        "GATE",
        "PAUSE_REVERSE",
    ]
    assert plan.coverage["complete"] is True
    assert plan.coverage["coverage_percent"] == 100.0
    assert plan.executability["score"] >= 80
    assert plan.executability["hard_failures"] == []
    assert plan.ready is True
    assert state.decision_completion["execution_plan_complete"] is True
    assert state.decision_completion["final_approval_ready"] is True
    assert state.report.status == "final"

    fact_types = {item.fact_type for item in plan.facts}
    assert {"budget", "capacity", "hard_constraint", "success_metric", "guardrail"} <= fact_types
    assert any("$2.25 million" in item.statement for item in plan.facts)
    assert all(
        action.owner
        and action.accountable_executive
        and action.deliverable
        and action.deadline
        and action.budget_or_capacity
        and action.acceptance_criteria
        and action.failure_response
        for action in plan.actions
    )
    assert all(action.evidence_source_ids for action in plan.actions)
    assert "## 1A. Decision Execution Plan" in state.report.markdown
    assert "Decision-relevant evidence not operationalized" not in state.report.markdown

    original_rounds = list(state.rounds)
    reassigned = pipeline.assign_execution_owners(
        state.run_id,
        {
            "VALIDATE": "VP Decision Analytics",
            "GATE": "Chief Financial Officer",
        },
    )
    owners = {item.action_type: item.owner for item in reassigned.execution_plan.actions}
    assert owners["VALIDATE"] == "VP Decision Analytics"
    assert owners["GATE"] == "Chief Financial Officer"
    assert reassigned.execution_plan.ready is True
    assert reassigned.decision_completion["final_approval_ready"] is True
    assert reassigned.rounds == original_rounds
    assert any(
        event.event_type == "execution_owners_assigned"
        and event.details["simulation_rerun"] is False
        for event in reassigned.audit_trail
    )


def test_execution_validator_fails_closed_on_missing_resources_and_named_owners(pipeline):
    public = pipeline.run_from_inline_documents(
        [{"filename": "case.md", "text": "A staged pilot is under consideration."}],
        question="Should the company run a staged pilot or defer the initiative?",
        project_name="Incomplete execution case",
    )
    state = pipeline.fork_public_run(public.run_id)

    for _ in range(4):
        if state.stop_evaluation.should_stop:
            break
        question = next(item for item in state.internal_questions if item.status == "requested")
        answer = {
            "strategic_success": "Success means improving retention by at least 5%.",
            "constraints": "The pilot is permitted after legal review.",
            "financial_capacity": "Finance approved a pilot budget, but the amount is not specified.",
            "execution_capacity": "Operations confirmed capacity exists, but no owner or capacity limit is specified.",
        }[question.category]
        state = pipeline.submit_internal_answer(
            state.run_id,
            question.question_id,
            answer,
            submitted_by="decision_owner",
            confidence=1.0,
        )
        assert state.internal_evidence[-1].decision_usable is True, question.category
    assert state.stop_evaluation.should_stop is True

    plan = state.execution_plan
    assert plan is not None
    assert plan.ready is False
    assert any("placeholder ownership" in item for item in plan.executability["hard_failures"])
    assert any("budget or capacity allocation" in item for item in plan.executability["hard_failures"])

    state = pipeline.confirm_decision_actions(
        state.run_id,
        [item.hypothesis_id for item in state.hypotheses],
        confirmed_by="decision-owner",
    )
    state = pipeline.waive_quantitative_decision_analysis(
        state.run_id,
        confirmed_by="decision-owner",
    )
    app = create_app()
    app.config.update(TESTING=True, V2_REQUIRE_AUTH=False, V2_API_KEY="")
    response = app.test_client().post(
        f"/api/v2/runs/{state.run_id}/execution-owners",
        json={
            "owners": {
                "VALIDATE": "VP Decision Analytics",
                "GATE": "Chief Financial Officer",
            }
        },
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]["run"]
    assert payload["execution_owner_assignments"] == {
        "VALIDATE": "VP Decision Analytics",
        "GATE": "Chief Financial Officer",
    }
    remaining_failures = payload["execution_plan"]["executability"]["hard_failures"]
    assert not any(
        failure.startswith(("A-04:", "A-05:"))
        and "placeholder ownership" in failure
        for failure in remaining_failures
    )
