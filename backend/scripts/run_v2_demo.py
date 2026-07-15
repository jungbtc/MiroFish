"""Run the local MiroFish v2 demo pipeline."""

from __future__ import annotations

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.v2.pipeline import MiroFishV2Pipeline  # noqa: E402
from app.v2.storage import V2Storage  # noqa: E402


def main() -> None:
    pipeline = MiroFishV2Pipeline()
    state = pipeline.run_demo(rounds=3)
    report_path = V2Storage.report_path(state.run_id).resolve()

    print(f"run_id={state.run_id}")
    print(f"documents={len(state.documents)}")
    print(f"claims={len(state.claims)}")
    print(f"entities={len(state.entities)}")
    print(f"relationships={len(state.relationships)}")
    print(f"hypotheses={len(state.hypotheses)}")
    print(f"internal_questions={len(state.internal_questions)}")
    print(f"external_llm_calls={state.token_usage.external_llm_calls}")
    print(f"incremental_model_tokens={state.token_usage.total_tokens}")
    print(f"memo={report_path}")

    answer = pipeline.answer(state.run_id, "What evidence most supports the downside case?")
    print("follow_up_answer=" + answer["answer"].splitlines()[0])


if __name__ == "__main__":
    main()
