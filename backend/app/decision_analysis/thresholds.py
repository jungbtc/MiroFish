"""Analytical one-variable switching thresholds for binary uncertainties."""

from __future__ import annotations

import math
from typing import Dict, List, Mapping, Sequence

from .distributions import finite_support, state_value_key
from .expected_utility import conditional_expected_utilities, exact_state_count
from .numeric import NumericCalculationError, stable_weighted_mean, stable_weighted_sum
from .schemas import CalculationTraceRow, DecisionModel, SwitchingThreshold
from .validation import approved_actions, approved_variables, validate_decision_model


MAX_THRESHOLD_WORK_ITEMS = 1_000_000


class ThresholdLimitError(ValueError):
    pass


def binary_switching_thresholds(
    model: DecisionModel,
    *,
    trace_rows: Sequence[CalculationTraceRow] | None = None,
) -> List[SwitchingThreshold]:
    validate_decision_model(model)
    thresholds: List[SwitchingThreshold] = []
    variables = approved_variables(model)
    state_count = len(trace_rows) if trace_rows is not None else exact_state_count(model)
    if state_count is None:
        return []
    threshold_work = state_count * len(variables) * len(approved_actions(model))
    if threshold_work > MAX_THRESHOLD_WORK_ITEMS:
        raise ThresholdLimitError("switching-threshold analysis exceeds its work-item limit")

    for variable in variables:
        support = finite_support(variable.distribution)
        if support is None or len(support) != 2:
            continue
        lower_state, _ = support[0]
        upper_state, _ = support[1]
        if trace_rows is None:
            utility_at_lower = conditional_expected_utilities(model, variable.id, lower_state)
            utility_at_upper = conditional_expected_utilities(model, variable.id, upper_state)
        else:
            utility_at_lower = _conditional_from_trace(
                model, trace_rows, variable.id, lower_state
            )
            utility_at_upper = _conditional_from_trace(
                model, trace_rows, variable.id, upper_state
            )
        roots = _candidate_roots(utility_at_lower, utility_at_upper)
        boundaries = [0.0, *roots, 1.0]

        for index, root in enumerate(roots, start=1):
            below_probability = (boundaries[index - 1] + root) / 2.0
            above_probability = (root + boundaries[index + 1]) / 2.0
            action_below = _best_action_at_probability(
                utility_at_lower,
                utility_at_upper,
                below_probability,
            )
            action_above = _best_action_at_probability(
                utility_at_lower,
                utility_at_upper,
                above_probability,
            )
            if action_below == action_above:
                continue
            thresholds.append(
                SwitchingThreshold(
                    variable_id=variable.id,
                    lower_state=lower_state,
                    upper_state=upper_state,
                    probability_of_upper_state=root,
                    action_below=action_below,
                    action_above=action_above,
                )
            )
    return thresholds


def _conditional_from_trace(
    model: DecisionModel,
    rows: Sequence[CalculationTraceRow],
    variable_id: str,
    state_value,
) -> Dict[str, float]:
    target_key = state_value_key(state_value)
    matching = [
        row
        for row in rows
        if state_value_key(row.state[variable_id]) == target_key
    ]
    mass = math.fsum(float(row.probability) for row in matching)
    if mass <= 0.0:
        return conditional_expected_utilities(model, variable_id, state_value)
    try:
        return {
            action.id: stable_weighted_mean(
                (
                    float(row.probability),
                    float(row.utility_by_action[action.id]),
                )
                for row in matching
            )
            for action in approved_actions(model)
        }
    except NumericCalculationError as exc:
        raise ThresholdLimitError("conditional utility is not representable") from exc


def _candidate_roots(
    utility_at_lower: Mapping[str, float],
    utility_at_upper: Mapping[str, float],
) -> List[float]:
    action_ids = sorted(utility_at_lower)
    roots: List[float] = []
    for left_index, left_action in enumerate(action_ids):
        for right_action in action_ids[left_index + 1 :]:
            scale = max(
                abs(utility_at_lower[left_action]),
                abs(utility_at_lower[right_action]),
                abs(utility_at_upper[left_action]),
                abs(utility_at_upper[right_action]),
            )
            if scale == 0.0:
                continue
            lower_difference = (
                utility_at_lower[left_action] / scale
                - utility_at_lower[right_action] / scale
            )
            upper_difference = (
                utility_at_upper[left_action] / scale
                - utility_at_upper[right_action] / scale
            )
            slope = upper_difference - lower_difference
            if slope == 0.0:
                continue
            root = -lower_difference / slope
            if math.isfinite(root) and 0.0 < root < 1.0:
                roots.append(root)
    roots.sort()
    deduplicated: List[float] = []
    for root in roots:
        if not deduplicated or root != deduplicated[-1]:
            deduplicated.append(root)
    return deduplicated


def _best_action_at_probability(
    utility_at_lower: Mapping[str, float],
    utility_at_upper: Mapping[str, float],
    probability_of_upper: float,
) -> str:
    expected: Dict[str, float] = {
        action_id: _interpolated_utility(
            utility_at_lower[action_id],
            utility_at_upper[action_id],
            probability_of_upper,
        )
        for action_id in utility_at_lower
    }
    return min(expected, key=lambda action_id: (-expected[action_id], action_id))


def _interpolated_utility(lower: float, upper: float, probability: float) -> float:
    try:
        return stable_weighted_sum(
            ((1.0 - probability, lower), (probability, upper))
        )
    except NumericCalculationError as exc:
        raise ThresholdLimitError("interpolated utility is not representable") from exc
