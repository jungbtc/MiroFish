"""Numerically stable primitives shared by deterministic calculations."""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Iterable, Tuple


class NumericCalculationError(ValueError):
    pass


def stable_weighted_sum(pairs: Iterable[Tuple[float, float]]) -> float:
    """Return the correctly rounded exact dot product of finite binary floats.

    Multiplying each pair as a float before summation can erase a real residual:
    close, very large endpoints may round to identical products, while tiny
    products can underflow to zero.  Every Python float is an exact dyadic
    rational, so a bounded integer superaccumulator preserves the products and
    performs only one final conversion back to binary64.
    """

    rows = [(float(weight), float(value)) for weight, value in pairs]
    if not rows:
        return 0.0
    if any(
        not math.isfinite(weight) or not math.isfinite(value)
        for weight, value in rows
    ):
        raise NumericCalculationError("weighted-sum inputs must be finite")

    numerator = 0
    denominator_exponent = 0
    components: dict[float, tuple[int, int]] = {}
    for weight, value in rows:
        weight_numerator, weight_exponent = _dyadic_components(weight, components)
        value_numerator, value_exponent = _dyadic_components(value, components)
        term_numerator = weight_numerator * value_numerator
        if term_numerator == 0:
            continue
        term_exponent = weight_exponent + value_exponent
        if term_exponent > denominator_exponent:
            numerator <<= term_exponent - denominator_exponent
            denominator_exponent = term_exponent
        else:
            term_numerator <<= denominator_exponent - term_exponent
        numerator += term_numerator
    try:
        result = float(Fraction(numerator, 1 << denominator_exponent))
    except (OverflowError, ValueError) as exc:
        raise NumericCalculationError("weighted sum is not representable") from exc
    if not math.isfinite(result):
        raise NumericCalculationError("weighted sum is not representable")
    return result


def stable_mean(values: Iterable[float]) -> float:
    """Return the correctly rounded arithmetic mean of finite binary floats."""

    rows = [float(value) for value in values]
    if not rows:
        raise NumericCalculationError("mean requires at least one value")
    if any(not math.isfinite(value) for value in rows):
        raise NumericCalculationError("mean inputs must be finite")
    # Converting a correctly rounded sum and then dividing can double-round the
    # mean.  Accumulate the exact dyadic sum, divide exactly by N, and convert
    # only once.
    numerator = 0
    denominator_exponent = 0
    components: dict[float, tuple[int, int]] = {}
    for value in rows:
        value_numerator, value_exponent = _dyadic_components(value, components)
        if value_numerator == 0:
            continue
        if value_exponent > denominator_exponent:
            numerator <<= value_exponent - denominator_exponent
            denominator_exponent = value_exponent
        else:
            value_numerator <<= denominator_exponent - value_exponent
        numerator += value_numerator
    try:
        result = float(
            Fraction(numerator, len(rows) * (1 << denominator_exponent))
        )
    except (OverflowError, ValueError) as exc:
        raise NumericCalculationError("mean is not representable") from exc
    if not math.isfinite(result):
        raise NumericCalculationError("mean is not representable")
    return result


def stable_weighted_mean(pairs: Iterable[Tuple[float, float]]) -> float:
    """Return ``sum(weight * value) / sum(weight)`` with one final rounding."""

    rows = [(float(weight), float(value)) for weight, value in pairs]
    if not rows:
        raise NumericCalculationError("weighted mean requires at least one value")
    if any(
        not math.isfinite(weight)
        or weight < 0.0
        or not math.isfinite(value)
        for weight, value in rows
    ):
        raise NumericCalculationError(
            "weighted-mean inputs must be finite with nonnegative weights"
        )

    product_numerator = 0
    product_exponent = 0
    weight_numerator = 0
    weight_exponent = 0
    components: dict[float, tuple[int, int]] = {}
    for weight, value in rows:
        weight_component, current_weight_exponent = _dyadic_components(
            weight, components
        )
        value_component, current_value_exponent = _dyadic_components(
            value, components
        )
        if current_weight_exponent > weight_exponent:
            weight_numerator <<= current_weight_exponent - weight_exponent
            weight_exponent = current_weight_exponent
        else:
            weight_component <<= weight_exponent - current_weight_exponent
        weight_numerator += weight_component

        term_numerator = weight_component * value_component
        # ``weight_component`` was aligned above.  Its effective exponent is
        # now ``weight_exponent``.
        term_exponent = weight_exponent + current_value_exponent
        if term_numerator == 0:
            continue
        if term_exponent > product_exponent:
            product_numerator <<= term_exponent - product_exponent
            product_exponent = term_exponent
        else:
            term_numerator <<= product_exponent - term_exponent
        product_numerator += term_numerator

    if weight_numerator <= 0:
        raise NumericCalculationError("weighted mean requires positive total weight")
    try:
        result = float(
            Fraction(
                product_numerator << weight_exponent,
                weight_numerator << product_exponent,
            )
        )
    except (OverflowError, ValueError) as exc:
        raise NumericCalculationError("weighted mean is not representable") from exc
    if not math.isfinite(result):
        raise NumericCalculationError("weighted mean is not representable")
    return result


def _dyadic_components(
    value: float,
    cache: dict[float, tuple[int, int]],
) -> tuple[int, int]:
    cached = cache.get(value)
    if cached is not None:
        return cached
    numerator, denominator = value.as_integer_ratio()
    components = (numerator, denominator.bit_length() - 1)
    # Repeated probabilities and discrete payoffs are common.  Bound the cache
    # so continuous Monte Carlo samples cannot grow a second unbounded copy.
    if len(cache) < 4_096:
        cache[value] = components
    return components
