import io
import json
import os
import stat

import pytest
from werkzeug.datastructures import FileStorage

from app import create_app
from app.v2.pipeline import MiroFishV2Pipeline
from app.v2.storage import V2Storage


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_upload_runs")
    return MiroFishV2Pipeline()


def _upload(filename: str, body: bytes) -> FileStorage:
    return FileStorage(stream=io.BytesIO(body), filename=filename)


@pytest.mark.parametrize(
    "uploads",
    [
        [_upload("unsupported.exe", b"payload")],
        [_upload("empty.md", b"")],
        [
            _upload("valid.md", b"A documented benefit was reported."),
            _upload("unsupported.exe", b"payload"),
        ],
    ],
    ids=["unsupported", "empty", "mixed-invalid"],
)
def test_failed_upload_import_leaves_no_provisional_run_payload(pipeline, uploads):
    with pytest.raises(ValueError):
        pipeline.run_from_uploads(uploads, question="Should we proceed?")

    assert not V2Storage.RUNS_DIR.exists() or list(V2Storage.RUNS_DIR.iterdir()) == []


def test_discard_guard_preserves_initialized_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_upload_runs")
    run_id = V2Storage.create_run_id()
    run_dir = V2Storage.run_dir(run_id)
    run_dir.mkdir(parents=True)
    V2Storage.state_path(run_id).write_text("{}", encoding="utf-8")

    assert V2Storage.discard_uninitialized_run(run_id) is False
    assert run_dir.exists()


def test_non_loopback_v2_access_requires_configured_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_remote_runs")
    app = create_app()
    app.config.update(TESTING=True, V2_API_KEY="test-v2-secret")
    client = app.test_client()
    request_kwargs = {
        "json": {},
        "environ_base": {"REMOTE_ADDR": "192.0.2.25"},
    }

    missing = client.post("/api/v2/run", **request_kwargs)
    wrong = client.post(
        "/api/v2/run",
        headers={"Authorization": "Bearer wrong"},
        **request_kwargs,
    )
    accepted = client.post(
        "/api/v2/run",
        headers={"Authorization": "Bearer test-v2-secret"},
        **request_kwargs,
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert accepted.status_code == 400  # authenticated; rejected only by body validation


def test_non_loopback_v2_access_is_closed_when_no_key_is_configured():
    app = create_app()
    app.config.update(TESTING=True, V2_API_KEY="")
    response = app.test_client().post(
        "/api/v2/demo",
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
    )

    assert response.status_code == 403


def test_decision_imports_are_rate_limited_per_client():
    app = create_app()
    app.config.update(
        TESTING=True,
        V2_RUN_RATE_LIMIT=2,
        V2_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    client = app.test_client()

    first = client.post("/api/v2/run", json={})
    second = client.post("/api/v2/run", json={})
    limited = client.post("/api/v2/run", json={})

    assert first.status_code == second.status_code == 400
    assert limited.status_code == 429


def test_v2_cors_allows_loopback_origin_but_not_arbitrary_web_origins():
    app = create_app()
    client = app.test_client()
    preflight_headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }

    local = client.options(
        "/api/v2/run",
        headers={"Origin": "http://localhost:3000", **preflight_headers},
    )
    external = client.options(
        "/api/v2/run",
        headers={"Origin": "https://attacker.example", **preflight_headers},
    )

    assert local.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert "Access-Control-Allow-Origin" not in external.headers


def test_configured_key_is_required_even_for_loopback_proxy_requests():
    app = create_app()
    app.config.update(TESTING=True, V2_API_KEY="proxy-secret")
    client = app.test_client()

    missing = client.post("/api/v2/run", json={})
    accepted = client.post(
        "/api/v2/run",
        json={},
        headers={"X-MiroFish-Key": "proxy-secret"},
    )

    assert missing.status_code == 401
    assert accepted.status_code == 400


def test_configured_key_allows_trusted_browser_preflight_without_credentials():
    app = create_app()
    app.config.update(TESTING=True, V2_API_KEY="proxy-secret")

    response = app.test_client().options(
        "/api/v2/run",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-MiroFish-Key",
        },
    )

    assert response.status_code < 400
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert "x-mirofish-key" in response.headers.get("Access-Control-Allow-Headers", "").lower()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are not portable to Windows")
def test_v2_case_files_are_owner_only_and_existing_modes_are_repaired(pipeline):
    state = pipeline.run_from_uploads(
        [_upload("private-report.md", b"The documented option improved reliability by 20%. ")],
        question="Should we proceed now or defer?",
    )
    run_dir = V2Storage.run_dir(state.run_id)

    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)
        for path in run_dir.rglob("*")
        if not path.is_symlink()
    )

    state_path = V2Storage.state_path(state.run_id)
    state_path.chmod(0o644)
    run_dir.chmod(0o755)
    V2Storage.load_state(state.run_id)

    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600


def test_api_never_exposes_import_filesystem_paths(pipeline):
    state = pipeline.run_from_uploads(
        [_upload("report.md", b"The benchmark documented a 15% reliability improvement.")],
        question="Should we proceed now or defer?",
    )
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get(f"/api/v2/runs/{state.run_id}")
    metadata = response.get_json()["data"]["documents"][0]["metadata"]

    assert response.status_code == 200
    assert "path" not in metadata
    assert all(not key.lower().endswith("_path") for key in metadata)


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "Should we proceed?", "project_name": [], "documents": [{}]},
        {"question": "Should we proceed?", "rounds": 1.5, "documents": [{}]},
        {"question": "Should we proceed?", "rounds": 0, "documents": [{}]},
        {"question": [], "documents": [{}]},
    ],
)
def test_v2_run_api_rejects_falsey_or_non_integral_field_shapes(payload):
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post("/api/v2/run", json=payload)

    assert response.status_code == 400


