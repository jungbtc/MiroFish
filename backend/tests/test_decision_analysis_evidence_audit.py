import pytest

from app.decision_analysis import evaluate_decision_model
from app.decision_analysis.audit import build_analysis_audit_record
from app.decision_analysis.evidence_updates import (
    EvidenceUpdateError,
    apply_confirmed_observation,
)
from app.decision_analysis.schemas import (
    BetaDistribution,
    BetaParameters,
    EvidenceObservation,
    NormalDistribution,
    NormalParameters,
    TriangularDistribution,
    TriangularParameters,
    UniformDistribution,
    UniformParameters,
)
from app.decision_analysis.validation import calculate_model_hash
from decision_analysis_fixtures import (
    APPROVED_AT,
    APPROVER,
    approval_metadata,
    binary_decision_model,
    continuous_decision_model,
)


def _observation(**values):
    payload = {
        "variable_id": "demand",
        "observation_type": "categorical_probabilities",
        "value": {"low": 0.5, "high": 0.5},
        "source_evidence_id": "evidence_001",
        "approval_status": "approved",
        "approved_by": APPROVER,
        "approved_at": APPROVED_AT,
    }
    payload.update(values)
    return EvidenceObservation(**payload)


def test_confirmed_categorical_update_returns_new_hashed_model_without_mutation():
    model = binary_decision_model()
    original_hash = calculate_model_hash(model)
    result = apply_confirmed_observation(model, _observation())

    assert result.status == "applied"
    assert model.uncertain_variables[0].distribution.parameters.probabilities == {
        "low": 0.7,
        "high": 0.3,
    }
    demand = next(
        item for item in result.updated_model.uncertain_variables if item.id == "demand"
    )
    assert demand.distribution.parameters.probabilities == {"low": 0.5, "high": 0.5}
    assert demand.evidence_ids == ["evidence_001"]
    assert result.updated_model.model_hash == calculate_model_hash(result.updated_model)
    assert result.updated_model.model_hash != original_hash

    retried = apply_confirmed_observation(result.updated_model, _observation())
    assert retried.status == "not_applied_to_distribution"
    assert "already applied" in retried.reason
    assert retried.updated_model.model_hash == result.updated_model.model_hash


def test_evidence_version_chain_stays_fixed_length_and_reloadable():
    model = binary_decision_model()
    for index in range(8):
        result = apply_confirmed_observation(
            model,
            _observation(source_evidence_id=f"evidence_{index:03d}"),
        )
        assert result.status == "applied"
        model = result.updated_model
        assert len(model.version) == len("evidence-") + 32
        model = type(model).model_validate(model.model_dump(mode="json"))


def test_replace_point_safely_filters_reachable_payoffs_or_remains_unapplied():
    model = binary_decision_model()
    applied = apply_confirmed_observation(
        model,
        _observation(
            observation_type="replace_point",
            value="high",
        ),
    )

    assert applied.status == "applied"
    assert len(applied.updated_model.utility_model.outcomes) == 4
    assert all(
        outcome.state["demand"] == "high"
        for outcome in applied.updated_model.utility_model.outcomes
    )
    assert evaluate_decision_model(applied.updated_model).status == "calculated"

    unapplied = apply_confirmed_observation(
        model,
        _observation(
            source_evidence_id="evidence_unmodeled",
            observation_type="replace_point",
            value="unmodeled_state",
        ),
    )
    assert unapplied.status == "not_applied_to_distribution"
    assert "payoff or utility confirmation" in unapplied.reason
    assert unapplied.updated_model.model_dump() == model.model_dump()


def test_beta_counts_and_normal_observation_use_explicit_statistical_inputs():
    beta_model = continuous_decision_model()
    variable = beta_model.uncertain_variables[0]
    variable.distribution = BetaDistribution(
        parameters=BetaParameters(alpha=2.0, beta=3.0),
        source="approved prior",
        approval_status="approved",
        **approval_metadata(),
    )
    beta_result = apply_confirmed_observation(
        beta_model,
        _observation(
            variable_id="market_move",
            observation_type="beta_counts",
            value={"successes": 4, "failures": 1},
        ),
    )
    beta_parameters = beta_result.updated_model.uncertain_variables[0].distribution.parameters
    assert beta_parameters.alpha == pytest.approx(6.0)
    assert beta_parameters.beta == pytest.approx(4.0)

    normal_model = continuous_decision_model()
    normal_result = apply_confirmed_observation(
        normal_model,
        _observation(
            variable_id="market_move",
            observation_type="normal_observation",
            value={"observation": 1.0, "standard_error": 0.5},
        ),
    )
    normal_parameters = normal_result.updated_model.uncertain_variables[0].distribution.parameters
    assert normal_parameters.mean == pytest.approx(0.86)
    assert normal_parameters.standard_deviation == pytest.approx((1.0 / 5.0) ** 0.5)


