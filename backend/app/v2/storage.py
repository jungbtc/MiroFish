"""Local, demo-safe persistence for MiroFish v2 runs."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from ..config import Config
from .schemas import V2RunState


class V2Storage:
    RUNS_DIR = Path(Config.UPLOAD_FOLDER) / "v2_runs"

    @classmethod
    def ensure_root(cls) -> None:
        cls.RUNS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create_run_id(cls) -> str:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"v2_{stamp}_{uuid4().hex[:8]}"

    @classmethod
    def run_dir(cls, run_id: str) -> Path:
        cls.ensure_root()
        return cls.RUNS_DIR / run_id

    @classmethod
    def pack_dir(cls, run_id: str) -> Path:
        return cls.run_dir(run_id) / "research_pack"

    @classmethod
    def state_path(cls, run_id: str) -> Path:
        return cls.run_dir(run_id) / "state.json"

    @classmethod
    def report_path(cls, run_id: str) -> Path:
        return cls.run_dir(run_id) / "forecast_report.md"

    @classmethod
    def artifact_path(cls, run_id: str, filename: str) -> Path:
        return cls.run_dir(run_id) / filename

    @classmethod
    def save_state(cls, state: V2RunState) -> None:
        state.touch()
        run_dir = cls.run_dir(state.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = state.model_dump(mode="json")
        with cls.state_path(state.run_id).open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        cls._write_artifact(state.run_id, "graph.json", state.graph)
        cls._write_artifact(state.run_id, "agents.json", [a.model_dump(mode="json") for a in state.agents])
        cls._write_artifact(state.run_id, "simulation_rounds.json", [r.model_dump(mode="json") for r in state.rounds])
        cls._write_artifact(state.run_id, "scenario_scores.json", [s.model_dump(mode="json") for s in state.scores])
        if state.report:
            with cls.report_path(state.run_id).open("w", encoding="utf-8") as f:
                f.write(state.report.markdown)

    @classmethod
    def load_state(cls, run_id: str) -> V2RunState:
        path = cls.state_path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"v2 run not found: {run_id}")
        with path.open("r", encoding="utf-8") as f:
            return V2RunState.model_validate(json.load(f))

    @classmethod
    def safe_filename(cls, filename: str) -> str:
        base = os.path.basename(filename or "document.txt")
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base)
        return safe or "document.txt"

    @classmethod
    def _write_artifact(cls, run_id: str, filename: str, payload: Any) -> None:
        with cls.artifact_path(run_id, filename).open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
