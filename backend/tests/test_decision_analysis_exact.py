import math

import pytest

from app.decision_analysis import evaluate_decision_model
from app.decision_analysis.expected_utility import ExpectedUtilityError, evaluate_exact
from app.decision_analysis.regret import (
    RegretCalculationError,
    expected_regret_from_records,
    expected_regret_from_trace,
)
from app.decision_analysis.schemas import InformationCost
from app.decision_analysis.schemas import (
    Action,
    AffinePayoff,
    BernoulliDistribution,
    BernoulliParameters,
    CategoricalDistribution,
    CategoricalParameters,
    DecisionModel,
    FixedDistribution,
    FixedParameters,
    Outcome,
    UncertainVariable,
    UtilityModel,
)
from app.decision_analysis.thresholds import binary_switching_thresholds
from app.decision_analysis.validation import calculate_model_hash
from app.decision_analysis.numeric import stable_weighted_sum
from decision_analysis_fixtures import (
    approval_metadata,
    binary_decision_model,
    continuous_decision_model,
    rare_event_decision_model,
)


def _categorical_payoff_model(
    probabilities: dict[str, float],
    payoffs: dict[str, dict[str, float]],
) -> DecisionModel:
    approval = approval_metadata()
    return DecisionModel(
        id="numerical_cancellation",
        version="1.0.0",
        question="Which action has the greater expected utility?",
        consequence_unit="utility_points",
        actions=[
            Action(id=action_id, label=action_id.title(), status="approved", **approval)
            for action_id in payoffs
        ],
        uncertain_variables=[
            UncertainVariable(
                id="state",
                label="State",
                unit="category",
                distribution=CategoricalDistribution(
                    parameters=CategoricalParameters(probabilities=probabilities),
                    source="approved numerical fixture",
                    approval_status="approved",
                    **approval,
                ),
                approval_status="approved",
                **approval,
            )
        ],
        utility_model=UtilityModel(
            type="utility_points",
            unit="utility_points",
            version="1.0.0",
            outcomes=[
                Outcome(
                    action_id=action_id,
                    state={"state": state},
                    consequence=consequence,
                    consequence_unit="utility_points",
                )
                for action_id, state_payoffs in payoffs.items()
                for state, consequence in state_payoffs.items()
            ],
            approval_status="approved",
            **approval,
        ),
        approval_status="approved",
        **approval,
    )


def test_exact_expected_utility_and_trace_match_hand_calculation():
    model = binary_decision_model()
    result = evaluate_exact(model)

    assert result.expected_utility_by_action == pytest.approx({"safe": 40.0, "risky": 30.0})
    assert result.recommended_action == "safe"
    assert result.runner_up == "risky"
    assert result.recommendation_margin == pytest.approx(10.0)
    assert len(result.trace_rows) == 4
    assert sum(row.probability for row in result.trace_rows) == pytest.approx(1.0)


def test_expected_regret_matches_hand_calculation():
    exact = evaluate_exact(binary_decision_model())
    regret = expected_regret_from_trace(exact.trace_rows)

    assert regret == pytest.approx({"safe": 18.0, "risky": 28.0})


def test_binary_switching_threshold_identifies_the_global_action_change():
    thresholds = binary_switching_thresholds(binary_decision_model())
    demand = next(item for item in thresholds if item.variable_id == "demand")

    # Support is canonicalized as high, low, so this is P(low)=0.6.  Equivalently
    # the risky/safe switch occurs at P(high)=0.4.
    assert demand.upper_state == "low"
    assert demand.probability_of_upper_state == pytest.approx(0.6)
    assert demand.action_below == "risky"
    assert demand.action_above == "safe"
    assert not any(item.variable_id == "regulatory" for item in thresholds)