def test_beta_counts_must_match_confirmed_sample_size():
    model = continuous_decision_model()
    model.uncertain_variables[0].distribution = BetaDistribution(
        parameters=BetaParameters(alpha=2.0, beta=3.0),
        source="approved prior",
        approval_status="approved",
        **approval_metadata(),
    )
    with pytest.raises(EvidenceUpdateError, match="sample size"):
        apply_confirmed_observation(
            model,
            _observation(
                variable_id="market_move",
                observation_type="beta_counts",
                value={"successes": 4, "failures": 1},
                sample_size=6,
            ),
        )


def test_beta_counts_and_fixed_values_reject_extreme_numeric_inputs_cleanly():
    beta_model = continuous_decision_model()
    beta_model.uncertain_variables[0].distribution = BetaDistribution(
        parameters=BetaParameters(alpha=1_000_000.0, beta=2.0),
        source="approved upper-bound prior",
        approval_status="approved",
        **approval_metadata(),
    )
    with pytest.raises(EvidenceUpdateError, match="beta shape"):
        apply_confirmed_observation(
            beta_model,
            _observation(
                variable_id="market_move",
                observation_type="beta_counts",
                value={"successes": 1, "failures": 0},
                sample_size=1,
            ),
        )

    with pytest.raises(EvidenceUpdateError, match="finite number"):
        apply_confirmed_observation(
            continuous_decision_model(),
            _observation(
                variable_id="market_move",
                observation_type="replace_point",
                value=10**400,
            ),
        )


def test_replace_point_and_supported_uniform_hard_range_are_applied():
    point_result = apply_confirmed_observation(
        continuous_decision_model(),
        _observation(
            variable_id="market_move",
            observation_type="replace_point",
            value=1.25,
        ),
    )
    assert point_result.status == "applied"
    assert point_result.updated_model.uncertain_variables[0].distribution.type == "fixed"
    assert point_result.updated_model.uncertain_variables[0].distribution.parameters.value == 1.25

    ranged_model = continuous_decision_model()
    ranged_model.uncertain_variables[0].distribution = UniformDistribution(
        parameters=UniformParameters(minimum=0.0, maximum=10.0),
        source="approved range",
        approval_status="approved",
        **approval_metadata(),
    )
    range_result = apply_confirmed_observation(
        ranged_model,
        _observation(
            variable_id="market_move",
            observation_type="hard_range",
            value={"lower_bound": 2.0, "upper_bound": 8.0},
        ),
    )
    assert range_result.status == "applied"
    parameters = range_result.updated_model.uncertain_variables[0].distribution.parameters
    assert parameters.minimum == pytest.approx(2.0)
    assert parameters.maximum == pytest.approx(8.0)


def test_unsupported_update_is_preserved_without_changing_distribution():
    model = continuous_decision_model()
    variable = model.uncertain_variables[0]
    variable.distribution = BetaDistribution(
        parameters=BetaParameters(alpha=2.0, beta=2.0),
        source="approved prior",
        approval_status="approved",
        **approval_metadata(),
    )
    result = apply_confirmed_observation(
        model,
        _observation(
            variable_id="market_move",
            observation_type="hard_range",
            value={"lower_bound": 0.2, "upper_bound": 0.8},
        ),
    )

    assert result.status == "not_applied_to_distribution"
    assert result.updated_model.uncertain_variables[0].distribution.type == "beta"


def test_updates_that_need_truncated_likelihoods_fail_closed():
    bounded_normal = continuous_decision_model()
    bounded_normal.uncertain_variables[0].distribution = NormalDistribution(
        parameters=NormalParameters(
            mean=0.0,
            standard_deviation=1.0,
            lower_bound=-2.0,
            upper_bound=2.0,
        ),
        source="approved bounded prior",
        approval_status="approved",
        **approval_metadata(),
    )
    normal_result = apply_confirmed_observation(
        bounded_normal,
        _observation(
            variable_id="market_move",
            observation_type="normal_observation",
            value={"observation": 1.0, "standard_error": 0.5},
        ),
    )
    assert normal_result.status == "not_applied_to_distribution"
    assert "truncated-normal" in normal_result.reason

    triangular = continuous_decision_model()
    triangular.uncertain_variables[0].distribution = TriangularDistribution(
        parameters=TriangularParameters(minimum=0.0, mode=1.0, maximum=3.0),
        source="approved triangular prior",
        approval_status="approved",
        **approval_metadata(),
    )
    range_result = apply_confirmed_observation(
        triangular,
        _observation(
            variable_id="market_move",
            observation_type="hard_range",
            value={"lower_bound": 0.5, "upper_bound": 2.0},
        ),
    )
    assert range_result.status == "not_applied_to_distribution"
    assert range_result.updated_model.uncertain_variables[0].distribution.type == "triangular"


