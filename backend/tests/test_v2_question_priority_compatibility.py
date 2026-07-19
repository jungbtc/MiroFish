from app.v2.decision import QUESTION_PRIORITY_FORMULA
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.schemas import InternalQuestion, StopEvaluation
from app.v2.scoring import ScenarioScoringService
from app.v2.storage import V2Storage


def test_legacy_priority_fields_parse_but_new_json_emits_corrected_names():
    question = InternalQuestion.model_validate(
        {
            "question_id": "question_budget",
            "question": "What budget is approved?",
            "category": "financial_capacity",
            "rationale": "The approved budget can change the feasible path.",
            "owner_hint": "CFO",
            "information_value_score": 62.5,
            "value_components": {
                "decision_sensitivity": 0.7,
                "uncertainty": 0.6,
                "answerability": 0.8,
                "urgency": 0.5,
            },
            "expected_change": "May disqualify an unfunded action.",
        }
    )
    payload = question.model_dump(mode="json")

    assert question.question_priority_score == 62.5
    assert payload["question_priority_score"] == 62.5
    assert "information_value_score" not in payload
    assert question.value_components.formula == QUESTION_PRIORITY_FORMULA

    stop = StopEvaluation.model_validate(
        {
            "reason": "Continue",
            "remaining_information_value": 62.5,
            "highest_unanswered_score": 62.5,
        }
    )
    stop_payload = stop.model_dump(mode="json")
    assert stop_payload["remaining_question_priority"] == 62.5
    assert stop_payload["highest_unanswered_priority"] == 62.5
    assert "remaining_information_value" not in stop_payload
    assert "highest_unanswered_score" not in stop_payload


def test_active_pipeline_never_calls_deprecated_fixed_probability_scorer(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "priority_runs")

    def forbidden_score(*_args, **_kwargs):
        raise AssertionError("deprecated fixed-probability scoring was called")

    monkeypatch.setattr(ScenarioScoringService, "score", forbidden_score)
    state = MiroFishV2Pipeline().run_from_inline_documents(
        [
            {
                "filename": "completed-report.md",
                "text": (
                    "The completed simulation found that a staged pilot preserves "
                    "optionality while the immediate commitment has execution risk."
                ),
            }
        ],
        "Should the organization commit now, stage a pilot, or defer?",
        "Question priority compatibility",
    )

    assert state.run_type == "public"
    assert state.internal_questions
    assert all(
        "question_priority_score" in item.model_dump(mode="json")
        for item in state.internal_questions
    )
