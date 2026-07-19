from types import SimpleNamespace

from app.v2.decision import (
    MATERIALITY_THRESHOLD,
    MAX_INTERNAL_QUESTIONS,
    is_executable_action_label,
)
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.refinement import CoreRefinementService
from app.v2.storage import V2Storage


class FakeResponses:
    def __init__(self):
        self.created = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id="unexpected_research", status="queued")


def _service(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "core_refinement_runs")
    responses = FakeResponses()
    return CoreRefinementService(client=SimpleNamespace(responses=responses)), responses


def _initialize(service, **overrides):
    values = {
        "project_id": "project_1",
        "graph_id": "graph_1",
        "simulation_id": "sim_1",
        "report_id": "report_1",
        "project_name": "Capacity Decision",
        "decision_question": "Should we proceed immediately or stage the capacity commitment?",
        "report_markdown": "# Initial report\nThe immediate and staged paths remain open because internal constraints are unknown.",
        "graph_evidence": {"public_summary": "market structure"},
        "simulation_metadata": {"rounds": 10},
    }
    values.update(overrides)
    return service.initialize_from_core_report(**values)


def test_core_report_immediately_opens_bounded_internal_refinement(tmp_path, monkeypatch):
    service, responses = _service(tmp_path, monkeypatch)

    state = _initialize(service)

    assert responses.created == []
    assert state.research_job is None
    assert state.public_research_context == {}
    assert state.workflow_stage == "internal_evidence_refinement"
    assert state.hypotheses
    assert state.internal_questions
    assert len(state.internal_questions) <= MAX_INTERNAL_QUESTIONS
    assert all(
        question.question_priority_score >= MATERIALITY_THRESHOLD
        for question in state.internal_questions
    )
    assert all(len(question.question) <= 320 for question in state.internal_questions)
    assert all(state.question not in question.question for question in state.internal_questions)
    assert sum(question.status == "requested" for question in state.internal_questions) == 1
    assert "does not launch another public research process" in state.report.markdown


def test_imported_reports_use_the_same_finite_question_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "imported_report_runs")
    pipeline = MiroFishV2Pipeline()
    public_state = pipeline.run_from_inline_documents(
        [
            {
                "filename": "completed-mirofish-report.md",
                "text": (
                    "Proceed now and stage a reversible pilot have comparable public support. "
                    "Internal constraints, budget, execution capacity, risk tolerance, and timing remain unknown."
                ),
            }
        ],
        question="Should Northstar proceed now, stage a reversible pilot, or defer?",
        project_name="Imported report",
    )
    child_state = pipeline.fork_public_run(public_state.run_id)

    assert child_state.workflow_origin == "legacy_research_import"
    assert 0 < len(child_state.internal_questions) <= MAX_INTERNAL_QUESTIONS
    assert sum(question.status == "requested" for question in child_state.internal_questions) == 1


def test_long_simulation_prompt_gets_a_short_case_title(tmp_path, monkeypatch):
    service, _responses = _service(tmp_path, monkeypatch)
    prompt = (
        "We have just reported record Q2 2026 operating profit, driven largely by AI-memory demand, "
        "but the market remains skeptical. Simulate what would happen if Samsung Electronics announces "
        "that it will aggressively expand HBM4 and advanced-packaging capacity only where demand is backed "
        "by long-term customer commitments."
    )

    state = _initialize(
        service,
        project_name="Unnamed Project",
        decision_question=prompt,
    )

    assert state.case_title == "Samsung HBM4 Capacity Strategy"
    assert state.project_name == state.case_title
    assert state.case_title != prompt
    assert len(state.case_title) <= 80


def test_answer_reevaluates_only_the_initial_finite_question_set(tmp_path, monkeypatch):
    service, responses = _service(tmp_path, monkeypatch)
    state = _initialize(service)
    state = MiroFishV2Pipeline().fork_public_run(state.run_id)
    original_ids = {question.question_id for question in state.internal_questions}
    requested = next(question for question in state.internal_questions if question.status == "requested")
    answers = {
        "strategic_success": "The verified minimum outcome is 20% growth and the staged path meets it.",
        "constraints": "The immediate path is blocked by contract and cannot proceed.",
        "financial_capacity": "Only the staged pilot budget is approved; immediate commitment has no approved budget.",
        "execution_capacity": "The staged pilot has a confirmed owner and sufficient capacity.",
        "risk_tolerance": "The organization accepts only the reversible staged downside.",
        "timing": "The verified deadline allows a staged pilot before commitment.",
    }

    updated = MiroFishV2Pipeline().submit_internal_answer(
        state.run_id,
        requested.question_id,
        answers[requested.category],
        confidence=1.0,
        confidential=True,
    )

    assert {question.question_id for question in updated.internal_questions} <= original_ids
    assert len(updated.internal_questions) <= MAX_INTERNAL_QUESTIONS
    assert updated.targeted_reevaluations
    assert updated.internal_evidence[-1].outbound_external_use is False
    assert responses.created == []
    assert "## Targeted Re-evaluation Record" in updated.report.markdown


