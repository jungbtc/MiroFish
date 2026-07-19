"""Pure decision-analysis facade used by the v2 integration layer.

``evaluate_decision_model`` returns a structured ``needs_confirmation`` result
for valid proposals that lack human approval, and a ``calculated`` result only
after all calculation inputs pass the deterministic gate.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from pydantic import ValidationError

from .audit import CALCULATION_ENGINE_VERSION
from .distributions import finite_support
from .expected_utility import (
    MAX_EXACT_WORK_ITEMS,
    evaluate_exact,
    exact_work_item_count,
)
from .monte_carlo import DEFAULT_SAMPLE_COUNT, evaluate_monte_carlo
from .regret import expected_regret_from_trace
from .schemas import (
    ConvergenceDiagnostics,
    DecisionAnalysisOutcome,
    DecisionAnalysisResult,
    DecisionAnalysisTrace,
    DecisionModel,
    InformationCost,
    MissingConfirmation,
    NeedsConfirmationResult,
)
from .thresholds import ThresholdLimitError, binary_switching_thresholds
from .validation import (
    MAX_TABLE_STATES,
    DecisionModelNeedsConfirmation,
    approved_variables,
    calculate_model_hash,
    calculation_warnings,
    validate_decision_model,
)
from .voi import (
    WeightedUtilityRecord,
    calculate_value_of_information,
    net_information_values,
)


class DecisionAnalysisInputError(ValueError):
    pass


def evaluate_decision_model(
    model: DecisionModel | Mapping[str, Any],
    *,
    seed: int = 0,
    sample_count: int = DEFAULT_SAMPLE_COUNT,
    information_costs: Mapping[str, InformationCost | Mapping[str, Any]] | None = None,
    evppi_groups: Mapping[str, Sequence[str]] | None = None,
    force_method: str | None = None,
) -> DecisionAnalysisOutcome:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise DecisionAnalysisInputError("seed must be an integer")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise DecisionAnalysisInputError("sample_count must be an integer")
    if information_costs is not None and not isinstance(information_costs, Mapping):
        raise DecisionAnalysisInputError("information_costs must be an object")
    if evppi_groups is not None and not isinstance(evppi_groups, Mapping):
        raise DecisionAnalysisInputError("evppi_groups must be an object")
    try:
        # Pydantic models remain mutable after construction.  Reparse a dumped
        # instance so post-construction strings, booleans, or malformed nested
        # values cannot bypass the strict input contract.
        model_payload = (
            model.model_dump(mode="python", warnings=False)
            if isinstance(model, DecisionModel)
            else model
        )
        parsed = DecisionModel.model_validate(model_payload)
    except ValidationError as exc:
        if exc.errors() and all(error.get("type") == "missing" for error in exc.errors()):
            return NeedsConfirmationResult(
                missing_confirmations=[
                    MissingConfirmation(
                        field=".".join(str(item) for item in error["loc"]),
                        reason="This required decision-model field must be supplied and confirmed.",
                    )
                    for error in exc.errors()
                ]
            )
        raise DecisionAnalysisInputError("decision model payload is invalid") from exc

    try:
        validate_decision_model(parsed)
    except DecisionModelNeedsConfirmation as exc:
        return NeedsConfirmationResult(
            missing_confirmations=exc.issues,
            model_hash=calculate_model_hash(parsed),
        )

    model_hash = calculate_model_hash(parsed)
    variables = approved_variables(parsed)
    finite_supports = [finite_support(variable.distribution) for variable in variables]
    finite_state_count = (
        math.prod(len(support) for support in finite_supports if support is not None)
        if all(support is not None for support in finite_supports)
        else None
    )
    can_enumerate = (
        finite_state_count is not None
        and finite_state_count <= MAX_TABLE_STATES
        and (exact_work_item_count(parsed) or 0) <= MAX_EXACT_WORK_ITEMS
    )
    if force_method not in {None, "exact_enumeration", "monte_carlo"}:
        raise DecisionAnalysisInputError(
            "force_method must be exact_enumeration or monte_carlo"
        )
    if force_method == "exact_enumeration" and not can_enumerate:
        raise DecisionAnalysisInputError(
            "exact enumeration is unavailable for continuous or oversized state spaces"
        )
    use_exact = can_enumerate and force_method != "monte_carlo"
    warnings = calculation_warnings(parsed)

    if use_exact:
        exact = evaluate_exact(parsed)
        regret = expected_regret_from_trace(exact.trace_rows)
        voi_records = [
            WeightedUtilityRecord(
                state=row.state,
                utilities=row.utility_by_action,
                weight=float(row.probability),
            )
            for row in exact.trace_rows
        ]
        voi = calculate_value_of_information(
            voi_records,
            [variable.id for variable in variables],
            variable_groups=evppi_groups,
        )
        convergence = ConvergenceDiagnostics(
            batch_count=0,
            standard_error_by_action={
                action_id: 0.0 for action_id in exact.expected_utility_by_action
            },
            max_standard_error=0.0,
            stable_recommendation=True,
            recommendation_margin_to_error_ratio=1e12,
        )
        trace = DecisionAnalysisTrace(
            method="exact_enumeration",
            model_hash=model_hash,
            seed=seed,
            sample_count=0,
            enumerated_state_count=len(exact.trace_rows),
            rows=exact.trace_rows,
        )
        recommended_action = exact.recommended_action
        runner_up = exact.runner_up
        margin = exact.recommendation_margin
        expected_utility = exact.expected_utility_by_action
        try:
            thresholds = binary_switching_thresholds(
                parsed,
                trace_rows=exact.trace_rows,
            )
        except ThresholdLimitError:
            thresholds = []
            warnings.append(
                "Switching thresholds were omitted because their work limit was exceeded."
            )
        actual_sample_count = 0
        method = "exact_enumeration"
    else:
        sampled = evaluate_monte_carlo(
            parsed,
            seed=seed,
            sample_count=sample_count,
        )
        weight = 1.0 / sample_count
        voi = calculate_value_of_information(
            [
                WeightedUtilityRecord(
                    state=record.state,
                    utilities=record.utilities,
                    weight=weight,
                )
                for record in sampled.records
            ],
            [variable.id for variable in variables],
            continuous_variable_ids=[
                variable.id
                for variable, support in zip(variables, finite_supports)
                if support is None
            ],
            variable_groups=evppi_groups,
        )
        regret = sampled.expected_regret_by_action
        convergence = sampled.convergence
        trace = DecisionAnalysisTrace(
            method="monte_carlo",
            model_hash=model_hash,
            seed=seed,
            sample_count=sample_count,
            sample_preview=sampled.preview,
            sample_digest=sampled.sample_digest,
        )
        recommended_action = sampled.recommended_action
        runner_up = sampled.runner_up
        margin = sampled.recommendation_margin
        expected_utility = sampled.expected_utility_by_action
        thresholds = []
        actual_sample_count = sample_count
        method = "monte_carlo"
        if not convergence.stable_recommendation:
            warnings.append(
                "The sampled recommendation margin is small relative to its standard error."
            )

    warnings.extend(voi.warnings)
    parsed_costs = {}
    for variable_id, value in (information_costs or {}).items():
        if not isinstance(variable_id, str) or not variable_id:
            raise DecisionAnalysisInputError("information cost IDs must be nonblank strings")
        if not isinstance(value, (InformationCost, Mapping)):
            raise DecisionAnalysisInputError(
                f"information cost {variable_id} must be an object"
            )
        try:
            cost_payload = (
                value.model_dump(mode="python", warnings=False)
                if isinstance(value, InformationCost)
                else value
            )
            parsed_costs[variable_id] = InformationCost.model_validate(cost_payload)
        except ValidationError as exc:
            raise DecisionAnalysisInputError(
                f"information cost {variable_id} is invalid"
            ) from exc
    duplicate_group_ids = set(voi.evppi_by_group) & set(voi.evppi_by_variable)
    if duplicate_group_ids:
        raise DecisionAnalysisInputError(
            "EVPPI group IDs must not duplicate variable IDs: "
            + ", ".join(sorted(duplicate_group_ids))
        )
    all_evppi = {**voi.evppi_by_variable, **voi.evppi_by_group}
    normalized_costs, all_net_values = net_information_values(
        all_evppi,
        parsed_costs,
    )
    return DecisionAnalysisResult(
        recommended_action=recommended_action,
        runner_up=runner_up,
        recommendation_margin=max(0.0, float(margin)),
        expected_utility_by_action={
            action_id: _finite(float(value), "expected utility")
            for action_id, value in expected_utility.items()
        },
        expected_regret_by_action={
            action_id: max(0.0, _finite(float(value), "expected regret"))
            for action_id, value in regret.items()
        },
        evpi=voi.evpi,
        evppi_by_variable=voi.evppi_by_variable,
        evppi_by_group=voi.evppi_by_group,
        information_costs=normalized_costs,
        net_information_value_by_variable={
            variable_id: all_net_values[variable_id]
            for variable_id in voi.evppi_by_variable
        },
        net_information_value_by_group={
            group_id: all_net_values[group_id] for group_id in voi.evppi_by_group
        },
        switching_thresholds=thresholds,
        seed=seed,
        sample_count=actual_sample_count,
        model_hash=model_hash,
        model_version=parsed.version,
        calculation_engine_version=CALCULATION_ENGINE_VERSION,
        utility_model_version=parsed.utility_model.version,
        method=method,
        convergence=convergence,
        warnings=warnings,
        trace=trace,
    )


def _finite(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise DecisionAnalysisInputError(f"{label} is not finite")
    return value


__all__ = [
    "DecisionAnalysisInputError",
    "DecisionAnalysisOutcome",
    "DecisionAnalysisResult",
    "DecisionModel",
    "InformationCost",
    "NeedsConfirmationResult",
    "evaluate_decision_model",
]