def test_threshold_trace_normalizes_subnormal_conditional_mass_before_rounding():
    approval = approval_metadata()
    minimum = float.fromhex("0x0.0000000000001p-1022")
    model = DecisionModel(
        id="subnormal_threshold",
        version="1.0.0",
        question="Which action wins as event probability changes?",
        consequence_unit="utility_points",
        actions=[
            Action(id="a", label="A", status="approved", **approval),
            Action(id="b", label="B", status="approved", **approval),
        ],
        uncertain_variables=[
            UncertainVariable(
                id="event",
                label="Event",
                unit="boolean",
                distribution=BernoulliDistribution(
                    parameters=BernoulliParameters(probability_true=minimum),
                    source="approved subnormal fixture",
                    approval_status="approved",
                    **approval,
                ),
                approval_status="approved",
                **approval,
            )
        ],
        utility_model=UtilityModel(
            type="utility_points",
            unit="utility_points",
            version="1.0.0",
            outcomes=[
                Outcome(
                    action_id="a",
                    state={"event": False},
                    consequence=0.0,
                    consequence_unit="utility_points",
                ),
                Outcome(
                    action_id="a",
                    state={"event": True},
                    consequence=0.5,
                    consequence_unit="utility_points",
                ),
                Outcome(
                    action_id="b",
                    state={"event": False},
                    consequence=0.25,
                    consequence_unit="utility_points",
                ),
                Outcome(
                    action_id="b",
                    state={"event": True},
                    consequence=0.25,
                    consequence_unit="utility_points",
                ),
            ],
            approval_status="approved",
            **approval,
        ),
        approval_status="approved",
        **approval,
    )
    exact = evaluate_exact(model)

    thresholds = binary_switching_thresholds(model, trace_rows=exact.trace_rows)

    assert len(thresholds) == 1
    assert thresholds[0].probability_of_upper_state == pytest.approx(0.5)


def test_evpi_evppi_and_net_information_value_match_hand_calculation():
    result = evaluate_decision_model(
        binary_decision_model(),
        information_costs={
            "demand": InformationCost(cash_cost=5.0),
            "all_uncertainty": InformationCost(validation_cost=2.0),
        },
        evppi_groups={"all_uncertainty": ["demand", "regulatory"]},
    )

    assert result.status == "calculated"
    assert result.method == "exact_enumeration"
    assert result.recommended_action == "safe"
    assert result.expected_utility_by_action == pytest.approx({"safe": 40.0, "risky": 30.0})
    assert result.expected_regret_by_action == pytest.approx({"safe": 18.0, "risky": 28.0})
    assert result.evpi == pytest.approx(18.0)
    assert result.evppi_by_variable == pytest.approx({"demand": 18.0, "regulatory": 0.0})
    assert result.evppi_by_group == pytest.approx({"all_uncertainty": 18.0})
    assert result.information_costs["demand"].total_cost == pytest.approx(5.0)
    assert result.net_information_value_by_variable == pytest.approx(
        {"demand": 13.0, "regulatory": 0.0}
    )
    assert result.net_information_value_by_group == pytest.approx({"all_uncertainty": 16.0})
    assert result.evpi >= 0.0
    assert all(value <= result.evpi + 1e-9 for value in result.evppi_by_variable.values())
    assert result.trace.enumerated_state_count == 4
    assert result.trace.sample_count == 0
    assert result.model_hash == calculate_model_hash(binary_decision_model())


def test_information_value_is_zero_when_one_action_wins_in_every_state():
    model = binary_decision_model()
    for outcome in model.utility_model.outcomes:
        if outcome.action_id == "risky":
            outcome.consequence = 30.0

    result = evaluate_decision_model(model)

    assert result.status == "calculated"
    assert result.recommended_action == "safe"
    assert result.evpi == pytest.approx(0.0)
    assert result.evppi_by_variable == pytest.approx({"demand": 0.0, "regulatory": 0.0})
    assert result.switching_thresholds == []


def test_information_cost_total_must_equal_components_when_supplied():
    with pytest.raises(ValueError, match="must equal"):
        InformationCost(cash_cost=2.0, delay_cost=3.0, total_cost=99.0)
    with pytest.raises(ValueError, match="finite"):
        InformationCost(cash_cost=1e308, delay_cost=1e308)


def test_regret_rejects_every_nonfinite_action_utility():
    with pytest.raises(RegretCalculationError, match="finite"):
        expected_regret_from_records(
            [(1.0, {"safe": 10.0, "risky": float("nan")})]
        )