def test_saved_research_gated_run_is_migrated_in_place(tmp_path, monkeypatch):
    service, responses = _service(tmp_path, monkeypatch)
    state = _initialize(
        service,
        project_name="Unnamed Project",
        decision_question="Simulate what happens if Samsung Electronics expands HBM4 capacity.",
    )
    state.case_title = None
    state.workflow_stage = "deep_research_failed"
    from app.v2.schemas import ResearchJobState
    state.research_job = ResearchJobState(job_id="old_job", status="failed")
    state.hypotheses = []
    state.internal_questions = []
    V2Storage.save_state(state)

    migrated = service.migrate_core_state(V2Storage.load_state(state.run_id))

    assert migrated.run_id == state.run_id
    assert migrated.case_title == "Samsung HBM4 Capacity Strategy"
    assert migrated.research_job is None
    assert migrated.workflow_stage == "internal_evidence_refinement"
    assert migrated.hypotheses
    assert 0 < len(migrated.internal_questions) <= MAX_INTERNAL_QUESTIONS
    assert responses.created == []


def test_saved_core_run_repairs_legacy_stakeholder_paths_in_place(tmp_path, monkeypatch):
    service, _responses = _service(tmp_path, monkeypatch)
    state = _initialize(
        service,
        project_name="Starbucks Priority Pass demo",
        decision_question=(
            "Evaluate Starbucks Priority Pass for non-members, baristas, and store managers. "
            "Determine whether momentum builds toward national rollout, limited pilot, "
            "redesign, or cancellation."
        ),
    )
    legacy_labels = ["Non-members", "Baristas", "Store managers"]
    for hypothesis, label in zip(state.hypotheses, legacy_labels):
        hypothesis.label = label
        hypothesis.decision_role = "alternative"
    state.decision_completion = {}
    V2Storage.save_state(state)

    migrated = service.migrate_core_state(V2Storage.load_state(state.run_id))

    assert all(is_executable_action_label(item.label) for item in migrated.hypotheses)
    assert not any(item.label in legacy_labels for item in migrated.hypotheses)
    assert {
        item.decision_role for item in migrated.hypotheses
    } == {"immediate", "staged", "redesign", "defer"}
    assert any(
        event.event_type == "invalid_actions_reconstructed"
        for event in migrated.audit_trail
    )


def test_user_can_propose_a_material_question_without_expanding_the_budget(tmp_path, monkeypatch):
    service, _responses = _service(tmp_path, monkeypatch)
    state = _initialize(service)
    state = MiroFishV2Pipeline().fork_public_run(state.run_id)
    original_count = len(state.internal_questions)
    original_revision = state.graph_revision
    custom_text = "Which customer qualification deadline would force management to accelerate HBM4 capacity?"

    updated = MiroFishV2Pipeline().propose_internal_question(
        state.run_id,
        custom_text,
        "timing",
        owner_hint="HBM program office",
    )

    proposed = next(question for question in updated.internal_questions if question.origin == "user_proposed")
    assert proposed.question == custom_text
    assert proposed.owner_hint == "HBM program office"
    assert proposed.question_priority_score >= MATERIALITY_THRESHOLD
    assert len(updated.internal_questions) <= MAX_INTERNAL_QUESTIONS
    assert len(updated.internal_questions) == original_count
    assert updated.graph_revision == original_revision + 1
    assert any(node["id"] == proposed.question_id for node in updated.graph["nodes"])


def test_provider_enum_style_status_is_still_normalized_for_legacy_runs(tmp_path, monkeypatch):
    service, _responses = _service(tmp_path, monkeypatch)

    assert service._provider_status(SimpleNamespace(value="in_progress")) == "in_progress"
    assert service._provider_status("ResponseStatus.COMPLETED") == "completed"
