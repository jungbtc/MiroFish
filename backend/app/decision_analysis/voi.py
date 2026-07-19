"""EVPI, EVPPI, and information-cost calculations from deterministic states."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .distributions import state_value_key
from .numeric import NumericCalculationError, stable_weighted_sum
from .schemas import InformationCost, StateValue


BASE_NUMERICAL_TOLERANCE = 1e-9
DEFAULT_CONTINUOUS_BINS = 20


class ValueOfInformationError(ValueError):
    pass


@dataclass(frozen=True)
class WeightedUtilityRecord:
    state: Mapping[str, StateValue]
    utilities: Mapping[str, float]
    weight: float


@dataclass(frozen=True)
class ValueOfInformationResult:
    current_value: float
    perfect_information_value: float
    evpi: float
    evppi_by_variable: Dict[str, float]
    evppi_by_group: Dict[str, float]
    warnings: List[str]


def calculate_value_of_information(
    records: Iterable[WeightedUtilityRecord],
    variable_ids: Sequence[str],
    *,
    continuous_variable_ids: Sequence[str] = (),
    continuous_bins: int = DEFAULT_CONTINUOUS_BINS,
    variable_groups: Mapping[str, Sequence[str]] | None = None,
) -> ValueOfInformationResult:
    rows = list(records)
    if not rows:
        raise ValueOfInformationError("value-of-information calculation requires states")
    if isinstance(continuous_bins, bool) or not isinstance(continuous_bins, int):
        raise ValueOfInformationError("continuous_bins must be an integer")
    if continuous_bins < 2:
        raise ValueOfInformationError("continuous_bins must be at least 2")
    if variable_groups is not None and not isinstance(variable_groups, Mapping):
        raise ValueOfInformationError("variable_groups must be an object")
    action_ids = sorted(rows[0].utilities)
    if not action_ids:
        raise ValueOfInformationError("value-of-information calculation requires actions")
    if any(set(row.utilities) != set(action_ids) for row in rows):
        raise ValueOfInformationError("every state must contain the same action utilities")
    if any(
        not math.isfinite(float(row.weight)) or float(row.weight) < 0.0
        for row in rows
    ):
        raise ValueOfInformationError("state weights must be finite and nonnegative")
    total_weight = math.fsum(float(row.weight) for row in rows)
    if total_weight <= 0.0:
        raise ValueOfInformationError("state weights must have positive mass")
    normalized_weights = [float(row.weight) / total_weight for row in rows]
    if any(
        not math.isfinite(float(value))
        for row in rows
        for value in row.utilities.values()
    ):
        raise ValueOfInformationError("utilities must be finite")

    try:
        expected_by_action = {
            action_id: stable_weighted_sum(
                (weight, float(row.utilities[action_id]))
                for row, weight in zip(rows, normalized_weights)
            )
            for action_id in action_ids
        }
    except NumericCalculationError as exc:
        raise ValueOfInformationError("expected utility is not representable") from exc
    current_value = max(expected_by_action.values())
    try:
        perfect_value = stable_weighted_sum(
            (
                weight,
                max(float(value) for value in row.utilities.values()),
            )
            for row, weight in zip(rows, normalized_weights)
        )
    except NumericCalculationError as exc:
        raise ValueOfInformationError("perfect-information value is not representable") from exc
    scale = max(
        1.0,
        abs(current_value),
        abs(perfect_value),
        *(abs(value) for value in expected_by_action.values()),
    )
    tolerance = max(BASE_NUMERICAL_TOLERANCE, scale * 1e-10)
    evpi = _validated_nonnegative(
        perfect_value - current_value,
        tolerance,
        label="EVPI",
    )

    continuous = set(continuous_variable_ids)
    warnings: List[str] = []
    evppi: Dict[str, float] = {}
    keys_by_variable: Dict[str, List[str]] = {}
    for variable_id in variable_ids:
        if any(variable_id not in row.state for row in rows):
            raise ValueOfInformationError(f"state is missing variable {variable_id}")
        if variable_id in continuous:
            group_keys = _continuous_quantile_groups(rows, variable_id, continuous_bins)
            warnings.append(
                f"EVPPI for continuous variable {variable_id} is a deterministic "
                f"{continuous_bins}-bin approximation."
            )
        else:
            group_keys = [state_value_key(row.state[variable_id]) for row in rows]
        keys_by_variable[variable_id] = group_keys
        evppi[variable_id] = _partition_evppi(
            rows,
            normalized_weights,
            action_ids,
            group_keys,
            current_value=current_value,
            evpi=evpi,
            tolerance=tolerance,
            label=f"EVPPI({variable_id})",
        )

    evppi_by_group: Dict[str, float] = {}
    known_variables = set(variable_ids)
    for group_id, members in (variable_groups or {}).items():
        if not isinstance(group_id, str) or not group_id.strip():
            raise ValueOfInformationError("EVPPI variable group IDs must be nonblank strings")
        if (
            not isinstance(members, Sequence)
            or isinstance(members, (str, bytes))
        ):
            raise ValueOfInformationError(f"EVPPI group {group_id} members must be a list")
        member_ids = list(members)
        if any(not isinstance(member, str) or not member for member in member_ids):
            raise ValueOfInformationError(
                f"EVPPI group {group_id} members must be variable IDs"
            )
        if not group_id or not member_ids:
            raise ValueOfInformationError("EVPPI variable groups require an ID and members")
        if len(member_ids) != len(set(member_ids)):
            raise ValueOfInformationError(f"EVPPI group {group_id} contains duplicate variables")
        unknown = set(member_ids) - known_variables
        if unknown:
            raise ValueOfInformationError(
                f"EVPPI group {group_id} references unknown variables: "
                + ", ".join(sorted(unknown))
            )
        group_keys = [
            "|".join(keys_by_variable[variable_id][row_index] for variable_id in member_ids)
            for row_index in range(len(rows))
        ]
        evppi_by_group[group_id] = _partition_evppi(
            rows,
            normalized_weights,
            action_ids,
            group_keys,
            current_value=current_value,
            evpi=evpi,
            tolerance=tolerance,
            label=f"EVPPI group {group_id}",
        )

    return ValueOfInformationResult(
        current_value=current_value,
        perfect_information_value=perfect_value,
        evpi=evpi,
        evppi_by_variable=evppi,
        evppi_by_group=evppi_by_group,
        warnings=warnings,
    )


def net_information_values(
    evppi_by_variable: Mapping[str, float],
    costs: Mapping[str, InformationCost] | None = None,
) -> Tuple[Dict[str, InformationCost], Dict[str, float]]:
    if costs is not None and not isinstance(costs, Mapping):
        raise ValueOfInformationError("information costs must be an object")
    costs = dict(costs or {})
    if any(not isinstance(variable_id, str) for variable_id in costs):
        raise ValueOfInformationError("information cost IDs must be strings")
    unknown_costs = set(costs) - set(evppi_by_variable)
    if unknown_costs:
        raise ValueOfInformationError(
            "information costs reference unknown variables: " + ", ".join(sorted(unknown_costs))
        )
    normalized_costs: Dict[str, InformationCost] = {}
    net_values: Dict[str, float] = {}
    for variable_id, evppi in evppi_by_variable.items():
        cost = costs.get(variable_id, InformationCost())
        normalized_costs[variable_id] = cost
        net = float(evppi) - float(cost.total_cost or 0.0)
        if not math.isfinite(net):
            raise ValueOfInformationError("net information value is not finite")
        net_values[variable_id] = net
    return normalized_costs, net_values


def _validated_nonnegative(value: float, tolerance: float, *, label: str) -> float:
    if not math.isfinite(value):
        raise ValueOfInformationError(f"{label} is not finite")
    if value < -tolerance:
        raise ValueOfInformationError(f"{label} is negative beyond numerical tolerance")
    return max(0.0, value)


def _partition_evppi(
    rows: Sequence[WeightedUtilityRecord],
    normalized_weights: Sequence[float],
    action_ids: Sequence[str],
    group_keys: Sequence[str],
    *,
    current_value: float,
    evpi: float,
    tolerance: float,
    label: str,
) -> float:
    group_terms: Dict[str, Dict[str, List[tuple[float, float]]]] = {}
    for row, weight, group_key in zip(rows, normalized_weights, group_keys):
        terms = group_terms.setdefault(
            group_key,
            {action_id: [] for action_id in action_ids},
        )
        for action_id in action_ids:
            terms[action_id].append((weight, float(row.utilities[action_id])))
    try:
        group_totals = [
            {
                action_id: stable_weighted_sum(action_terms)
                for action_id, action_terms in terms.items()
            }
            for terms in group_terms.values()
        ]
        partially_informed_value = math.fsum(
            max(totals.values()) for totals in group_totals
        )
    except (OverflowError, NumericCalculationError) as exc:
        raise ValueOfInformationError(f"{label} overflowed") from exc
    value = _validated_nonnegative(
        partially_informed_value - current_value,
        tolerance,
        label=label,
    )
    if value > evpi + tolerance:
        raise ValueOfInformationError(f"{label} exceeds EVPI beyond numerical tolerance")
    return min(value, evpi)


def _continuous_quantile_groups(
    rows: Sequence[WeightedUtilityRecord],
    variable_id: str,
    bin_count: int,
) -> List[str]:
    indexed_values = []
    for index, row in enumerate(rows):
        value = row.state[variable_id]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueOfInformationError(
                f"continuous variable {variable_id} produced a nonnumeric state"
            )
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueOfInformationError(
                f"continuous variable {variable_id} produced a nonfinite state"
            )
        indexed_values.append((numeric, index))
    indexed_values.sort(key=lambda item: (item[0], item[1]))
    groups = [""] * len(rows)
    denominator = max(1, len(rows))
    rank = 0
    while rank < len(indexed_values):
        value = indexed_values[rank][0]
        end = rank + 1
        while end < len(indexed_values) and indexed_values[end][0] == value:
            end += 1
        group = min(bin_count - 1, (rank * bin_count) // denominator)
        for _, original_index in indexed_values[rank:end]:
            groups[original_index] = f"quantile_{group:03d}"
        rank = end
    return groups