def test_regret_uses_stable_summation_and_rejects_action_set_changes():
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    regret = expected_regret_from_records(
        [(1.0 / 11.0, {"a": maximum, "b": 0.0}) for _ in range(11)]
    )
    assert regret["a"] == 0.0
    assert regret["b"] == pytest.approx(maximum)

    with pytest.raises(RegretCalculationError, match="same action"):
        expected_regret_from_records(
            [(0.5, {"a": 1.0, "b": 0.0}), (0.5, {"a": 1.0})]
        )


def test_weighted_regret_can_be_finite_when_raw_state_difference_overflows():
    regret = expected_regret_from_records(
        [
            (0.01, {"a": 1e308, "b": -1e308}),
            (0.99, {"a": 0.0, "b": 0.0}),
        ]
    )

    assert regret["a"] == 0.0
    assert regret["b"] == pytest.approx(2e306)

    nearby = math.nextafter(1e308, 0.0)
    close_regret = expected_regret_from_records(
        [
            (1e-258, {"a": 1e308, "b": nearby}),
            (1.0, {"a": 0.0, "b": 0.0}),
        ]
    )
    assert close_regret["b"] == pytest.approx((1e308 - nearby) * 1e-258)


def test_exact_engine_fails_closed_when_positive_joint_mass_underflows():
    with pytest.raises(ExpectedUtilityError, match="probability underflowed"):
        evaluate_exact(rare_event_decision_model())


def test_exact_engine_fails_closed_when_joint_mass_is_subnormal():
    model = rare_event_decision_model()
    for variable in model.uncertain_variables:
        variable.distribution.parameters.probability_true = 2e-162

    with pytest.raises(ExpectedUtilityError, match="probability is subnormal"):
        evaluate_exact(model)


def test_exact_dot_preserves_min_subnormal_expected_utility_and_recommendation():
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    minimum = float.fromhex("0x0.0000000000001p-1022")
    model = _categorical_payoff_model(
        {"negative": 0.2, "positive": 0.2, "residual": 0.6},
        {
            "baseline": {"negative": 0.0, "positive": 0.0, "residual": 0.0},
            "residual": {
                "negative": -maximum,
                "positive": maximum,
                "residual": minimum,
            },
        },
    )

    result = evaluate_decision_model(model)

    assert result.expected_utility_by_action["baseline"] == 0.0
    assert result.expected_utility_by_action["residual"] == minimum
    assert result.recommended_action == "residual"


def test_exact_dot_preserves_close_endpoint_residual_before_weighting():
    nearby = math.nextafter(1e308, 0.0)
    model = _categorical_payoff_model(
        {"negative": 1e-258, "positive": 1e-258, "zero": 1.0},
        {
            "baseline": {
                "negative": 1e34,
                "positive": 1e34,
                "zero": 1e34,
            },
            "signal": {
                "negative": -nearby,
                "positive": 1e308,
                "zero": 0.0,
            },
        },
    )

    result = evaluate_decision_model(model)

    assert result.expected_utility_by_action["signal"] == pytest.approx(
        (1e308 - nearby) * 1e-258
    )
    assert result.expected_utility_by_action["signal"] > result.expected_utility_by_action[
        "baseline"
    ]
    assert result.recommended_action == "signal"


def test_stable_weighted_sum_matches_exact_float_dot_after_extreme_cancellation():
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    minimum = float.fromhex("0x0.0000000000001p-1022")
    weight = 1.0 / 300.0
    pairs = [
        *[(weight, maximum) for _ in range(50)],
        *[(weight, -maximum) for _ in range(50)],
        *[(weight, minimum) for _ in range(200)],
    ]

    assert stable_weighted_sum(pairs) == minimum


