import math
import random

import pytest
from pydantic import TypeAdapter, ValidationError

from app.decision_analysis import DecisionAnalysisInputError, evaluate_decision_model
from app.decision_analysis.distributions import (
    DistributionValidationError,
    finite_support,
    sample_distribution,
)
from app.decision_analysis.schemas import (
    AffinePayoff,
    BetaDistribution,
    BetaParameters,
    BernoulliDistribution,
    BernoulliParameters,
    CategoricalDistribution,
    CategoricalParameters,
    DiscreteDistribution,
    DiscreteParameters,
    DiscretePoint,
    DecisionModel,
    Distribution,
    EvidenceObservation,
    FixedDistribution,
    FixedParameters,
    InformationCost,
    NormalDistribution,
    NormalParameters,
    TriangularDistribution,
    TriangularParameters,
    UniformDistribution,
    UniformParameters,
)
from app.decision_analysis.validation import (
    DecisionModelValidationError,
    calculate_model_hash,
    validate_decision_model,
)
from decision_analysis_fixtures import approval_metadata, binary_decision_model


def _metadata():
    return {
        "source": "approved fixture",
        "approval_status": "approved",
        **approval_metadata(),
    }


@pytest.mark.parametrize(
    ("distribution", "predicate"),
    [
        (
            CategoricalDistribution(
                parameters=CategoricalParameters(probabilities={"a": 0.4, "b": 0.6}),
                **_metadata(),
            ),
            lambda value: value in {"a", "b"},
        ),
        (
            DiscreteDistribution(
                parameters=DiscreteParameters(
                    points=[
                        DiscretePoint(value=1, probability=0.25),
                        DiscretePoint(value=3, probability=0.75),
                    ]
                ),
                **_metadata(),
            ),
            lambda value: value in {1, 3},
        ),
        (
            BernoulliDistribution(
                parameters=BernoulliParameters(probability_true=0.3),
                **_metadata(),
            ),
            lambda value: isinstance(value, bool),
        ),
        (
            BetaDistribution(
                parameters=BetaParameters(alpha=2.0, beta=3.0),
                **_metadata(),
            ),
            lambda value: 0.0 <= value <= 1.0,
        ),
        (
            NormalDistribution(
                parameters=NormalParameters(
                    mean=0.0,
                    standard_deviation=1.0,
                    lower_bound=-1.0,
                    upper_bound=1.0,
                ),
                **_metadata(),
            ),
            lambda value: -1.0 <= value <= 1.0,
        ),
        (
            TriangularDistribution(
                parameters=TriangularParameters(minimum=1.0, mode=2.0, maximum=4.0),
                **_metadata(),
            ),
            lambda value: 1.0 <= value <= 4.0,
        ),
        (
            UniformDistribution(
                parameters=UniformParameters(minimum=5.0, maximum=8.0),
                **_metadata(),
            ),
            lambda value: 5.0 <= value <= 8.0,
        ),
        (
            FixedDistribution(
                parameters=FixedParameters(value=7.0),
                **_metadata(),
            ),
            lambda value: value == 7.0,
        ),
    ],
)
def test_every_supported_distribution_samples_inside_its_support(distribution, predicate):
    rng = random.Random(1234)
    assert all(predicate(sample_distribution(distribution, rng)) for _ in range(200))


def test_probability_rounding_is_normalized_but_material_error_is_rejected():
    rounded = CategoricalDistribution(
        parameters=CategoricalParameters(
            probabilities={"a": 0.3333333, "b": 0.3333333, "c": 0.3333333}
        ),
        **_metadata(),
    )
    support = finite_support(rounded)
    assert math.fsum(probability for _, probability in support) == pytest.approx(1.0)

    invalid = CategoricalDistribution(
        parameters=CategoricalParameters(probabilities={"a": 0.4, "b": 0.4}),
        **_metadata(),
    )
    with pytest.raises(DistributionValidationError, match="sum to 1"):
        finite_support(invalid)


def test_invalid_parameters_and_unknown_distribution_types_fail_closed():
    with pytest.raises(ValidationError):
        BetaParameters(alpha=0.0, beta=1.0)
    with pytest.raises(ValidationError):
        NormalParameters(mean=0.0, standard_deviation=0.0)
    with pytest.raises(ValidationError):
        TriangularParameters(minimum=4.0, mode=2.0, maximum=1.0)
    with pytest.raises(ValidationError):
        UniformParameters(minimum=2.0, maximum=2.0)
    with pytest.raises(ValidationError):
        BetaParameters(alpha=5e-324, beta=1.0)
    with pytest.raises(ValidationError):
        BetaParameters(alpha=0.001, beta=1.0)
    with pytest.raises(ValidationError):
        NormalParameters(mean=0.0, standard_deviation=5e-324)
    with pytest.raises(ValidationError):
        UniformParameters(minimum=-1.7e308, maximum=1.7e308)
    with pytest.raises(ValidationError):
        TriangularParameters(minimum=-1.7e308, mode=0.0, maximum=1.7e308)
    with pytest.raises(ValidationError):
        FixedParameters(value=10**400)
    with pytest.raises(ValidationError):
        TypeAdapter(Distribution).validate_python(
            {
                "type": "llm_confidence",
                "parameters": {"value": 0.8},
                "source": "unsupported",
            }
        )


@pytest.mark.parametrize("bad_probability", [True, "0.5"])
def test_numeric_probability_fields_reject_booleans_and_strings(bad_probability):
    with pytest.raises(ValidationError):
        BernoulliParameters(probability_true=bad_probability)


