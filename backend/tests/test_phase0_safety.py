from types import SimpleNamespace

import pytest

from app import create_app
from app.api import graph as graph_api
from app.config import Config
from app.models.project import ProjectManager
from app.services.report_agent import ReportManager
from app.services.simulation_manager import SimulationManager
from app.utils.private_data import (
    PrivateDataPolicyError,
    assert_private_data_allowed,
    contains_private_data,
    safe_debug_payload,
)
from app.utils.safe_path import UnsafePathError, safe_child_path, validate_identifier
from app.v2.refinement import CoreRefinementService
from app.v2.storage import V2Storage


@pytest.mark.parametrize(
    "identifier",
    [
        "/tmp/escape",
        "../escape",
        "nested/escape",
        r"nested\escape",
        "%2e%2e",
        "%252e%252e",
        "nested%2fescape",
        "bad id",
        "",
    ],
)
def test_shared_identifier_validation_rejects_traversal_and_invalid_ids(identifier):
    with pytest.raises(UnsafePathError, match="Invalid test ID"):
        validate_identifier(identifier, label="test ID")


def test_safe_child_path_rejects_symlink_escape(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "valid_id").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    with pytest.raises(UnsafePathError):
        safe_child_path(root, "valid_id")


def test_storage_managers_share_safe_identifier_policy(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path / "simulations"))
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "runs")

    with pytest.raises(UnsafePathError):
        ProjectManager._get_project_dir("../escape")
    with pytest.raises(UnsafePathError):
        SimulationManager()._get_simulation_dir("%2e%2e")
    with pytest.raises(UnsafePathError):
        ReportManager._get_report_folder("nested/escape")
    with pytest.raises(FileNotFoundError, match="v2 run not found") as error:
        V2Storage.run_dir("../escape")
    assert str(tmp_path) not in str(error.value)


def test_graph_task_listing_accepts_already_serialized_results(monkeypatch):
    task = SimpleNamespace(to_dict=lambda: {"task_id": "object"})
    monkeypatch.setattr(
        graph_api.TaskManager,
        "list_tasks",
        lambda _self: [{"task_id": "dictionary"}, task],
    )
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get("/api/graph/tasks")

    assert response.status_code == 200
    assert response.get_json()["data"] == [
        {"task_id": "dictionary"},
        {"task_id": "object"},
    ]


@pytest.mark.parametrize("suffix", ["start", "sync", "cancel"])
def test_legacy_deep_research_endpoints_are_gone_by_default(suffix):
    app = create_app()
    app.config.update(TESTING=True, ENABLE_LEGACY_DEEP_RESEARCH=False)

    response = app.test_client().post(
        f"/api/v2/core/reports/report_example/research/{suffix}", json={}
    )

    assert response.status_code == 410
    assert "disabled" in response.get_json()["error"].lower()


def test_health_does_not_advertise_deep_research_as_a_normal_stage():
    app = create_app()
    app.config.update(TESTING=True)

    workflow = app.test_client().get("/health").get_json()["workflows"][
        "continuous_decision_workflow"
    ]

    assert "deep_research" not in workflow["stages"]
    assert "research_mode" not in workflow


def test_private_data_guard_blocks_external_and_log_sinks_but_allows_public_data():
    private = {
        "internal_evidence": [
            {
                "evidence_id": "evidence_1",
                "answer": "Board-only budget",
                "confidential": True,
                "outbound_external_use": False,
            }
        ]
    }
    public = {"claims": [{"text": "A public filing was published."}]}

    assert contains_private_data(private) is True
    assert contains_private_data(public) is False
    assert safe_debug_payload(private) == "[REDACTED_PRIVATE_PAYLOAD]"
    assert_private_data_allowed(public, sink="web_search")
    for sink in ("web_search", "external_research", "report_agent_log", "outbound_tool_call"):
        with pytest.raises(PrivateDataPolicyError):
            assert_private_data_allowed(private, sink=sink)


def test_private_context_is_rejected_before_a_research_prompt_is_built():
    state = SimpleNamespace(
        public_research_context={
            "internal_evidence": [{"answer": "secret", "confidential": True}]
        },
        question="Should we proceed?",
    )

    with pytest.raises(PrivateDataPolicyError):
        CoreRefinementService()._research_prompt(state)


def test_default_configuration_disables_legacy_deep_research():
    assert Config.ENABLE_LEGACY_DEEP_RESEARCH is False


def test_unsafe_route_id_returns_safe_client_error():
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get("/api/report/%252e%252e")

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Invalid storage identifier.",
    }
