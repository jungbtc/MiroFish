"""Validation, finite support, and seeded sampling for approved distributions."""

from __future__ import annotations

import json
import math
import random
from typing import Callable, List, Optional, Sequence, Tuple

from .schemas import Distribution, StateValue


PROBABILITY_SUM_TOLERANCE = 1e-6
MAX_BOUNDED_NORMAL_ATTEMPTS = 10_000


class DistributionValidationError(ValueError):
    """Raised when distribution parameters cannot define a valid probability law."""


class DistributionSamplingError(RuntimeError):
    """Raised when a valid-looking distribution cannot be sampled safely."""


def state_value_key(value: StateValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_probabilities(
    probabilities: Sequence[float],
    *,
    tolerance: float = PROBABILITY_SUM_TOLERANCE,
) -> List[float]:
    """Validate probabilities and normalize only harmless decimal-rounding drift."""

    if not probabilities:
        raise DistributionValidationError("at least one probability is required")
    numeric = [float(value) for value in probabilities]
    if any(not math.isfinite(value) or value < 0.0 for value in numeric):
        raise DistributionValidationError("probabilities must be finite and nonnegative")
    total = math.fsum(numeric)
    if total <= 0.0:
        raise DistributionValidationError("probabilities must have positive total mass")
    if abs(total - 1.0) > tolerance:
        raise DistributionValidationError(
            f"probabilities must sum to 1 within tolerance {tolerance:g}"
        )
    return [value / total for value in numeric]


def finite_support(distribution: Distribution) -> Optional[List[Tuple[StateValue, float]]]:
    """Return normalized finite support, or ``None`` for a continuous law."""

    distribution_type = distribution.type
    if distribution_type == "categorical":
        rows = sorted(distribution.parameters.probabilities.items(), key=lambda row: row[0])
        normalized = normalize_probabilities([probability for _, probability in rows])
        return [(value, probability) for (value, _), probability in zip(rows, normalized)]
    if distribution_type == "discrete":
        rows = sorted(
            distribution.parameters.points,
            key=lambda point: state_value_key(point.value),
        )
        keys = [state_value_key(point.value) for point in rows]
        if len(keys) != len(set(keys)):
            raise DistributionValidationError("discrete values must be unique")
        normalized = normalize_probabilities([point.probability for point in rows])
        return [(point.value, probability) for point, probability in zip(rows, normalized)]
    if distribution_type == "bernoulli":
        probability_true = float(distribution.parameters.probability_true)
        return [(False, 1.0 - probability_true), (True, probability_true)]
    if distribution_type in {"fixed", "deterministic"}:
        return [(distribution.parameters.value, 1.0)]
    if distribution_type in {"beta", "normal", "triangular", "uniform"}:
        return None
    # Pydantic's discriminated union should make this unreachable.  Retaining a
    # fail-closed branch protects direct callers and future schema extensions.
    raise DistributionValidationError(f"unsupported distribution type: {distribution_type}")


def validate_distribution(distribution: Distribution) -> None:
    support = finite_support(distribution)
    if support is not None:
        probability_total = math.fsum(probability for _, probability in support)
        if not math.isclose(probability_total, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise DistributionValidationError("normalized support does not sum to 1")


def sample_distribution(distribution: Distribution, rng: random.Random) -> StateValue:
    """Draw one value using only the caller's local RNG."""

    return compile_sampler(distribution)(rng)


def compile_sampler(
    distribution: Distribution,
) -> Callable[[random.Random], StateValue]:
    """Validate and precompute immutable sampling data for repeated draws."""

    support = finite_support(distribution)
    if support is not None:
        cumulative_support = []
        cumulative = 0.0
        for value, probability in support:
            cumulative += probability
            cumulative_support.append((value, cumulative))

        def sample_finite(rng: random.Random) -> StateValue:
            draw = rng.random()
            for value, boundary in cumulative_support:
                if draw < boundary:
                    return value
            return cumulative_support[-1][0]

        return sample_finite

    parameters = distribution.parameters
    if distribution.type == "beta":
        alpha = float(parameters.alpha)
        beta = float(parameters.beta)
        return lambda rng: rng.betavariate(alpha, beta)
    if distribution.type == "normal":
        lower = parameters.lower_bound
        upper = parameters.upper_bound
        mean = float(parameters.mean)
        standard_deviation = float(parameters.standard_deviation)
        lower_value = float(lower) if lower is not None else None
        upper_value = float(upper) if upper is not None else None

        def sample_normal(rng: random.Random) -> StateValue:
            for _ in range(MAX_BOUNDED_NORMAL_ATTEMPTS):
                value = rng.gauss(mean, standard_deviation)
                if lower_value is not None and value < lower_value:
                    continue
                if upper_value is not None and value > upper_value:
                    continue
                if math.isfinite(value):
                    return value
            raise DistributionSamplingError(
                "bounded normal sampling did not converge within the hard attempt limit"
            )

        return sample_normal
    if distribution.type == "triangular":
        minimum = float(parameters.minimum)
        maximum = float(parameters.maximum)
        mode = float(parameters.mode)
        return lambda rng: rng.triangular(minimum, maximum, mode)
    if distribution.type == "uniform":
        minimum = float(parameters.minimum)
        maximum = float(parameters.maximum)
        return lambda rng: rng.uniform(minimum, maximum)
    raise DistributionSamplingError(f"unsupported distribution type: {distribution.type}")


def is_continuous(distribution: Distribution) -> bool:
    return finite_support(distribution) is None