@pytest.mark.parametrize(
    "field,value",
    [
        ("submitted_by", ["finance"]),
        ("interpretation", ["favorable"]),
        ("confidential", "false"),
        ("confidence", True),
    ],
)
def test_internal_answer_api_rejects_ambiguous_json_types(field, value):
    app = create_app()
    app.config.update(TESTING=True)
    payload = {
        "question_id": "question_example",
        "answer": "The approved budget is $2 million.",
        field: value,
    }

    response = app.test_client().post(
        "/api/v2/runs/v2_20260101000000_deadbeef/answers",
        json=payload,
    )

    assert response.status_code == 400


def test_demo_rejects_non_integral_rounds_as_a_client_error():
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post("/api/v2/demo?rounds=1.5")

    assert response.status_code == 400


def test_demo_is_post_only_rate_limited_and_does_not_create_runs_on_get(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_demo_rate_runs")
    app = create_app()
    app.config.update(TESTING=True, V2_RUN_RATE_LIMIT=1)
    client = app.test_client()

    read_like = client.get("/api/v2/demo")
    first = client.post("/api/v2/demo")
    limited = client.post("/api/v2/demo")

    assert read_like.status_code == 405
    assert first.status_code == 200
    assert limited.status_code == 429
    assert len(list(V2Storage.RUNS_DIR.glob("v2_*"))) == 1


def test_untrusted_browser_origin_is_rejected_before_state_change():
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post(
        "/api/v2/demo",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Origin is not trusted for v2 access."


def test_configured_browser_origins_are_exact_not_regex_patterns(monkeypatch):
    monkeypatch.setenv("V2_CORS_ORIGINS", "https://decision.example.com")
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    exact = client.options(
        "/api/v2/run",
        headers={
            "Origin": "https://decision.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    lookalike = client.post(
        "/api/v2/demo",
        headers={"Origin": "https://decisionXexampleYcom"},
    )

    assert exact.headers.get("Access-Control-Allow-Origin") == "https://decision.example.com"
    assert lookalike.status_code == 403


def test_v2_responses_disable_browser_and_proxy_caching():
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post("/api/v2/run", json={})

    assert response.headers["Cache-Control"] == "no-store, private, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"


def test_malformed_pdf_is_a_sanitized_client_error_and_is_cleaned_up(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_bad_pdf_runs")
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post(
        "/api/v2/research-pack",
        data={
            "files": (io.BytesIO(b"not a real PDF"), "secret-report.pdf"),
            "question": "Should we proceed?",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid or unreadable PDF: secret-report.pdf"
    assert str(tmp_path) not in response.get_data(as_text=True)
    assert not V2Storage.RUNS_DIR.exists() or list(V2Storage.RUNS_DIR.iterdir()) == []


def test_unexpected_import_errors_do_not_expose_internal_exception_text(monkeypatch):
    def fail_import(*_args, **_kwargs):
        raise RuntimeError("sensitive failure at /srv/private/case.json")

    monkeypatch.setattr(MiroFishV2Pipeline, "run_from_inline_documents", fail_import)
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post(
        "/api/v2/run",
        json={
            "question": "Should we proceed?",
            "documents": [{"text": "Documented evidence."}],
        },
    )

    assert response.status_code == 500
    assert response.get_json()["error"] == "Decision import failed unexpectedly."
    assert "/srv/private" not in response.get_data(as_text=True)


def test_state_validation_errors_cannot_echo_confidential_state_values(pipeline):
    state = pipeline.run_from_uploads(
        [_upload("report.md", b"The documented option improved reliability.")],
        question="Should we proceed now or defer?",
    )
    state_path = V2Storage.state_path(state.run_id)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["project_name"] = {"private": "TOP_SECRET_BOARD_VALUE"}
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().post(
        f"/api/v2/runs/{state.run_id}/answers",
        json={
            "question_id": "question_example",
            "answer": "The approved budget is $2 million.",
        },
    )

    assert response.status_code == 500
    assert response.get_json()["error"] == "Decision state is invalid and could not be updated."
    assert "TOP_SECRET_BOARD_VALUE" not in response.get_data(as_text=True)


@pytest.mark.parametrize("endpoint", ["answers", "stop/evaluate"])
def test_mutating_nonexistent_run_does_not_create_lock_artifacts(
    tmp_path,
    monkeypatch,
    endpoint,
):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_missing_run")
    app = create_app()
    app.config.update(TESTING=True)
    run_id = "v2_20260101000000_deadbeef"
    lock_keys_before = set(V2Storage._PROCESS_LOCKS)
    payload = (
        {"question_id": "question_missing", "answer": "The approved budget is $2 million."}
        if endpoint == "answers"
        else None
    )

    response = app.test_client().post(
        f"/api/v2/runs/{run_id}/{endpoint}",
        json=payload,
    )

    assert response.status_code == 404
    assert not (V2Storage.RUNS_DIR / run_id).exists()
    assert set(V2Storage._PROCESS_LOCKS) == lock_keys_before
