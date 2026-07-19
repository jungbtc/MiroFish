import json
import os
import stat

import pytest

from app.config import Config
from app.v2.schemas import InternalEvidence, V2RunState
from app.v2.storage import ConfidentialStorageUnavailable, V2Storage


def _private_state(run_id: str, answer: str) -> V2RunState:
    return V2RunState(
        run_id=run_id,
        run_type="internal",
        parent_run_id="v2_20260718010101_aaaa1111",
        root_public_run_id="v2_20260718010101_aaaa1111",
        project_name="Confidential storage fixture",
        question="Should the organization proceed?",
        internal_evidence=[
            InternalEvidence(
                evidence_id="evidence_board_budget",
                question_id="question_budget",
                answer=answer,
                interpretation="favorable",
                confidential=True,
                visibility="restricted",
                classification="board_confidential",
                outbound_external_use=False,
            )
        ],
    )


def test_confidential_answer_is_stored_once_outside_canonical_and_derived_state(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(Config, "CONFIDENTIAL_STORAGE_MODE", "local_development")
    secret = "BOARD-ONLY-CAPACITY-2026"
    state = _private_state("v2_20260718010102_bbbb2222", secret)

    V2Storage.save_state(state)
    run_dir = V2Storage.run_dir(state.run_id)
    state_text = (run_dir / "state.json").read_text(encoding="utf-8")
    derivative_text = (run_dir / "internal_evidence.json").read_text(encoding="utf-8")
    confidential_files = list((run_dir / "confidential" / "internal_evidence").glob("*.json"))

    assert secret not in state_text
    assert secret not in derivative_text
    assert V2Storage.CONFIDENTIAL_ANSWER_MARKER in state_text
    assert len(confidential_files) == 1
    assert json.loads(confidential_files[0].read_text(encoding="utf-8"))["answer"] == secret
    assert V2Storage.load_state(state.run_id).internal_evidence[0].answer == secret

    # Re-saving a hydrated state keeps one immutable raw artifact instead of
    # duplicating it across revisions or derivatives.
    V2Storage.save_state(V2Storage.load_state(state.run_id))
    assert len(list((run_dir / "confidential" / "internal_evidence").glob("*.json"))) == 1
    if os.name != "nt":
        assert stat.S_IMODE((run_dir / "confidential").stat().st_mode) == 0o700
        assert stat.S_IMODE(confidential_files[0].stat().st_mode) == 0o600


def test_confidential_write_fails_closed_when_local_development_mode_is_disabled(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(V2Storage, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(Config, "CONFIDENTIAL_STORAGE_MODE", "disabled")
    state = _private_state("v2_20260718010103_cccc3333", "DO-NOT-PERSIST")

    with pytest.raises(ConfidentialStorageUnavailable):
        V2Storage.save_state(state)

    run_dir = V2Storage.run_dir(state.run_id)
    assert state.state_revision == 0
    assert not (run_dir / "state.json").exists()
    assert not list((run_dir / "confidential" / "internal_evidence").glob("*.json"))