def test_nearby_real_switching_thresholds_are_not_merged():
    approval = approval_metadata()
    model = DecisionModel(
        id="close_thresholds",
        version="1.0.0",
        question="Which action maximizes utility?",
        consequence_unit="utility_points",
        actions=[
            Action(id="a", label="A", status="approved", **approval),
            Action(id="b", label="B", status="approved", **approval),
            Action(id="c", label="C", status="approved", **approval),
        ],
        uncertain_variables=[
            UncertainVariable(
                id="x",
                label="Binary state",
                unit="boolean",
                distribution=BernoulliDistribution(
                    parameters=BernoulliParameters(probability_true=0.5),
                    source="approved fixture",
                    approval_status="approved",
                    **approval,
                ),
                approval_status="approved",
                **approval,
            )
        ],
        utility_model=UtilityModel(
            type="utility_points",
            unit="utility_points",
            version="1.0.0",
            affine_payoffs=[
                AffinePayoff(
                    action_id="a",
                    intercept=0.0,
                    consequence_unit="utility_points",
                ),
                AffinePayoff(
                    action_id="b",
                    intercept=-0.5,
                    coefficients={"x": 1.0},
                    consequence_unit="utility_points",
                ),
                AffinePayoff(
                    action_id="c",
                    intercept=-1.00000000005,
                    coefficients={"x": 2.0},
                    consequence_unit="utility_points",
                ),
            ],
            approval_status="approved",
            **approval,
        ),
        approval_status="approved",
        **approval,
    )

    thresholds = binary_switching_thresholds(model)

    assert [(item.action_below, item.action_above) for item in thresholds] == [
        ("a", "b"),
        ("b", "c"),
    ]
    assert [item.probability_of_upper_state for item in thresholds] == pytest.approx(
        [0.5, 0.50000000005],
        abs=1e-14,
    )


def test_affine_coefficient_order_cannot_change_hash_or_recommendation():
    approval = approval_metadata()
    model = continuous_decision_model()
    model.uncertain_variables = [
        UncertainVariable(
            id=variable_id,
            label=variable_id.upper(),
            unit="number",
            distribution=FixedDistribution(
                parameters=FixedParameters(value=1.0),
                source="approved fixture",
                approval_status="approved",
                **approval,
            ),
            approval_status="approved",
            **approval,
        )
        for variable_id in ("x", "y", "z")
    ]
    positive = next(
        item for item in model.utility_model.affine_payoffs if item.action_id == "positive"
    )
    negative = next(
        item for item in model.utility_model.affine_payoffs if item.action_id == "negative"
    )
    positive.coefficients = {"x": 1e16, "y": -1e16, "z": 1.0}
    negative.intercept = 0.5
    negative.coefficients = {}
    reordered = model.model_copy(deep=True)
    next(
        item
        for item in reordered.utility_model.affine_payoffs
        if item.action_id == "positive"
    ).coefficients = {"z": 1.0, "x": 1e16, "y": -1e16}

    first = evaluate_decision_model(model)
    second = evaluate_decision_model(reordered)

    assert first.model_hash == second.model_hash
    assert first.expected_utility_by_action == second.expected_utility_by_action
    assert first.recommended_action == second.recommended_action == "positive"


def test_threshold_math_scales_max_float_endpoint_utilities():
    approval = approval_metadata()
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    outcomes = [
        Outcome(
            action_id="a",
            state={"x": False},
            consequence=-maximum,
            consequence_unit="utility_points",
        ),
        Outcome(
            action_id="a",
            state={"x": True},
            consequence=maximum,
            consequence_unit="utility_points",
        ),
        Outcome(
            action_id="b",
            state={"x": False},
            consequence=maximum,
            consequence_unit="utility_points",
        ),
        Outcome(
            action_id="b",
            state={"x": True},
            consequence=-maximum,
            consequence_unit="utility_points",
        ),
    ]
    model = DecisionModel(
        id="maximum_threshold",
        version="1.0.0",
        question="Which extreme action?",
        consequence_unit="utility_points",
        actions=[
            Action(id="a", label="A", status="approved", **approval),
            Action(id="b", label="B", status="approved", **approval),
        ],
        uncertain_variables=[
            UncertainVariable(
                id="x",
                label="X",
                unit="boolean",
                distribution=BernoulliDistribution(
                    parameters=BernoulliParameters(probability_true=0.5),
                    source="approved fixture",
                    approval_status="approved",
                    **approval,
                ),
                approval_status="approved",
                **approval,
            )
        ],
        utility_model=UtilityModel(
            type="utility_points",
            unit="utility_points",
            version="1.0.0",
            outcomes=outcomes,
            approval_status="approved",
            **approval,
        ),
        approval_status="approved",
        **approval,
    )

    thresholds = binary_switching_thresholds(model)

    assert len(thresholds) == 1
    assert thresholds[0].probability_of_upper_state == pytest.approx(0.5)
