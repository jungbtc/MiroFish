import asyncio

import pytest

import run as backend_entrypoint
from app import create_app
from app.services.run_mode import normalize_run_mode, resolve_run_mode
from scripts.simulation_runtime import (
    ContextGuardState,
    apply_active_agent_caps,
    apply_runtime_overrides,
    clamp_active_agent_target,
    estimate_message_tokens,
    guarded_env_step,
)


def test_preview_mode_preserves_imported_token_and_activity_caps():
    resolved = resolve_run_mode("preview", platform=None, max_rounds=120)

    assert resolved == {
        "run_mode": "preview",
        "run_mode_label": "Preview",
        "run_mode_description": "Fast first pass with one platform and tight activity caps.",
        "platform": "twitter",
        "max_rounds": 40,
        "agents_per_hour_min_cap": 2,
        "agents_per_hour_max_cap": 8,
        "hard_max_active_agents": 10,
        "context_token_limit": 180_000,
        "context_error_limit": 3,
    }


def test_balanced_and_full_modes_keep_expected_cost_boundaries():
    balanced = resolve_run_mode("balanced", platform="reddit", max_rounds=None)
    full = resolve_run_mode("full", platform=None, max_rounds=140)

    assert balanced["platform"] == "reddit"
    assert balanced["max_rounds"] == 80
    assert balanced["hard_max_active_agents"] == 18
    assert full["platform"] == "parallel"
    assert full["max_rounds"] == 140
    assert full["hard_max_active_agents"] is None
    assert normalize_run_mode("economy") == "preview"


def test_runtime_caps_are_applied_without_mutating_generated_config():
    original = {"simulation": {"topic": "demo"}}
    adjusted = apply_runtime_overrides(
        original,
        run_mode="preview",
        agents_per_hour_min_cap=2,
        agents_per_hour_max_cap=8,
        hard_max_active_agents=10,
    )

    assert "runtime_efficiency" not in original
    assert apply_active_agent_caps(adjusted, 6, 24) == (2, 8)
    assert clamp_active_agent_target(adjusted, 50) == 10


def test_context_guard_estimate_and_stop_counter_remain_deterministic():
    messages = [{"role": "user", "content": "x" * 300}]
    assert estimate_message_tokens(messages) >= 100

    state = ContextGuardState(token_limit=100, error_limit=2)
    state.record_prevented(140)
    assert state.should_stop() is False
    state.record_api_error("request resulted in 250 tokens")
    assert state.should_stop() is True
    assert state.max_estimated_tokens == 250


def test_guarded_step_skips_context_errors_instead_of_retrying_token_heavy_call():
    class OversizedEnvironment:
        async def step(self, _actions):
            raise RuntimeError("MIROFISH_CONTEXT_GUARD: estimated input exceeds safety limit")

    logs = []
    completed = asyncio.run(
        guarded_env_step(OversizedEnvironment(), {}, logs.append, "verification step")
    )

    assert completed is False
    assert len(logs) == 1
    assert "Context guard skipped verification step" in logs[0]


def test_invalid_run_mode_is_rejected_before_runtime_launch():
    with pytest.raises(ValueError, match="Unsupported run_mode"):
        resolve_run_mode("unbounded", platform=None, max_rounds=None)


def test_optional_v2_backend_can_start_without_core_llm_or_graph_credentials(monkeypatch, capsys):
    launched = {}

    class FakeApp:
        def run(self, **kwargs):
            launched.update(kwargs)

    monkeypatch.setattr(
        backend_entrypoint.Config,
        "validate",
        classmethod(lambda _cls: ["OPENAI_API_KEY or LLM_API_KEY is required."]),
    )
    monkeypatch.setattr(backend_entrypoint.Config, "STRICT_STARTUP_VALIDATION", False)
    monkeypatch.setattr(backend_entrypoint, "create_app", lambda: FakeApp())
    monkeypatch.delenv("FLASK_HOST", raising=False)
    monkeypatch.delenv("FLASK_PORT", raising=False)

    backend_entrypoint.main()

    assert launched["host"] == "127.0.0.1"
    assert launched["port"] == 5001
    assert "MiroFish v2 will still start in local deterministic mode" in capsys.readouterr().out


def test_health_distinguishes_core_configuration_from_optional_addon(monkeypatch):
    monkeypatch.setattr(
        backend_entrypoint.Config,
        "validate",
        classmethod(lambda _cls: ["OPENAI_API_KEY or LLM_API_KEY is required."]),
    )
    app = create_app()
    app.config.update(TESTING=True)

    payload = app.test_client().get("/health").get_json()

    assert payload["status"] == "ok"
    assert payload["workflows"]["ontology_simulation"] == {
        "status": "configuration_required",
        "configuration_errors": ["OPENAI_API_KEY or LLM_API_KEY is required."],
    }
    assert payload["workflows"]["deep_research_decision_addon"] == {
        "status": "ready",
        "processing_mode": "local_deterministic",
    }


def test_core_and_optional_workflow_routes_are_registered_together():
    app = create_app()
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert {
        "/api/graph/ontology/generate",
        "/api/graph/build",
        "/api/simulation/create",
        "/api/simulation/prepare",
        "/api/simulation/start",
        "/api/report/generate",
        "/api/report/chat",
        "/api/v2/research-pack",
        "/api/v2/runs/<run_id>/answers",
    } <= routes


def test_graph_build_resolves_requested_llm_settings_before_status_validation(monkeypatch):
    from types import SimpleNamespace

    from app.api import graph as graph_api

    project = SimpleNamespace(
        llm_model="gpt-5.4-nano",
        llm_reasoning_effort="minimal",
        status=graph_api.ProjectStatus.CREATED,
    )
    monkeypatch.setattr(
        graph_api.Config,
        "validate_graph_settings",
        classmethod(lambda _cls: []),
    )
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _project_id: project)

    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post(
        "/api/graph/build",
        json={
            "project_id": "proj_settings_regression",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "low",
        },
    )

    assert response.status_code == 400
    assert "NameError" not in (response.get_json().get("error") or "")
    assert project.llm_model == "gpt-5.4-mini"
    assert project.llm_reasoning_effort == "low"


def test_twitter_profiles_are_loaded_from_generated_csv(tmp_path, monkeypatch):
    from app.services.simulation_manager import SimulationManager

    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path))
    manager = SimulationManager()
    monkeypatch.setattr(manager, "_load_simulation_state", lambda _simulation_id: object())
    simulation_dir = tmp_path / "sim_twitter_profiles"
    simulation_dir.mkdir()
    (simulation_dir / "twitter_profiles.csv").write_text(
        "user_id,username,name,description,user_char\n"
        "0,market_watch,Market Watch,Tracks DIS sentiment,Analyst persona\n",
        encoding="utf-8",
    )

    profiles = manager.get_profiles("sim_twitter_profiles", platform="twitter")

    assert profiles == [
        {
            "user_id": "0",
            "username": "market_watch",
            "name": "Market Watch",
            "description": "Tracks DIS sentiment",
            "user_char": "Analyst persona",
        }
    ]
