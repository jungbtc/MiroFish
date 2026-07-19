"""Exact, deterministic expected-utility calculation for finite models."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .distributions import finite_support
from .numeric import NumericCalculationError, stable_weighted_sum
from .schemas import CalculationTraceRow, DecisionModel, StateValue
from .validation import (
    MAX_TABLE_STATES,
    approved_actions,
    approved_variables,
    state_assignment_key,
    validate_decision_model,
)


class ExpectedUtilityError(ValueError):
    pass


MAX_EXACT_WORK_ITEMS = 1_000_000
MIN_NORMAL_FLOAT = float.fromhex("0x1p-1022")


@dataclass(frozen=True)
class ExactEvaluation:
    expected_utility_by_action: Dict[str, float]
    recommended_action: str
    runner_up: str | None
    recommendation_margin: float
    trace_rows: List[CalculationTraceRow]


class PayoffEvaluator:
    """Compile a validated payoff definition into a small pure evaluator."""

    def __init__(self, model: DecisionModel):
        self._action_ids = [action.id for action in approved_actions(model)]
        self._table = {
            (outcome.action_id, state_assignment_key(outcome.state)): float(outcome.consequence)
            for outcome in model.utility_model.outcomes
            if outcome.action_id in self._action_ids
        }
        self._affine = {
            payoff.action_id: payoff
            for payoff in model.utility_model.affine_payoffs
            if payoff.action_id in self._action_ids
        }

    @property
    def action_ids(self) -> Sequence[str]:
        return tuple(self._action_ids)

    def utility(self, action_id: str, state: Mapping[str, StateValue]) -> float:
        payoff = self._affine.get(action_id)
        if payoff is not None:
            terms = [(1.0, float(payoff.intercept))]
            for variable_id, coefficient in sorted(payoff.coefficients.items()):
                state_value = state[variable_id]
                if not isinstance(state_value, (bool, int, float)):
                    raise ExpectedUtilityError(
                        f"state {variable_id} is not numeric for affine payoff {action_id}"
                    )
                try:
                    numeric_coefficient = float(coefficient)
                    numeric_state = float(state_value)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ExpectedUtilityError(
                        f"state {variable_id} is outside the numeric range for {action_id}"
                    ) from exc
                if not math.isfinite(numeric_coefficient) or not math.isfinite(numeric_state):
                    raise ExpectedUtilityError(
                        f"affine payoff term {variable_id} is not finite for {action_id}"
                    )
                terms.append((numeric_coefficient, numeric_state))
            try:
                value = stable_weighted_sum(terms)
            except NumericCalculationError as exc:
                raise ExpectedUtilityError(
                    f"affine payoff for action {action_id} overflowed"
                ) from exc
        else:
            try:
                value = self._table[(action_id, state_assignment_key(dict(state)))]
            except KeyError as exc:
                raise ExpectedUtilityError(
                    f"no payoff is defined for action {action_id} in the sampled state"
                ) from exc
        if not math.isfinite(value):
            raise ExpectedUtilityError(f"utility for action {action_id} is not finite")
        return value

    def utilities(self, state: Mapping[str, StateValue]) -> Dict[str, float]:
        return {action_id: self.utility(action_id, state) for action_id in self._action_ids}


def enumerate_joint_states(
    model: DecisionModel,
    *,
    fixed_values: Mapping[str, StateValue] | None = None,
) -> Iterable[Tuple[Dict[str, StateValue], float]]:
    fixed_values = dict(fixed_values or {})
    variables = approved_variables(model)
    unknown_fixed = set(fixed_values) - {variable.id for variable in variables}
    if unknown_fixed:
        raise ExpectedUtilityError(
            "fixed state references unknown variables: " + ", ".join(sorted(unknown_fixed))
        )

    free_variables = [variable for variable in variables if variable.id not in fixed_values]
    supports: List[List[Tuple[StateValue, float]]] = []
    for variable in free_variables:
        support = finite_support(variable.distribution)
        if support is None:
            raise ExpectedUtilityError(
                f"variable {variable.id} is continuous and cannot be enumerated exactly"
            )
        supports.append(support)
    state_count = math.prod(len(support) for support in supports) if supports else 1
    if state_count > MAX_TABLE_STATES:
        raise ExpectedUtilityError(
            f"exact enumeration exceeds the hard limit of {MAX_TABLE_STATES} states"
        )

    products = itertools.product(*supports) if supports else [tuple()]
    for combination in products:
        state = dict(fixed_values)
        probability_parts = []
        for variable, (value, probability) in zip(free_variables, combination):
            state[variable.id] = value
            probability_parts.append(probability)
        probability = math.prod(probability_parts) if probability_parts else 1.0
        if probability == 0.0 and probability_parts and all(
            part > 0.0 for part in probability_parts
        ):
            raise ExpectedUtilityError(
                "joint-state probability underflowed; exact float calculation is unsafe"
            )
        if (
            len(probability_parts) > 1
            and 0.0 < probability < MIN_NORMAL_FLOAT
            and all(part > 0.0 for part in probability_parts)
        ):
            # A rounded subnormal joint mass can have order-one relative error.
            # Multiplying that rounded mass by a large consequence can reverse a
            # recommendation, so exact enumeration fails closed here.
            raise ExpectedUtilityError(
                "joint-state probability is subnormal; exact float calculation is unsafe"
            )
        yield state, probability


def evaluate_exact(model: DecisionModel) -> ExactEvaluation:
    validate_decision_model(model)
    work_items = exact_work_item_count(model)
    if work_items is None:
        raise ExpectedUtilityError("continuous variables cannot be enumerated exactly")
    if work_items > MAX_EXACT_WORK_ITEMS:
        raise ExpectedUtilityError("exact calculation exceeds its work-item limit")
    evaluator = PayoffEvaluator(model)
    utility_pairs = {action_id: [] for action_id in evaluator.action_ids}
    trace_rows: List[CalculationTraceRow] = []
    probability_terms: List[float] = []

    for state, probability in enumerate_joint_states(model):
        utilities = evaluator.utilities(state)
        best_action = _rank_actions(utilities)[0]
        best_utility = utilities[best_action]
        for action_id, utility in utilities.items():
            utility_pairs[action_id].append((probability, utility))
        probability_terms.append(probability)
        trace_rows.append(
            CalculationTraceRow(
                state=state,
                probability=probability,
                utility_by_action=utilities,
                best_action=best_action,
                best_utility=best_utility,
            )
        )
    total_probability = math.fsum(probability_terms)
    if not math.isclose(total_probability, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ExpectedUtilityError("joint-state probabilities do not sum to 1")
    try:
        expected = {
            action_id: stable_weighted_sum(pairs)
            for action_id, pairs in utility_pairs.items()
        }
    except NumericCalculationError as exc:
        raise ExpectedUtilityError("expected utility overflowed") from exc
    if any(not math.isfinite(value) for value in expected.values()):
        raise ExpectedUtilityError("expected utility is not finite")

    ranked = _rank_actions(expected)
    recommended = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    margin = expected[recommended] - expected[runner_up] if runner_up else 0.0
    if not math.isfinite(margin):
        raise ExpectedUtilityError("recommendation margin is not finite")
    return ExactEvaluation(
        expected_utility_by_action=expected,
        recommended_action=recommended,
        runner_up=runner_up,
        recommendation_margin=max(0.0, margin),
        trace_rows=trace_rows,
    )


def conditional_expected_utilities(
    model: DecisionModel,
    variable_id: str,
    value: StateValue,
) -> Dict[str, float]:
    """Expected utilities conditional on one finite variable's state."""

    validate_decision_model(model)
    variable = next(
        (item for item in approved_variables(model) if item.id == variable_id),
        None,
    )
    if variable is None:
        raise ExpectedUtilityError(f"unknown approved variable: {variable_id}")
    support = finite_support(variable.distribution)
    if support is None or state_assignment_key({"value": value}) not in {
        state_assignment_key({"value": candidate}) for candidate, _ in support
    }:
        raise ExpectedUtilityError(f"value is outside finite support for variable {variable_id}")

    evaluator = PayoffEvaluator(model)
    utility_pairs = {action_id: [] for action_id in evaluator.action_ids}
    probability_terms: List[float] = []
    for state, probability in enumerate_joint_states(model, fixed_values={variable_id: value}):
        utilities = evaluator.utilities(state)
        for action_id, utility in utilities.items():
            utility_pairs[action_id].append((probability, utility))
        probability_terms.append(probability)
    total_probability = math.fsum(probability_terms)
    if not math.isclose(total_probability, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ExpectedUtilityError("conditional-state probabilities do not sum to 1")
    try:
        return {
            action_id: stable_weighted_sum(pairs)
            for action_id, pairs in utility_pairs.items()
        }
    except NumericCalculationError as exc:
        raise ExpectedUtilityError("conditional expected utility overflowed") from exc


def _rank_actions(values: Mapping[str, float]) -> List[str]:
    return sorted(values, key=lambda action_id: (-values[action_id], action_id))


def exact_state_count(model: DecisionModel) -> int | None:
    supports = [
        finite_support(variable.distribution) for variable in approved_variables(model)
    ]
    if any(support is None for support in supports):
        return None
    return math.prod(len(support) for support in supports if support is not None)


def exact_work_item_count(model: DecisionModel) -> int | None:
    state_count = exact_state_count(model)
    if state_count is None:
        return None
    return state_count * (
        len(approved_actions(model)) + len(approved_variables(model))
    )
