"""Statewise and expected regret derived from deterministic utilities."""

from __future__ import annotations

import math
from typing import Dict, Iterable, Mapping, Tuple

from .numeric import NumericCalculationError, stable_weighted_sum
from .schemas import CalculationTraceRow


class RegretCalculationError(ValueError):
    pass


def expected_regret_from_trace(rows: Iterable[CalculationTraceRow]) -> Dict[str, float]:
    records = (
        (float(row.probability), row.utility_by_action)
        for row in rows
    )
    return expected_regret_from_records(records)


def expected_regret_from_records(
    records: Iterable[Tuple[float, Mapping[str, float]]],
) -> Dict[str, float]:
    validated_records: list[tuple[float, Dict[str, float]]] = []
    expected_action_ids: set[str] | None = None
    weight_terms: list[float] = []
    for weight, utilities in records:
        if not math.isfinite(weight) or weight < 0.0:
            raise RegretCalculationError("regret weights must be finite and nonnegative")
        if not utilities:
            raise RegretCalculationError("at least one action utility is required")
        numeric_utilities = {action_id: float(value) for action_id, value in utilities.items()}
        action_ids = set(numeric_utilities)
        if expected_action_ids is None:
            expected_action_ids = action_ids
        elif action_ids != expected_action_ids:
            raise RegretCalculationError("every state must contain the same action utilities")
        if any(not math.isfinite(value) for value in numeric_utilities.values()):
            raise RegretCalculationError("state utilities must be finite")
        validated_records.append((weight, numeric_utilities))
        weight_terms.append(weight)
    try:
        total_weight = math.fsum(weight_terms)
    except OverflowError as exc:
        raise RegretCalculationError("regret weights overflowed") from exc
    if total_weight <= 0.0:
        raise RegretCalculationError("regret calculation requires positive weight")
    regret_pairs: Dict[str, list[tuple[float, float]]] = {
        action_id: [] for action_id in (expected_action_ids or set())
    }
    overflow_terms: Dict[str, list[float]] = {
        action_id: [] for action_id in (expected_action_ids or set())
    }
    for weight, utilities in validated_records:
        normalized_weight = weight / total_weight
        best = max(utilities.values())
        for action_id, utility in utilities.items():
            raw_regret = best - utility
            if math.isfinite(raw_regret):
                # Subtract first when representable so close-ULP differences at
                # huge scale are not erased by weighting both endpoints.
                if raw_regret < -1e-10:
                    raise RegretCalculationError("state regret cannot be negative")
                regret_pairs[action_id].append(
                    (normalized_weight, max(0.0, raw_regret))
                )
                continue
            else:
                try:
                    # Opposite max-float endpoints need weighting first because
                    # their raw difference overflows even when expectation does not.
                    weighted_regret = stable_weighted_sum(
                        ((normalized_weight, best), (-normalized_weight, utility))
                    )
                except NumericCalculationError as exc:
                    raise RegretCalculationError("weighted state regret overflowed") from exc
            if not math.isfinite(weighted_regret):
                raise RegretCalculationError("weighted state regret is not finite")
            if weighted_regret < -1e-10:
                raise RegretCalculationError("weighted state regret cannot be negative")
            overflow_terms[action_id].append(max(0.0, weighted_regret))
    try:
        expected = {
            action_id: math.fsum(
                [stable_weighted_sum(regret_pairs[action_id]), *overflow_terms[action_id]]
            )
            for action_id in regret_pairs
        }
    except (OverflowError, NumericCalculationError) as exc:
        raise RegretCalculationError("expected regret overflowed") from exc
    if any(not math.isfinite(value) for value in expected.values()):
        raise RegretCalculationError("expected regret is not finite")
    return expected