def test_costs_payoffs_and_sample_counts_use_strict_numeric_types():
    with pytest.raises(ValidationError):
        InformationCost(cash_cost=True)
    with pytest.raises(ValidationError):
        AffinePayoff(
            action_id="a",
            intercept=True,
            consequence_unit="utility_points",
        )
    for bad_sample_size in (True, 1.0, "2"):
        with pytest.raises(ValidationError):
            EvidenceObservation(
                variable_id="x",
                observation_type="beta_counts",
                value={"successes": 1, "failures": 0},
                sample_size=bad_sample_size,
                source_evidence_id="evidence_001",
            )


@pytest.mark.parametrize(
    "options",
    [
        {"information_costs": []},
        {"evppi_groups": []},
        {"evppi_groups": {"joint": None}},
    ],
)
def test_facade_rejects_non_object_or_non_list_option_shapes(options):
    with pytest.raises((DecisionAnalysisInputError, ValueError)):
        evaluate_decision_model(binary_decision_model(), **options)


@pytest.mark.parametrize("invalid_value", [True, "4000"])
def test_facade_revalidates_mutated_model_instances(invalid_value):
    model = binary_decision_model()
    model.utility_model.outcomes[0].consequence = invalid_value

    with pytest.raises(DecisionAnalysisInputError, match="payload is invalid"):
        evaluate_decision_model(model)


def test_facade_revalidates_mutated_information_cost_instances():
    cost = InformationCost(cash_cost=2.0)
    cost.cash_cost = 3.0

    with pytest.raises(DecisionAnalysisInputError, match="cost demand is invalid"):
        evaluate_decision_model(
            binary_decision_model(),
            information_costs={"demand": cost},
        )


def test_model_hash_is_order_independent_and_changes_with_calculation_inputs():
    model = binary_decision_model()
    reordered = model.model_copy(deep=True)
    reordered.actions.reverse()
    reordered.uncertain_variables.reverse()
    reordered.utility_model.outcomes.reverse()
    assert calculate_model_hash(reordered) == calculate_model_hash(model)

    changed = model.model_copy(deep=True)
    demand = next(item for item in changed.uncertain_variables if item.id == "demand")
    demand.distribution.parameters.probabilities = {"low": 0.6, "high": 0.4}
    assert calculate_model_hash(changed) != calculate_model_hash(model)


def test_discrete_point_order_is_canonical_in_model_hash():
    model = binary_decision_model()
    demand = next(item for item in model.uncertain_variables if item.id == "demand")
    demand.distribution = DiscreteDistribution(
        parameters=DiscreteParameters(
            points=[
                DiscretePoint(value="low", probability=0.7),
                DiscretePoint(value="high", probability=0.3),
            ]
        ),
        **_metadata(),
    )
    reordered = model.model_copy(deep=True)
    reordered.uncertain_variables[0].distribution.parameters.points.reverse()

    assert calculate_model_hash(model) == calculate_model_hash(reordered)


def test_fixed_distribution_alias_is_canonical_in_model_hash():
    fixed = binary_decision_model()
    demand = next(item for item in fixed.uncertain_variables if item.id == "demand")
    demand.distribution = FixedDistribution(
        type="fixed",
        parameters=FixedParameters(value="high"),
        **_metadata(),
    )
    deterministic = fixed.model_copy(deep=True)
    next(
        item for item in deterministic.uncertain_variables if item.id == "demand"
    ).distribution.type = "deterministic"

    assert calculate_model_hash(fixed) == calculate_model_hash(deterministic)


def test_dependency_cycles_are_rejected_before_calculation():
    model = binary_decision_model()
    demand = next(item for item in model.uncertain_variables if item.id == "demand")
    regulatory = next(item for item in model.uncertain_variables if item.id == "regulatory")
    demand.dependencies = ["regulatory"]
    regulatory.dependencies = ["demand"]
    with pytest.raises(DecisionModelValidationError, match="dependency cycle"):
        validate_decision_model(model)


def test_unapproved_proposals_return_exact_confirmation_requirements():
    model = binary_decision_model()
    model.actions[1].status = "proposed"
    model.actions[1].approved_by = None
    model.actions[1].approved_at = None
    result = evaluate_decision_model(model)

    assert result.status == "needs_confirmation"
    assert any(
        issue.field == "actions" and issue.item_id == "risky"
        for issue in result.missing_confirmations
    )


def test_distribution_requires_explicit_approval_not_only_actor_metadata():
    model = binary_decision_model()
    demand = next(item for item in model.uncertain_variables if item.id == "demand")
    demand.distribution.approval_status = "proposed"

    result = evaluate_decision_model(model)

    assert result.status == "needs_confirmation"
    assert any(
        issue.field == "distribution" and issue.item_id == "demand"
        for issue in result.missing_confirmations
    )


@pytest.mark.parametrize(
    ("approved_by", "approved_at"),
    [("   ", "2026-07-18T00:00:00+00:00"), ("owner", "not-a-timestamp")],
)
def test_approval_metadata_requires_nonblank_actor_and_parseable_time(
    approved_by,
    approved_at,
):
    model = binary_decision_model()
    model.approved_by = approved_by
    model.approved_at = approved_at

    result = evaluate_decision_model(model)

    assert result.status == "needs_confirmation"
    assert any(issue.field == "model_approval" for issue in result.missing_confirmations)


def test_schema_caps_action_count_before_calculation_allocation():
    payload = binary_decision_model().model_dump(mode="json")
    template = payload["actions"][0]
    payload["actions"] = [
        {**template, "id": f"action_{index}", "label": f"Action {index}"}
        for index in range(65)
    ]

    with pytest.raises(ValidationError):
        DecisionModel.model_validate(payload)
