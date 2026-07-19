"""Approval gates, semantic validation, and canonical decision-model hashing."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence

from .distributions import finite_support, state_value_key, validate_distribution
from .schemas import (
    Action,
    DecisionModel,
    MAX_ACTIONS,
    MAX_VARIABLES,
    MissingConfirmation,
    UncertainVariable,
)


MAX_TABLE_STATES = 100_000


class DecisionModelNeedsConfirmation(ValueError):
    def __init__(self, issues: Sequence[MissingConfirmation]):
        self.issues = list(issues)
        super().__init__("decision model requires human confirmation")


class DecisionModelValidationError(ValueError):
    def __init__(self, message: str, *, field: str | None = None):
        self.field = field
        super().__init__(message)


def approved_actions(model: DecisionModel) -> List[Action]:
    return sorted(
        (action for action in model.actions if action.status == "approved"),
        key=lambda action: action.id,
    )


def approved_variables(model: DecisionModel) -> List[UncertainVariable]:
    return sorted(
        (
            variable
            for variable in model.uncertain_variables
            if variable.approval_status == "approved"
        ),
        key=lambda variable: variable.id,
    )


def collect_missing_confirmations(model: DecisionModel) -> List[MissingConfirmation]:
    issues: List[MissingConfirmation] = []
    if model.approval_status != "approved":
        issues.append(
            MissingConfirmation(
                field="approval_status",
                item_id=model.id,
                reason="The decision model must be explicitly approved.",
            )
        )
    elif not has_valid_approval(model.approved_by, model.approved_at):
        issues.append(
            MissingConfirmation(
                field="model_approval",
                item_id=model.id,
                reason="The model approval requires an actor and timestamp.",
            )
        )

    actions = approved_actions(model)
    if len(actions) < 2:
        candidates = [action for action in model.actions if action.status == "proposed"]
        if candidates:
            for action in candidates:
                issues.append(
                    MissingConfirmation(
                        field="actions",
                        item_id=action.id,
                        reason="Confirm whether this proposed action is actually available.",
                    )
                )
        else:
            issues.append(
                MissingConfirmation(
                    field="actions",
                    reason="At least two available actions must be approved.",
                )
            )
    for action in actions:
        if not has_valid_approval(action.approved_by, action.approved_at):
            issues.append(
                MissingConfirmation(
                    field="action_approval",
                    item_id=action.id,
                    reason="The action approval requires an actor and timestamp.",
                )
            )

    variables = approved_variables(model)
    if not variables:
        proposed = [
            variable
            for variable in model.uncertain_variables
            if variable.approval_status == "proposed"
        ]
        if proposed:
            for variable in proposed:
                issues.append(
                    MissingConfirmation(
                        field="uncertain_variables",
                        item_id=variable.id,
                        reason="Confirm this uncertain variable and its unit.",
                    )
                )
        else:
            issues.append(
                MissingConfirmation(
                    field="uncertain_variables",
                    reason="At least one uncertain variable must be approved.",
                )
            )
    for variable in variables:
        if not has_valid_approval(variable.approved_by, variable.approved_at):
            issues.append(
                MissingConfirmation(
                    field="variable_approval",
                    item_id=variable.id,
                    reason="The variable approval requires an actor and timestamp.",
                )
            )
        if (
            variable.distribution.approval_status != "approved"
            or not has_valid_approval(
                variable.distribution.approved_by,
                variable.distribution.approved_at,
            )
        ):
            issues.append(
                MissingConfirmation(
                    field="distribution",
                    item_id=variable.id,
                    reason="Confirm the proposed distribution and record its approver.",
                )
            )

    utility = model.utility_model
    if utility.approval_status != "approved":
        issues.append(
            MissingConfirmation(
                field="utility_model",
                reason="Consequences and the utility model must be explicitly approved.",
            )
        )
    elif not has_valid_approval(utility.approved_by, utility.approved_at):
        issues.append(
            MissingConfirmation(
                field="utility_model_approval",
                reason="The utility approval requires an actor and timestamp.",
            )
        )
    return issues


def has_valid_approval(actor: str | None, approved_at: str | None) -> bool:
    if not isinstance(actor, str) or not actor.strip():
        return False
    if not isinstance(approved_at, str) or not approved_at.strip():
        return False
    try:
        datetime.fromisoformat(approved_at.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_decision_model(model: DecisionModel, *, require_approved: bool = True) -> None:
    if require_approved:
        issues = collect_missing_confirmations(model)
        if issues:
            raise DecisionModelNeedsConfirmation(issues)

    actions = approved_actions(model)
    variables = approved_variables(model)
    if len(actions) < 2:
        raise DecisionModelValidationError("at least two approved actions are required")
    if len(model.actions) > MAX_ACTIONS:
        raise DecisionModelValidationError(
            f"decision models support at most {MAX_ACTIONS} actions"
        )
    if not variables:
        raise DecisionModelValidationError("at least one approved uncertain variable is required")
    if len(variables) > MAX_VARIABLES:
        raise DecisionModelValidationError(
            f"decision models support at most {MAX_VARIABLES} approved variables"
        )
    _require_unique_ids(model.actions, "action")
    _require_unique_ids(model.uncertain_variables, "uncertain variable")
    if not model.consequence_unit.strip():
        raise DecisionModelValidationError("consequence_unit must be explicit")
    if model.utility_model.unit != model.consequence_unit:
        raise DecisionModelValidationError(
            "utility outputs and consequences must use one shared unit"
        )

    variable_by_id = {variable.id: variable for variable in variables}
    for variable in variables:
        if not variable.unit.strip():
            raise DecisionModelValidationError(
                f"uncertain variable {variable.id} requires an explicit unit"
            )
        validate_distribution(variable.distribution)
        unknown_dependencies = set(variable.dependencies) - variable_by_id.keys()
        if unknown_dependencies:
            raise DecisionModelValidationError(
                f"variable {variable.id} references unknown dependencies: "
                f"{', '.join(sorted(unknown_dependencies))}"
            )
        if variable.id in variable.dependencies:
            raise DecisionModelValidationError(
                f"dependency cycle detected at variable {variable.id}"
            )
    _reject_dependency_cycles(variables)
    if any(variable.dependencies for variable in variables):
        raise DecisionModelValidationError(
            "conditional distributions are not supported yet; dependency declarations cannot be calculated"
        )

    _validate_payoffs(model, actions, variables)
    expected_hash = calculate_model_hash(model)
    if model.model_hash is not None and model.model_hash != expected_hash:
        raise DecisionModelValidationError(
            "model_hash does not match the canonical approved calculation inputs"
        )


def calculation_warnings(model: DecisionModel) -> List[str]:
    warnings: List[str] = []
    excluded_actions = [action.id for action in model.actions if action.status != "approved"]
    excluded_variables = [
        variable.id
        for variable in model.uncertain_variables
        if variable.approval_status != "approved"
    ]
    if excluded_actions:
        warnings.append(
            "Unapproved actions were excluded from calculation: " + ", ".join(sorted(excluded_actions))
        )
    if excluded_variables:
        warnings.append(
            "Unapproved variables were excluded from calculation: "
            + ", ".join(sorted(excluded_variables))
        )
    return warnings


def canonical_model_payload(model: DecisionModel) -> Dict[str, Any]:
    """Return only approved inputs that can affect deterministic results."""

    actions = sorted(approved_actions(model), key=lambda action: action.id)
    variables = sorted(approved_variables(model), key=lambda variable: variable.id)
    approved_action_ids = {action.id for action in actions}
    approved_variable_ids = {variable.id for variable in variables}
    outcomes = [
        outcome
        for outcome in model.utility_model.outcomes
        if outcome.action_id in approved_action_ids
    ]
    outcomes.sort(
        key=lambda outcome: (
            outcome.action_id,
            state_assignment_key(outcome.state),
            float(outcome.consequence),
        )
    )
    affine_payoffs = [
        payoff
        for payoff in model.utility_model.affine_payoffs
        if payoff.action_id in approved_action_ids
    ]
    affine_payoffs.sort(key=lambda payoff: payoff.action_id)

    return {
        "id": model.id,
        "version": model.version,
        "question": model.question,
        "consequence_unit": model.consequence_unit,
        "actions": [{"id": action.id} for action in actions],
        "uncertain_variables": [
            {
                "id": variable.id,
                "unit": variable.unit,
                "distribution": {
                    "type": (
                        "fixed"
                        if variable.distribution.type == "deterministic"
                        else variable.distribution.type
                    ),
                    "parameters": _canonical_distribution_parameters(variable),
                },
                "dependencies": sorted(variable.dependencies),
            }
            for variable in variables
        ],
        "utility_model": {
            "type": model.utility_model.type,
            "risk_attitude": model.utility_model.risk_attitude,
            "unit": model.utility_model.unit,
            "version": model.utility_model.version,
            "outcomes": [outcome.model_dump(mode="json") for outcome in outcomes],
            "affine_payoffs": [
                {
                    **payoff.model_dump(mode="json"),
                    "coefficients": {
                        variable_id: coefficient
                        for variable_id, coefficient in sorted(payoff.coefficients.items())
                        if variable_id in approved_variable_ids
                    },
                }
                for payoff in affine_payoffs
            ],
        },
    }


def calculate_model_hash(model: DecisionModel) -> str:
    canonical = json.dumps(
        canonical_model_payload(model),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def with_model_hash(model: DecisionModel) -> DecisionModel:
    return model.model_copy(update={"model_hash": calculate_model_hash(model)}, deep=True)


def _require_unique_ids(items: Iterable[Any], label: str) -> None:
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise DecisionModelValidationError(f"{label} IDs must be unique")


def _reject_dependency_cycles(variables: Sequence[UncertainVariable]) -> None:
    dependencies = {variable.id: tuple(variable.dependencies) for variable in variables}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(variable_id: str) -> None:
        if variable_id in visiting:
            raise DecisionModelValidationError(
                f"dependency cycle detected at variable {variable_id}"
            )
        if variable_id in visited:
            return
        visiting.add(variable_id)
        for dependency_id in dependencies[variable_id]:
            visit(dependency_id)
        visiting.remove(variable_id)
        visited.add(variable_id)

    for variable_id in dependencies:
        visit(variable_id)


def _validate_payoffs(
    model: DecisionModel,
    actions: Sequence[Action],
    variables: Sequence[UncertainVariable],
) -> None:
    action_ids = {action.id for action in actions}
    variable_ids = {variable.id for variable in variables}
    outcomes_by_action: Dict[str, list] = {action_id: [] for action_id in action_ids}
    affine_by_action: Dict[str, list] = {action_id: [] for action_id in action_ids}

    for outcome in model.utility_model.outcomes:
        if outcome.action_id not in action_ids:
            raise DecisionModelValidationError(
                f"outcome references unapproved or unknown action {outcome.action_id}"
            )
        if outcome.consequence_unit != model.consequence_unit:
            raise DecisionModelValidationError(
                f"outcome for {outcome.action_id} uses a different consequence unit"
            )
        if set(outcome.state) != variable_ids:
            raise DecisionModelValidationError(
                f"outcome for {outcome.action_id} must name every approved variable exactly once"
            )
        outcomes_by_action[outcome.action_id].append(outcome)

    for payoff in model.utility_model.affine_payoffs:
        if payoff.action_id not in action_ids:
            raise DecisionModelValidationError(
                f"affine payoff references unapproved or unknown action {payoff.action_id}"
            )
        if payoff.consequence_unit != model.consequence_unit:
            raise DecisionModelValidationError(
                f"affine payoff for {payoff.action_id} uses a different consequence unit"
            )
        unknown_coefficients = set(payoff.coefficients) - variable_ids
        if unknown_coefficients:
            raise DecisionModelValidationError(
                f"affine payoff for {payoff.action_id} references unknown variables: "
                + ", ".join(sorted(unknown_coefficients))
            )
        affine_by_action[payoff.action_id].append(payoff)

    variable_by_id = {variable.id: variable for variable in variables}
    for action_id in sorted(action_ids):
        table_rows = outcomes_by_action[action_id]
        affine_rows = affine_by_action[action_id]
        if bool(table_rows) == bool(affine_rows):
            raise DecisionModelValidationError(
                f"action {action_id} requires exactly one payoff table or affine payoff"
            )
        if len(affine_rows) > 1:
            raise DecisionModelValidationError(
                f"action {action_id} has duplicate affine payoff definitions"
            )
        if affine_rows:
            for variable_id in affine_rows[0].coefficients:
                support = finite_support(variable_by_id[variable_id].distribution)
                if support is not None and any(
                    not isinstance(value, (bool, int, float)) for value, _ in support
                ):
                    raise DecisionModelValidationError(
                        f"affine payoff coefficient {variable_id} requires numeric states"
                    )

    if any(outcomes_by_action.values()):
        supports = []
        for variable in variables:
            support = finite_support(variable.distribution)
            if support is None:
                raise DecisionModelValidationError(
                    "payoff tables cannot be used with continuous variables; use affine payoffs"
                )
            supports.append([value for value, _ in support])
        state_count = math.prod(len(support) for support in supports)
        if state_count > MAX_TABLE_STATES:
            raise DecisionModelValidationError(
                f"payoff table would require more than {MAX_TABLE_STATES} states"
            )
        expected_states = {
            state_assignment_key(dict(zip((variable.id for variable in variables), values)))
            for values in itertools.product(*supports)
        }
        for action_id, rows in outcomes_by_action.items():
            if not rows:
                continue
            actual_states = [state_assignment_key(outcome.state) for outcome in rows]
            if len(actual_states) != len(set(actual_states)):
                raise DecisionModelValidationError(
                    f"action {action_id} has duplicate payoff-table states"
                )
            if set(actual_states) != expected_states:
                raise DecisionModelValidationError(
                    f"action {action_id} payoff table does not cover every possible state"
                )


def state_assignment_key(state: Dict[str, Any]) -> str:
    normalized = {key: json.loads(state_value_key(value)) for key, value in state.items()}
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_distribution_parameters(variable: UncertainVariable) -> Dict[str, Any]:
    parameters = variable.distribution.parameters.model_dump(mode="json")
    if variable.distribution.type == "discrete":
        parameters["points"] = sorted(
            parameters["points"],
            key=lambda point: state_value_key(point["value"]),
        )
    return parameters
