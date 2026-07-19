"""Deterministic distribution updates for explicitly confirmed observations."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, Tuple

from pydantic import ValidationError

from .distributions import finite_support, state_value_key
from .numeric import NumericCalculationError, stable_weighted_sum
from .schemas import (
    BetaDistribution,
    BetaParameters,
    CategoricalDistribution,
    CategoricalParameters,
    DecisionModel,
    EvidenceObservation,
    EvidenceUpdateResult,
    FixedDistribution,
    FixedParameters,
    MAX_BETA_SHAPE,
    MAX_EVIDENCE_SAMPLE_SIZE,
    MAX_NORMAL_SCALE,
    MIN_NORMAL_SCALE,
    NormalDistribution,
    NormalParameters,
    UniformDistribution,
    UniformParameters,
)
from .validation import (
    DecisionModelNeedsConfirmation,
    DecisionModelValidationError,
    approved_variables,
    calculate_model_hash,
    has_valid_approval,
    validate_decision_model,
)


class EvidenceUpdateError(ValueError):
    pass


def apply_confirmed_observation(
    model: DecisionModel,
    observation: EvidenceObservation,
) -> EvidenceUpdateResult:
    """Return a new model; the supplied model is never mutated."""

    try:
        model = DecisionModel.model_validate(
            model.model_dump(mode="python", warnings=False)
        )
        observation = EvidenceObservation.model_validate(
            observation.model_dump(mode="python", warnings=False)
        )
    except (AttributeError, ValidationError) as exc:
        raise EvidenceUpdateError("model and evidence observation must be valid") from exc
    validate_decision_model(model)
    if observation.approval_status != "approved":
        raise EvidenceUpdateError("evidence observation must be explicitly approved")
    if not has_valid_approval(observation.approved_by, observation.approved_at):
        raise EvidenceUpdateError("evidence approval requires an actor and timestamp")
    updated = model.model_copy(deep=True)
    variable = next(
        (
            item
            for item in updated.uncertain_variables
            if item.id == observation.variable_id and item.approval_status == "approved"
        ),
        None,
    )
    if variable is None:
        raise EvidenceUpdateError("evidence references an unknown approved variable")
    if observation.source_evidence_id in variable.evidence_ids:
        return EvidenceUpdateResult(
            status="not_applied_to_distribution",
            variable_id=observation.variable_id,
            source_evidence_id=observation.source_evidence_id,
            reason="This confirmed evidence was already applied to the variable.",
            updated_model=updated,
        )

    try:
        distribution, reason = _updated_distribution(variable.distribution, observation)
    except (ValidationError, OverflowError) as exc:
        raise EvidenceUpdateError(
            "confirmed evidence is outside the supported distribution range"
        ) from exc
    if distribution is None:
        return EvidenceUpdateResult(
            status="not_applied_to_distribution",
            variable_id=observation.variable_id,
            source_evidence_id=observation.source_evidence_id,
            reason=reason,
            updated_model=updated,
        )

    variable.distribution = distribution
    if observation.source_evidence_id not in variable.evidence_ids:
        variable.evidence_ids.append(observation.source_evidence_id)
    version_digest = hashlib.sha256(
        json.dumps(
            {
                "prior_version": model.version,
                "observation": observation.model_dump(mode="json"),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    # Fixed-length content chaining remains reloadable after arbitrarily many
    # child evidence revisions and still binds the new version to its parent.
    updated.version = f"evidence-{version_digest[:32]}"
    updated.approved_by = observation.approved_by
    updated.approved_at = observation.approved_at
    updated.model_hash = None
    _filter_unreachable_payoff_rows(updated)
    try:
        # Reparse assignments through Pydantic so durability never depends on
        # in-memory assignment-validation settings.
        updated = DecisionModel.model_validate(updated.model_dump(mode="json"))
        validate_decision_model(updated)
    except (
        DecisionModelNeedsConfirmation,
        DecisionModelValidationError,
        ValidationError,
    ):
        return EvidenceUpdateResult(
            status="not_applied_to_distribution",
            variable_id=observation.variable_id,
            source_evidence_id=observation.source_evidence_id,
            reason=(
                "The confirmed observation requires new payoff or utility confirmation "
                "before it can change this distribution."
            ),
            updated_model=model.model_copy(deep=True),
        )
    updated.model_hash = calculate_model_hash(updated)
    updated = DecisionModel.model_validate(updated.model_dump(mode="json"))
    return EvidenceUpdateResult(
        status="applied",
        variable_id=observation.variable_id,
        source_evidence_id=observation.source_evidence_id,
        reason=reason,
        updated_model=updated,
    )


def _updated_distribution(distribution, observation: EvidenceObservation):
    common = {
        "source": f"confirmed_internal_evidence:{observation.source_evidence_id}",
        "approval_status": "approved",
        "proposed_by": distribution.proposed_by,
        "approved_by": observation.approved_by,
        "approved_at": observation.approved_at,
        "rationale": "Deterministic update from a human-confirmed observation.",
    }
    update_type = observation.observation_type
    if update_type == "replace_point":
        _require_state_value(observation.value)
        return (
            FixedDistribution(parameters=FixedParameters(value=observation.value), **common),
            "Replaced the approved point estimate with the confirmed value.",
        )

    if update_type == "categorical_probabilities":
        if not isinstance(observation.value, dict):
            raise EvidenceUpdateError("categorical update value must be a probability object")
        if any(
            not isinstance(label, str) or not label.strip()
            for label in observation.value
        ):
            raise EvidenceUpdateError("categorical probability labels must be nonblank strings")
        probabilities = {
            label: _finite_number(probability, f"probability for {label}")
            for label, probability in observation.value.items()
        }
        return (
            CategoricalDistribution(
                parameters=CategoricalParameters(probabilities=probabilities),
                **common,
            ),
            "Replaced categorical probabilities with the confirmed distribution.",
        )

    if update_type == "beta_counts":
        if distribution.type != "beta":
            return None, "Beta counts were retained but the target is not a beta distribution."
        payload = _require_mapping(observation.value, "beta count update")
        successes = _nonnegative_integer(payload.get("successes"), "successes")
        failures = _nonnegative_integer(payload.get("failures"), "failures")
        if successes + failures <= 0:
            raise EvidenceUpdateError("beta update requires at least one confirmed observation")
        if (
            observation.sample_size is not None
            and observation.sample_size != successes + failures
        ):
            raise EvidenceUpdateError(
                "beta success and failure counts must equal the confirmed sample size"
            )
        new_alpha = float(distribution.parameters.alpha) + successes
        new_beta = float(distribution.parameters.beta) + failures
        if new_alpha > MAX_BETA_SHAPE or new_beta > MAX_BETA_SHAPE:
            raise EvidenceUpdateError("updated beta shape exceeds the supported numerical range")
        return (
            BetaDistribution(
                parameters=BetaParameters(
                    alpha=new_alpha,
                    beta=new_beta,
                ),
                **common,
            ),
            "Updated beta shape parameters from confirmed success and failure counts.",
        )

    if update_type == "normal_observation":
        if distribution.type != "normal":
            return None, "Numeric observation was retained but the target is not a normal distribution."
        if (
            distribution.parameters.lower_bound is not None
            or distribution.parameters.upper_bound is not None
        ):
            return (
                None,
                "A bounded normal prior needs an explicit truncated-normal update model.",
            )
        payload = _require_mapping(observation.value, "normal observation")
        observed = _finite_number(payload.get("observation"), "observation")
        standard_error_value = payload.get("standard_error")
        if standard_error_value is None and payload.get("standard_deviation") is not None:
            if not observation.sample_size:
                return (
                    None,
                    "Normal observation needs a confirmed sample size or explicit standard error.",
                )
            standard_error_value = _finite_number(
                payload["standard_deviation"],
                "observation standard deviation",
            ) / math.sqrt(observation.sample_size)
        if standard_error_value is None:
            return None, "Normal observation needs an explicit confirmed standard error."
        standard_error = _finite_number(standard_error_value, "standard error")
        if not MIN_NORMAL_SCALE <= standard_error <= MAX_NORMAL_SCALE:
            raise EvidenceUpdateError(
                "standard error is outside the supported numerical range"
            )
        prior_mean = float(distribution.parameters.mean)
        prior_variance = float(distribution.parameters.standard_deviation) ** 2
        observation_variance = standard_error**2
        if prior_variance >= observation_variance:
            ratio = observation_variance / prior_variance
            prior_weight = ratio / (1.0 + ratio)
            observation_weight = 1.0 / (1.0 + ratio)
            posterior_variance = observation_variance / (1.0 + ratio)
        else:
            ratio = prior_variance / observation_variance
            prior_weight = 1.0 / (1.0 + ratio)
            observation_weight = ratio / (1.0 + ratio)
            posterior_variance = prior_variance / (1.0 + ratio)
        try:
            posterior_mean = stable_weighted_sum(
                ((prior_weight, prior_mean), (observation_weight, observed))
            )
        except NumericCalculationError as exc:
            raise EvidenceUpdateError("normal posterior mean is not representable") from exc
        posterior_standard_deviation = math.sqrt(posterior_variance)
        if (
            not math.isfinite(posterior_mean)
            or not MIN_NORMAL_SCALE
            <= posterior_standard_deviation
            <= MAX_NORMAL_SCALE
        ):
            raise EvidenceUpdateError("normal posterior is outside the supported numerical range")
        return (
            NormalDistribution(
                parameters=NormalParameters(
                    mean=posterior_mean,
                    standard_deviation=posterior_standard_deviation,
                    lower_bound=distribution.parameters.lower_bound,
                    upper_bound=distribution.parameters.upper_bound,
                ),
                **common,
            ),
            "Applied a normal-normal update using the confirmed observation error.",
        )

    if update_type == "hard_range":
        payload = _require_mapping(observation.value, "hard range")
        lower = payload.get("lower_bound")
        upper = payload.get("upper_bound")
        if lower is None and upper is None:
            raise EvidenceUpdateError("hard range requires a lower or upper bound")
        lower_value = _finite_number(lower, "lower bound") if lower is not None else None
        upper_value = _finite_number(upper, "upper bound") if upper is not None else None
        if lower_value is not None and upper_value is not None and lower_value >= upper_value:
            raise EvidenceUpdateError("hard range lower bound must be less than upper bound")
        return _apply_hard_range(distribution, lower_value, upper_value, common)

    return None, "The confirmed observation type is not supported by this engine version."


def _apply_hard_range(distribution, lower, upper, common):
    if distribution.type == "normal":
        current_lower = distribution.parameters.lower_bound
        current_upper = distribution.parameters.upper_bound
        new_lower = max(value for value in (current_lower, lower) if value is not None) \
            if current_lower is not None or lower is not None else None
        new_upper = min(value for value in (current_upper, upper) if value is not None) \
            if current_upper is not None or upper is not None else None
        if new_lower is not None and new_upper is not None and new_lower >= new_upper:
            raise EvidenceUpdateError("confirmed range has no overlap with the normal bounds")
        return (
            NormalDistribution(
                parameters=NormalParameters(
                    mean=distribution.parameters.mean,
                    standard_deviation=distribution.parameters.standard_deviation,
                    lower_bound=new_lower,
                    upper_bound=new_upper,
                ),
                **common,
            ),
            "Intersected the normal distribution with the confirmed hard range.",
        )
    if distribution.type == "uniform":
        new_minimum = max(
            float(distribution.parameters.minimum),
            lower if lower is not None else float(distribution.parameters.minimum),
        )
        new_maximum = min(
            float(distribution.parameters.maximum),
            upper if upper is not None else float(distribution.parameters.maximum),
        )
        if new_minimum >= new_maximum:
            raise EvidenceUpdateError("confirmed range has no overlap with the uniform range")
        return (
            UniformDistribution(
                parameters=UniformParameters(minimum=new_minimum, maximum=new_maximum),
                **common,
            ),
            "Intersected the uniform distribution with the confirmed hard range.",
        )
    if distribution.type in {"fixed", "deterministic"}:
        value = distribution.parameters.value
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None, "A numeric hard range cannot be applied to a nonnumeric fixed value."
        numeric_value = _finite_number(value, "fixed value")
        if lower is not None and numeric_value < lower:
            raise EvidenceUpdateError("fixed value is below the confirmed hard range")
        if upper is not None and numeric_value > upper:
            raise EvidenceUpdateError("fixed value is above the confirmed hard range")
        return distribution.model_copy(update=common), "Confirmed range retains the existing fixed value."
    return None, "The hard range was retained but this distribution type cannot apply it safely."


def _require_mapping(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceUpdateError(f"{label} value must be an object")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceUpdateError(f"{label} must be a finite number")
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceUpdateError(f"{label} must be a finite number") from exc
    if not math.isfinite(numeric):
        raise EvidenceUpdateError(f"{label} must be a finite number")
    return numeric


def _nonnegative_integer(value: Any, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_EVIDENCE_SAMPLE_SIZE
    ):
        raise EvidenceUpdateError(
            f"{label} must be a nonnegative integer no greater than "
            f"{MAX_EVIDENCE_SAMPLE_SIZE}"
        )
    return value


def _require_state_value(value: Any) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, str):
        if len(value) > 10_000:
            raise EvidenceUpdateError("point estimate string is too long")
        return
    if isinstance(value, (int, float)):
        _finite_number(value, "point estimate")
        return
    raise EvidenceUpdateError("point estimate must be a finite scalar value")


def _filter_unreachable_payoff_rows(model: DecisionModel) -> None:
    """Drop only payoff rows made unreachable by a confirmed finite update."""

    if not model.utility_model.outcomes:
        return
    support_keys: Dict[str, set[str]] = {}
    for variable in approved_variables(model):
        support = finite_support(variable.distribution)
        if support is None:
            return
        support_keys[variable.id] = {
            state_value_key(value) for value, _ in support
        }
    model.utility_model.outcomes = [
        outcome
        for outcome in model.utility_model.outcomes
        if all(
            variable_id in outcome.state
            and state_value_key(outcome.state[variable_id]) in possible_values
            for variable_id, possible_values in support_keys.items()
        )
    ]
