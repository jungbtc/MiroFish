from types import SimpleNamespace

from app.v2.refinement import CoreRefinementService
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.storage import V2Storage


class FakeResponses:
    def __init__(self):
        self.created = []
        self.retrieved = []
        self.cancelled = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id="resp_public_research", status="queued")

    def retrieve(self, response_id):
        self.retrieved.append(response_id)
        return SimpleNamespace(
            id=response_id,
            status="completed",
            output=[
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Public demand increased according to the cited primary source.",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://example.com/primary",
                                    "title": "Primary source",
                                    "start_index": 0,
                                    "end_index": 13,
                                }
                            ],
                        }
                    ],
                }
            ],
        )

    def cancel(self, response_id):
        self.cancelled.append(response_id)
        return SimpleNamespace(id=response_id, status="cancelled")


def _service(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "core_refinement_runs")
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)
    return CoreRefinementService(client=client), responses


def test_core_report_starts_one_durable_public_research_job(tmp_path, monkeypatch):
    service, responses = _service(tmp_path, monkeypatch)
    state = service.initialize_from_core_report(
        project_id="project_1",
        graph_id="graph_1",
        simulation_id="sim_1",
        report_id="report_1",
        project_name="Acquisition Decision",
        decision_question="Should we acquire the target?",
        report_markdown="# Initial report\nSimulation suggests a staged path.",
        graph_evidence={"public_summary": "market structure"},
        simulation_metadata={"rounds": 10},
    )

    started = service.start_research(state.run_id)
    repeated = service.start_research(state.run_id)

    assert started.research_job.provider_response_id == "resp_public_research"
    assert repeated.research_job.provider_response_id == "resp_public_research"
    assert len(responses.created) == 1
    request = responses.created[0]
    assert request["background"] is True
    assert request["tools"] == [{"type": "web_search_preview"}]
    assert "Should we acquire" in request["input"]


def test_completed_research_preserves_citations_and_opens_private_refinement(tmp_path, monkeypatch):
    service, responses = _service(tmp_path, monkeypatch)
    state = service.initialize_from_core_report(
        project_id="project_2",
        graph_id="graph_2",
        simulation_id="sim_2",
        report_id="report_2",
        project_name="Launch Decision",
        decision_question="Should we launch now or stage the rollout?",
        report_markdown="# Initial report\nAgents identified execution risk.",
    )
    service.start_research(state.run_id)

    completed = service.sync_research(state.run_id)
    repeated = service.sync_research(state.run_id)

    assert completed.research_job.status == "completed"
    assert completed.research_job.citation_count == 1
    assert completed.workflow_stage == "internal_evidence_refinement"
    assert completed.internal_questions
    assert completed.hypotheses
    external_documents = [
        document for document in completed.documents
        if document.metadata.get("source_type") == "external_research"
    ]
    assert len(external_documents) == 1
    assert external_documents[0].imported_citations[0].url == "https://example.com/primary"
    assert repeated.research_job.research_document_id == completed.research_job.research_document_id
    assert len(responses.retrieved) == 1


def test_provider_enum_style_status_is_normalized(tmp_path, monkeypatch):
    service, _responses = _service(tmp_path, monkeypatch)

    assert service._provider_status(SimpleNamespace(value="in_progress")) == "in_progress"
    assert service._provider_status("ResponseStatus.COMPLETED") == "completed"


def test_private_answer_triggers_bounded_reevaluation_without_new_research_call(tmp_path, monkeypatch):
    service, responses = _service(tmp_path, monkeypatch)
    state = service.initialize_from_core_report(
        project_id="project_3",
        graph_id="graph_3",
        simulation_id="sim_3",
        report_id="report_3",
        project_name="Capacity Decision",
        decision_question="Should we proceed immediately or stage the commitment?",
        report_markdown="# Initial report\nThe immediate and staged paths remain open.",
    )
    service.start_research(state.run_id)
    completed = service.sync_research(state.run_id)
    requested = next(question for question in completed.internal_questions if question.status == "requested")
    answers = {
        "strategic_success": "The verified minimum outcome is 20% growth and the staged path meets it.",
        "constraints": "The immediate path is blocked by contract and cannot proceed.",
        "financial_capacity": "Only the staged pilot budget is approved; immediate commitment has no approved budget.",
        "execution_capacity": "The staged pilot has a confirmed owner and sufficient capacity.",
        "risk_tolerance": "The organization accepts only the reversible staged downside.",
        "timing": "The verified deadline allows a staged pilot before commitment.",
    }

    updated = MiroFishV2Pipeline().submit_internal_answer(
        completed.run_id,
        requested.question_id,
        answers[requested.category],
        confidence=1.0,
        confidential=True,
    )

    assert updated.targeted_reevaluations
    reevaluation = updated.targeted_reevaluations[-1]
    assert reevaluation.evidence_id == updated.internal_evidence[-1].evidence_id
    assert reevaluation.mode == "bounded_branch_reevaluation"
    assert updated.internal_evidence[-1].outbound_external_use is False
    assert len(responses.created) == 1
    assert "## Targeted Re-evaluation Record" in updated.report.markdown
