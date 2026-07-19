import math

import pytest

from app.decision_analysis import evaluate_decision_model
from app.decision_analysis.monte_carlo import (
    MAX_SAMPLE_COUNT,
    MonteCarloLimitError,
    _scaled_mean_and_standard_error,
    evaluate_monte_carlo,
)
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
from app.decision_analysis.voi import WeightedUtilityRecord, calculate_value_of_information
from decision_analysis_fixtures import approval_metadata
from decision_analysis_fixtures import (
    binary_decision_model,
    continuous_decision_model,
    rare_event_decision_model,
)


def test_seeded_monte_carlo_is_reproducible():
    model = continuous_decision_model()
    first = evaluate_decision_model(model, seed=8821, sample_count=4_000)
    second = evaluate_decision_model(model, seed=8821, sample_count=4_000)

    assert first.status == second.status == "calculated"
    assert first.method == second.method == "monte_carlo"
    assert first.expected_utility_by_action == second.expected_utility_by_action
    assert first.expected_regret_by_action == second.expected_regret_by_action
    assert first.evpi == second.evpi
    assert first.evppi_by_variable == second.evppi_by_variable
    assert first.trace.sample_digest == second.trace.sample_digest
    assert first.trace.sample_preview == second.trace.sample_preview
    assert first.seed == second.seed == 8821
    assert first.sample_count == second.sample_count == 4_000


def test_different_seed_changes_the_sample_trace():
    model = continuous_decision_model()
    first = evaluate_decision_model(model, seed=11, sample_count=1_000)
    second = evaluate_decision_model(model, seed=12, sample_count=1_000)

    assert first.trace.sample_digest != second.trace.sample_digest


def test_reordering_variables_and_actions_preserves_seeded_result():
    model = binary_decision_model()
    reordered = model.model_copy(deep=True)
    reordered.actions.reverse()
    reordered.uncertain_variables.reverse()
    reordered.utility_model.outcomes.reverse()

    first = evaluate_decision_model(
        model,
        seed=77,
        sample_count=2_000,
        force_method="monte_carlo",
    )
    second = evaluate_decision_model(
        reordered,
        seed=77,
        sample_count=2_000,
        force_method="monte_carlo",
    )

    assert first.model_hash == second.model_hash
    assert first.expected_utility_by_action == second.expected_utility_by_action
    assert first.expected_regret_by_action == second.expected_regret_by_action
    assert first.trace.sample_digest == second.trace.sample_digest


def test_sampled_evpi_evppi_and_convergence_invariants_hold():
    result = evaluate_decision_model(
        continuous_decision_model(),
        seed=97,
        sample_count=8_000,
    )

    assert result.evpi > 0.0
    assert 0.0 <= result.evppi_by_variable["market_move"] <= result.evpi + 1e-9
    assert result.convergence.batch_count == 16
    assert result.convergence.max_standard_error > 0.0
    assert result.convergence.standard_error_by_action.keys() == {
        "positive",
        "negative",
    }
    assert any("20-bin approximation" in warning for warning in result.warnings)


def test_forced_monte_carlo_on_discrete_fixture_approaches_exact_values():
    result = evaluate_decision_model(
        binary_decision_model(),
        seed=404,
        sample_count=20_000,
        force_method="monte_carlo",
    )

    assert result.method == "monte_carlo"
    assert result.expected_utility_by_action["safe"] == pytest.approx(40.0)
    assert result.expected_utility_by_action["risky"] == pytest.approx(30.0, abs=1.5)
    assert result.evpi == pytest.approx(18.0, abs=1.5)
    assert result.evppi_by_variable["regulatory"] <= result.evpi + 1e-9


@pytest.mark.parametrize("sample_count", [99, MAX_SAMPLE_COUNT + 1])
def test_monte_carlo_enforces_sample_limits(sample_count):
    with pytest.raises(MonteCarloLimitError, match="sample_count"):
        evaluate_monte_carlo(
            continuous_decision_model(),
            seed=1,
            sample_count=sample_count,
        )


