"""Bounded, seeded Monte Carlo execution using only the Python standard library."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List

from .distributions import compile_sampler, finite_support
from .expected_utility import PayoffEvaluator
from .numeric import NumericCalculationError, stable_mean
from .regret import expected_regret_from_records
from .schemas import CalculationTraceRow, ConvergenceDiagnostics, DecisionModel, StateValue
from .validation import approved_variables, validate_decision_model


DEFAULT_SAMPLE_COUNT = 10_000
MIN_SAMPLE_COUNT = 100
MAX_SAMPLE_COUNT = 100_000
DEFAULT_BATCH_SIZE = 500
MAX_RUNTIME_SECONDS = 10.0
TRACE_PREVIEW_SIZE = 25
MAX_SAMPLE_WORK_ITEMS = 5_000_000
RNG_PROBABILITY_RESOLUTION = 2.0**-53


class MonteCarloLimitError(ValueError):
    pass


@dataclass(frozen=True)
class SampleRecord:
    state: Dict[str, StateValue]
    utilities: Dict[str, float]


@dataclass(frozen=True)
class MonteCarloEvaluation:
    expected_utility_by_action: Dict[str, float]
    expected_regret_by_action: Dict[str, float]
    recommended_action: str
    runner_up: str | None
    recommendation_margin: float
    records: List[SampleRecord]
    preview: List[CalculationTraceRow]
    sample_digest: str
    convergence: ConvergenceDiagnostics


def evaluate_monte_carlo(
    model: DecisionModel,
    *,
    seed: int = 0,
    sample_count: int = DEFAULT_SAMPLE_COUNT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    runtime_limit_seconds: float = MAX_RUNTIME_SECONDS,
) -> MonteCarloEvaluation:
    validate_decision_model(model)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise MonteCarloLimitError("seed must be an integer")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise MonteCarloLimitError("sample_count must be an integer")
    if not MIN_SAMPLE_COUNT <= sample_count <= MAX_SAMPLE_COUNT:
        raise MonteCarloLimitError(
            f"sample_count must be between {MIN_SAMPLE_COUNT} and {MAX_SAMPLE_COUNT}"
        )
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise MonteCarloLimitError("batch_size must be a positive integer")
    if (
        isinstance(runtime_limit_seconds, bool)
        or not isinstance(runtime_limit_seconds, (int, float))
    ):
        raise MonteCarloLimitError("runtime_limit_seconds must be a finite number")
    runtime_limit_seconds = float(runtime_limit_seconds)
    if (
        not math.isfinite(runtime_limit_seconds)
        or runtime_limit_seconds <= 0.0
        or runtime_limit_seconds > MAX_RUNTIME_SECONDS
    ):
        raise MonteCarloLimitError(
            f"runtime_limit_seconds must be in (0, {MAX_RUNTIME_SECONDS:g}]"
        )

    variables = approved_variables(model)
    for variable in variables:
        support = finite_support(variable.distribution)
        if support is not None and any(
            0.0 < probability < RNG_PROBABILITY_RESOLUTION
            for _, probability in support
        ):
            raise MonteCarloLimitError(
                f"variable {variable.id} contains nonzero probability below RNG resolution"
            )
    samplers = [compile_sampler(variable.distribution) for variable in variables]
    evaluator = PayoffEvaluator(model)
    work_items = sample_count * (len(variables) + len(evaluator.action_ids))
    if work_items > MAX_SAMPLE_WORK_ITEMS:
        raise MonteCarloLimitError(
            "sample_count, actions, and variables exceed the Monte Carlo work limit"
        )
    rng = random.Random(seed)
    records: List[SampleRecord] = []
    preview: List[CalculationTraceRow] = []
    digest = hashlib.sha256()
    started = time.monotonic()

    for sample_index in range(sample_count):
        if time.monotonic() - started > runtime_limit_seconds:
            raise MonteCarloLimitError("Monte Carlo calculation exceeded its runtime limit")
        state = {
            variable.id: sampler(rng)
            for variable, sampler in zip(variables, samplers)
        }
        if time.monotonic() - started > runtime_limit_seconds:
            raise MonteCarloLimitError("Monte Carlo calculation exceeded its runtime limit")
        utilities = evaluator.utilities(state)
        for action_id, utility in utilities.items():
            if not math.isfinite(utility):
                raise MonteCarloLimitError("sampled utility is not finite")
        best_action = min(utilities, key=lambda action_id: (-utilities[action_id], action_id))
        record = SampleRecord(state=state, utilities=utilities)
        records.append(record)
        digest.update(
            json.dumps(
                {"state": state, "utilities": utilities},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )
        digest.update(b"\n")
        if sample_index < TRACE_PREVIEW_SIZE:
            preview.append(
                CalculationTraceRow(
                    state=state,
                    probability=1.0 / sample_count,
                    utility_by_action=utilities,
                    best_action=best_action,
                    best_utility=utilities[best_action],
                )
            )

    expected: Dict[str, float] = {}
    standard_errors: Dict[str, float] = {}
    for action_id in evaluator.action_ids:
        mean, standard_error = _scaled_mean_and_standard_error(
            [record.utilities[action_id] for record in records]
        )
        expected[action_id] = mean
        standard_errors[action_id] = standard_error
    ranked = sorted(expected, key=lambda action_id: (-expected[action_id], action_id))
    recommended = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    margin = expected[recommended] - expected[runner_up] if runner_up else 0.0
    if not math.isfinite(margin):
        raise MonteCarloLimitError("recommendation margin is not finite")
    if runner_up:
        combined_error = standard_errors[recommended] + standard_errors[runner_up]
        ratio = margin / combined_error if combined_error > 0.0 else 1e12
        stable = ratio >= 2.0
    else:
        ratio = 1e12
        stable = True
    regret = expected_regret_from_records(
        (1.0 / sample_count, record.utilities) for record in records
    )
    convergence = ConvergenceDiagnostics(
        batch_count=math.ceil(sample_count / batch_size),
        standard_error_by_action=standard_errors,
        max_standard_error=max(standard_errors.values(), default=0.0),
        stable_recommendation=stable,
        recommendation_margin_to_error_ratio=max(0.0, ratio),
    )
    return MonteCarloEvaluation(
        expected_utility_by_action=expected,
        expected_regret_by_action=regret,
        recommended_action=recommended,
        runner_up=runner_up,
        recommendation_margin=max(0.0, margin),
        records=records,
        preview=preview,
        sample_digest=digest.hexdigest(),
        convergence=convergence,
    )


def _scaled_mean_and_standard_error(values: List[float]) -> tuple[float, float]:
    if not values:
        raise MonteCarloLimitError("Monte Carlo summary requires samples")
    scale = max(abs(value) for value in values)
    if not math.isfinite(scale):
        raise MonteCarloLimitError("sampled utility scale is not finite")
    if scale == 0.0:
        return 0.0, 0.0
    normalized = [value / scale for value in values]
    normalized_mean = math.fsum(normalized) / len(normalized)
    # Convex averaging can only leave [-1, 1] through harmless roundoff.
    normalized_mean = max(-1.0, min(1.0, normalized_mean))
    try:
        mean = stable_mean(values)
    except NumericCalculationError as exc:
        raise MonteCarloLimitError("Monte Carlo mean is not representable") from exc
    if len(normalized) < 2:
        standard_error = 0.0
    else:
        squared_deviations = math.fsum(
            (value - normalized_mean) ** 2 for value in normalized
        )
        normalized_standard_error = math.sqrt(
            (squared_deviations / (len(normalized) - 1)) / len(normalized)
        )
        standard_error = scale * normalized_standard_error
    if not math.isfinite(mean) or not math.isfinite(standard_error):
        raise MonteCarloLimitError("Monte Carlo summary is not representable")
    return mean, standard_error