@pytest.mark.parametrize("standard_error", [5e-324, 1e308])
def test_normal_observation_rejects_unrepresentable_scales(standard_error):
    with pytest.raises(EvidenceUpdateError, match="numerical range"):
        apply_confirmed_observation(
            continuous_decision_model(),
            _observation(
                variable_id="market_move",
                observation_type="normal_observation",
                value={"observation": 1.0, "standard_error": standard_error},
            ),
        )


def test_normal_observation_rejects_unrepresentable_posterior_scale():
    model = continuous_decision_model()
    model.uncertain_variables[0].distribution = NormalDistribution(
        parameters=NormalParameters(mean=0.0, standard_deviation=1e-12),
        source="approved numerical-boundary prior",
        approval_status="approved",
        **approval_metadata(),
    )
    with pytest.raises(EvidenceUpdateError, match="posterior"):
        apply_confirmed_observation(
            model,
            _observation(
                variable_id="market_move",
                observation_type="normal_observation",
                value={"observation": 1.0, "standard_error": 1e-12},
            ),
        )


def test_unapproved_evidence_cannot_update_a_distribution():
    observation = _observation(approval_status="proposed", approved_by=None, approved_at=None)
    with pytest.raises(EvidenceUpdateError, match="explicitly approved"):
        apply_confirmed_observation(binary_decision_model(), observation)


def test_evidence_approval_rejects_whitespace_actor_and_invalid_time():
    with pytest.raises(EvidenceUpdateError, match="actor and timestamp"):
        apply_confirmed_observation(
            binary_decision_model(),
            _observation(approved_by="   "),
        )
    with pytest.raises(EvidenceUpdateError, match="actor and timestamp"):
        apply_confirmed_observation(
            binary_decision_model(),
            _observation(approved_at="tomorrow"),
        )


def test_evidence_numeric_values_reject_string_coercion():
    with pytest.raises(EvidenceUpdateError, match="finite number"):
        apply_confirmed_observation(
            binary_decision_model(),
            _observation(value={"low": "0.5", "high": 0.5}),
        )
    with pytest.raises(EvidenceUpdateError, match="finite number"):
        apply_confirmed_observation(
            continuous_decision_model(),
            _observation(
                variable_id="market_move",
                observation_type="normal_observation",
                value={"observation": "1.0", "standard_error": 0.5},
            ),
        )
    with pytest.raises(EvidenceUpdateError, match="finite number"):
        apply_confirmed_observation(
            continuous_decision_model(),
            _observation(
                variable_id="market_move",
                observation_type="hard_range",
                value={"lower_bound": "0.0", "upper_bound": 1.0},
            ),
        )


def test_evidence_boundary_revalidates_mutated_pydantic_instances():
    model = binary_decision_model()
    model.utility_model.outcomes[0].consequence = True
    with pytest.raises(EvidenceUpdateError, match="must be valid"):
        apply_confirmed_observation(model, _observation())

    observation = _observation()
    observation.sample_size = True
    with pytest.raises(EvidenceUpdateError, match="must be valid"):
        apply_confirmed_observation(binary_decision_model(), observation)


def test_audit_record_contains_reproducibility_metadata_not_raw_evidence():
    model = binary_decision_model()
    model.uncertain_variables[0].evidence_ids = ["evidence_001"]
    result = evaluate_decision_model(model)
    audit = build_analysis_audit_record(
        model,
        result,
        run_id="v2_20260718000000_1234abcd",
        parent_run_id="v2_20260717000000_1234abcd",
        run_type="internal",
        tenant_id="local",
        owner_actor_id=APPROVER,
        prompt_identifier="decision-model-proposal-v1",
        prompt_hash="a" * 64,
        ontology_hash="b" * 64,
    )
    serialized = audit.model_dump_json()

    assert audit.decision_model_hash == result.model_hash
    assert audit.random_seed == result.seed
    assert audit.source_evidence_ids == ["evidence_001"]
    assert "evidence_001" in serialized
    assert "raw_answer" not in serialized
    assert "confidential document" not in serialized


def test_audit_hash_fields_reject_raw_text():
    model = binary_decision_model()
    result = evaluate_decision_model(model)

    with pytest.raises(ValueError):
        build_analysis_audit_record(
            model,
            result,
            run_id="v2_20260718000000_1234abcd",
            run_type="public",
            prompt_hash="raw confidential prompt text",
        )