def test_monte_carlo_rejects_probability_below_rng_resolution():
    with pytest.raises(MonteCarloLimitError, match="RNG resolution"):
        evaluate_monte_carlo(
            rare_event_decision_model(),
            seed=1,
            sample_count=100,
        )


@pytest.mark.parametrize("runtime_limit", [True, "1", float("nan"), 0.0, 11.0])
def test_monte_carlo_runtime_limit_uses_a_strict_bounded_number(runtime_limit):
    with pytest.raises(MonteCarloLimitError, match="runtime_limit_seconds"):
        evaluate_monte_carlo(
            continuous_decision_model(),
            seed=1,
            sample_count=100,
            runtime_limit_seconds=runtime_limit,
        )


@pytest.mark.parametrize("bin_count", [True, 2.5, "20", 1])
def test_evppi_continuous_bin_count_is_a_strict_bounded_integer(bin_count):
    with pytest.raises(ValueError, match="continuous_bins"):
        calculate_value_of_information(
            [
                WeightedUtilityRecord(
                    state={"x": 1.0},
                    utilities={"a": 1.0, "b": 0.0},
                    weight=1.0,
                )
            ],
            ["x"],
            continuous_variable_ids=["x"],
            continuous_bins=bin_count,
        )


def test_large_finite_state_space_falls_back_to_monte_carlo():
    model = continuous_decision_model()
    approval = approval_metadata()
    model.uncertain_variables = [
        UncertainVariable(
            id=f"binary_{index}",
            label=f"Binary {index}",
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
        for index in range(17)
    ]
    model.utility_model.affine_payoffs[0].coefficients = {"binary_0": 1.0}
    model.utility_model.affine_payoffs[1].coefficients = {"binary_0": -1.0}

    result = evaluate_decision_model(model, seed=3, sample_count=100)

    assert result.method == "monte_carlo"
    assert result.sample_count == 100


def test_equal_continuous_values_are_never_split_across_evppi_bins():
    result = calculate_value_of_information(
        [
            WeightedUtilityRecord(
                state={"x": 1.0},
                utilities={"a": 100.0, "b": 0.0},
                weight=0.5,
            ),
            WeightedUtilityRecord(
                state={"x": 1.0},
                utilities={"a": 0.0, "b": 100.0},
                weight=0.5,
            ),
        ],
        ["x"],
        continuous_variable_ids=["x"],
        continuous_bins=2,
    )

    assert result.evpi == pytest.approx(50.0)
    assert result.evppi_by_variable["x"] == pytest.approx(0.0)


def test_scaled_monte_carlo_summary_handles_opposite_max_float_utilities():
    model = binary_decision_model()
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    for outcome in model.utility_model.outcomes:
        if outcome.action_id == "safe":
            outcome.consequence = maximum if outcome.state["demand"] == "high" else -maximum
        else:
            outcome.consequence = 0.0

    result = evaluate_monte_carlo(model, seed=2, sample_count=100)

    assert all(math.isfinite(value) for value in result.expected_utility_by_action.values())
    assert all(math.isfinite(value) for value in result.expected_regret_by_action.values())
    assert math.isfinite(result.convergence.max_standard_error)
    assert result.convergence.max_standard_error > 0.0


def test_monte_carlo_mean_retains_tiny_residual_after_huge_cancellation():
    approval = approval_metadata()
    model = DecisionModel(
        id="cancellation_fixture",
        version="1.0.0",
        question="Which action has the larger sampled mean?",
        consequence_unit="utility_points",
        actions=[
            Action(id="a", label="A", status="approved", **approval),
            Action(id="b", label="B", status="approved", **approval),
        ],
        uncertain_variables=[
            UncertainVariable(
                id="state",
                label="State",
                unit="category",
                distribution=CategoricalDistribution(
                    parameters=CategoricalParameters(
                        probabilities={
                            "negative": 0.49,
                            "positive": 0.49,
                            "residual": 0.02,
                        }
                    ),
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
            outcomes=[
                Outcome(
                    action_id=action_id,
                    state={"state": state},
                    consequence=utility,
                    consequence_unit="utility_points",
                )
                for action_id, values in {
                    "a": {
                        "negative": -1e308,
                        "positive": 1e308,
                        "residual": 1e-100,
                    },
                    "b": {
                        "negative": 1e-102,
                        "positive": 1e-102,
                        "residual": 1e-102,
                    },
                }.items()
                for state, utility in values.items()
            ],
            approval_status="approved",
            **approval,
        ),
        approval_status="approved",
        **approval,
    )

    result = evaluate_monte_carlo(model, seed=6, sample_count=100)

    assert [record.state["state"] for record in result.records].count("negative") == 49
    assert [record.state["state"] for record in result.records].count("positive") == 49
    assert [record.state["state"] for record in result.records].count("residual") == 2
    assert result.expected_utility_by_action["a"] == pytest.approx(2e-102)
    assert result.expected_utility_by_action["b"] == pytest.approx(1e-102)
    assert result.recommended_action == "a"


def test_monte_carlo_mean_preserves_identical_min_subnormal_values():
    model = continuous_decision_model()
    model.uncertain_variables[0].distribution = FixedDistribution(
        parameters=FixedParameters(value=5e-324),
        source="approved subnormal fixture",
        approval_status="approved",
        **approval_metadata(),
    )

    result = evaluate_monte_carlo(model, seed=1, sample_count=100)

    assert result.expected_utility_by_action["positive"] == 5e-324
    assert result.expected_utility_by_action["negative"] == -5e-324


def test_monte_carlo_mean_preserves_min_subnormal_after_extreme_cancellation():
    minimum = float.fromhex("0x0.0000000000001p-1022")
    values = [1e308] * 50 + [-1e308] * 50 + [minimum] * 200

    mean, standard_error = _scaled_mean_and_standard_error(values)

    assert mean == minimum
    assert math.isfinite(standard_error)


def test_monte_carlo_mean_uses_one_correctly_rounded_conversion():
    values = [
        3.3184620407069e-227,
        0.0,
        -7.089487951279647e-23,
        1.7403935301870366e-14,
        -5e-324,
        -8.967913094454701e301,
        3.452371450843763e48,
        -1.1439269028956148e22,
        1.4956027595414791e305,
        -8.782870863462722e-102,
        3.736271768516052e145,
        -1.558307167721134e-294,
        1.0341455717904351e195,
        -8.267192223867707e-307,
    ]

    mean, _standard_error = _scaled_mean_and_standard_error(values)

    assert mean == 1.0676471201657383e304


def test_monte_carlo_combined_work_limit_prevents_large_allocation():
    model = continuous_decision_model()
    approval = approval_metadata()
    model.actions = [
        Action(id=f"action_{index}", label=f"Action {index}", status="approved", **approval)
        for index in range(64)
    ]
    model.utility_model.affine_payoffs = [
        AffinePayoff(
            action_id=f"action_{index}",
            intercept=float(index),
            consequence_unit="utility_points",
        )
        for index in range(64)
    ]

    with pytest.raises(MonteCarloLimitError, match="work limit"):
        evaluate_monte_carlo(model, seed=1, sample_count=100_000)


def test_exact_auto_selection_respects_combined_work_limit():
    model = continuous_decision_model()
    approval = approval_metadata()
    model.actions = [
        Action(id=f"action_{index}", label=f"Action {index}", status="approved", **approval)
        for index in range(64)
    ]
    model.uncertain_variables = [
        UncertainVariable(
            id=f"binary_{index}",
            label=f"Binary {index}",
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
        for index in range(14)
    ]
    model.utility_model.affine_payoffs = [
        AffinePayoff(
            action_id=f"action_{index}",
            intercept=float(index),
            consequence_unit="utility_points",
        )
        for index in range(64)
    ]

    result = evaluate_decision_model(model, seed=1, sample_count=100)

    assert result.method == "monte_carlo"
    assert result.sample_count == 100
