import json
import os
import stat

import pytest

from app.v2.schemas import AuditEvent, V2RunState
from app.v2.storage import V2Storage


@pytest.fixture
def persisted_state(tmp_path, monkeypatch):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "v2_transaction_runs")
    state = V2RunState(
        run_id="v2_20260716010101_abcdef12",
        project_name="Storage transaction test",
        question="Should the decision proceed?",
        graph={"revision": 0, "nodes": [], "edges": []},
        audit_trail=[
            AuditEvent(
                event_id="audit_0001",
                event_type="import_completed",
                summary="Canonical import",
            )
        ],
    )
    V2Storage.save_state(state)
    return V2Storage.load_state(state.run_id)


def _mutate_for_next_revision(state):
    state.graph = {"revision": 1, "nodes": [{"id": "new-node"}], "edges": []}
    state.audit_trail.append(
        AuditEvent(
            event_id="audit_0002",
            event_type="internal_answer_received",
            summary="Uncommitted answer",
        )
    )
    return state


def _assert_recovered_canonical(state, baseline_state_bytes, baseline_audit_bytes):
    run_dir = V2Storage.run_dir(state.run_id)
    recovered = V2Storage.load_state(state.run_id)

    assert recovered.state_revision == 1
    assert [event.event_id for event in recovered.audit_trail] == ["audit_0001"]
    assert (run_dir / "state.json").read_bytes() == baseline_state_bytes
    assert (run_dir / "audit_trail.jsonl").read_bytes() == baseline_audit_bytes
    assert json.loads((run_dir / "graph.json").read_text(encoding="utf-8"))["revision"] == 0
    assert not (run_dir / V2Storage.PENDING_REVISION_FILENAME).exists()
    assert not (run_dir / "graph_revisions" / "revision_002.json").exists()


def test_artifact_failure_keeps_old_state_as_commit_and_recovers_derivatives(
    persisted_state,
    monkeypatch,
):
    run_dir = V2Storage.run_dir(persisted_state.run_id)
    baseline_state_bytes = (run_dir / "state.json").read_bytes()
    baseline_audit_bytes = (run_dir / "audit_trail.jsonl").read_bytes()
    state = _mutate_for_next_revision(persisted_state)

    with monkeypatch.context() as failure_patch:
        def fail_first_artifact(_cls, _run_id, _filename, _payload):
            raise OSError("injected artifact failure")

        failure_patch.setattr(V2Storage, "_write_artifact", classmethod(fail_first_artifact))
        with pytest.raises(OSError, match="injected artifact failure"):
            V2Storage.save_state(state)

    assert state.state_revision == 1
    assert (run_dir / "state.json").read_bytes() == baseline_state_bytes
    marker = run_dir / V2Storage.PENDING_REVISION_FILENAME
    assert marker.exists()
    if os.name != "nt":
        assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    _assert_recovered_canonical(state, baseline_state_bytes, baseline_audit_bytes)


def test_jsonl_failure_rolls_back_prepared_artifacts_on_next_load(
    persisted_state,
    monkeypatch,
):
    run_dir = V2Storage.run_dir(persisted_state.run_id)
    baseline_state_bytes = (run_dir / "state.json").read_bytes()
    baseline_audit_bytes = (run_dir / "audit_trail.jsonl").read_bytes()
    state = _mutate_for_next_revision(persisted_state)
    original_append_jsonl = V2Storage._append_jsonl

    with monkeypatch.context() as failure_patch:
        def fail_jsonl(_cls, run_id, filename, rows):
            # Simulate an I/O error after bytes reached the append-only log but
            # before the transaction could publish state.json.
            original_append_jsonl(run_id, filename, rows)
            raise OSError("injected JSONL failure")

        failure_patch.setattr(V2Storage, "_append_jsonl", classmethod(fail_jsonl))
        with pytest.raises(OSError, match="injected JSONL failure"):
            V2Storage.save_state(state)

    assert json.loads((run_dir / "graph.json").read_text(encoding="utf-8"))["revision"] == 1
    assert (run_dir / "state.json").read_bytes() == baseline_state_bytes
    assert len((run_dir / "audit_trail.jsonl").read_bytes()) > len(baseline_audit_bytes)
    _assert_recovered_canonical(state, baseline_state_bytes, baseline_audit_bytes)


def test_state_commit_failure_truncates_jsonl_removes_snapshot_and_allows_clean_retry(
    persisted_state,
    monkeypatch,
):
    run_dir = V2Storage.run_dir(persisted_state.run_id)
    baseline_state_bytes = (run_dir / "state.json").read_bytes()
    baseline_audit_bytes = (run_dir / "audit_trail.jsonl").read_bytes()
    state = _mutate_for_next_revision(persisted_state)
    original_atomic_write_json = V2Storage._atomic_write_json

    with monkeypatch.context() as failure_patch:
        def fail_state_commit(_cls, path, payload):
            if path.name == "state.json":
                raise OSError("injected state commit failure")
            return original_atomic_write_json(path, payload)

        failure_patch.setattr(V2Storage, "_atomic_write_json", classmethod(fail_state_commit))
        with pytest.raises(OSError, match="injected state commit failure"):
            V2Storage.save_state(state)

    assert state.state_revision == 1
    assert (run_dir / "state.json").read_bytes() == baseline_state_bytes
    assert (run_dir / "audit_trail.jsonl").read_bytes().startswith(baseline_audit_bytes)
    assert len((run_dir / "audit_trail.jsonl").read_bytes()) > len(baseline_audit_bytes)
    poisoned_snapshot = run_dir / "graph_revisions" / "revision_002.json"
    assert poisoned_snapshot.exists()

    _assert_recovered_canonical(state, baseline_state_bytes, baseline_audit_bytes)

    # Retry the same mutation after recovery.  The restored in-memory revision
    # reuses revision 2 and replaces any failed-attempt snapshot deterministically.
    V2Storage.save_state(state)
    retried = V2Storage.load_state(state.run_id)
    assert retried.state_revision == 2
    assert [event.event_id for event in retried.audit_trail] == ["audit_0001", "audit_0002"]
    assert json.loads(poisoned_snapshot.read_text(encoding="utf-8"))["nodes"] == [
        {"id": "new-node"}
    ]
    assert (run_dir / "audit_trail.jsonl").read_bytes().startswith(baseline_audit_bytes)
    if os.name != "nt":
        assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
        for path in run_dir.rglob("*"):
            if path.is_file():
                assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_uncommitted_calculation_trace_is_removed_when_state_commit_fails(
    persisted_state,
    monkeypatch,
):
    state = _mutate_for_next_revision(persisted_state)
    trace_id = "trace_transaction_abcdef12"
    state.decision_analysis_trace_id = trace_id
    state.decision_analysis_result = {
        "status": "calculated",
        "trace_id": trace_id,
        "recommended_action": "safe",
    }
    state.decision_analysis_trace = {
        "trace_id": trace_id,
        "run_id": state.run_id,
        "trace": {"method": "exact_enumeration", "rows": []},
    }
    original_atomic_write_json = V2Storage._atomic_write_json

    with monkeypatch.context() as failure_patch:
        def fail_state_commit(_cls, path, payload):
            if path.name == "state.json":
                raise OSError("injected trace commit failure")
            return original_atomic_write_json(path, payload)

        failure_patch.setattr(V2Storage, "_atomic_write_json", classmethod(fail_state_commit))
        with pytest.raises(OSError, match="injected trace commit failure"):
            V2Storage.save_state(state)

    assert not V2Storage.calculation_trace_path(state.run_id, trace_id).exists()
    recovered = V2Storage.load_state(state.run_id)
    assert recovered.decision_analysis_trace_id is None
    assert recovered.decision_analysis_result is None
