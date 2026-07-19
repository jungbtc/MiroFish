"""Versioned, serializable contracts for deterministic decision analysis.

The models in this module intentionally contain no LLM behavior and no arbitrary
expression language.  Consequences are supplied either as an explicit payoff
table or as a small affine model whose coefficients can be audited directly.
"""

from __future__ import annotations

import math
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)


def _require_json_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a JSON number, not a boolean or string")
    return value


FiniteFloat = Annotated[
    float,
    BeforeValidator(_require_json_number),
    Field(allow_inf_nan=False),
]
NonNegativeFinite = Annotated[
    float,
    BeforeValidator(_require_json_number),
    Field(ge=0.0, allow_inf_nan=False),
]
PositiveFinite = Annotated[
    float,
    BeforeValidator(_require_json_number),
    Field(gt=0.0, allow_inf_nan=False),
]
# Python's standard-library beta sampler is severely biased below this range;
# fail closed rather than report reproducible but numerically false samples.
MIN_BETA_SHAPE = 0.01
MAX_BETA_SHAPE = 1e6
MAX_EVIDENCE_SAMPLE_SIZE = 1_000_000
BetaShape = Annotated[
    float,
    BeforeValidator(_require_json_number),
    Field(ge=MIN_BETA_SHAPE, le=MAX_BETA_SHAPE, allow_inf_nan=False),
]
MIN_NORMAL_SCALE = 1e-12
MAX_NORMAL_SCALE = 1e150
NormalScale = Annotated[
    float,
    BeforeValidator(_require_json_number),
    Field(ge=MIN_NORMAL_SCALE, le=MAX_NORMAL_SCALE, allow_inf_nan=False),
]
Probability = Annotated[
    float,
    BeforeValidator(_require_json_number),
    Field(ge=0.0, le=1.0, allow_inf_nan=False),
]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
StateValue = Union[StrictStr, StrictBool, StrictInt, FiniteFloat]
ApprovalStatus = Literal["proposed", "approved", "rejected"]
MAX_ACTIONS = 64
MAX_VARIABLES = 24
MAX_DISTRIBUTION_STATES = 1_000
MAX_PAYOFF_ROWS = 200_000


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoricalParameters(StrictModel):
    probabilities: Dict[str, Probability] = Field(max_length=MAX_DISTRIBUTION_STATES)

    @model_validator(mode="after")
    def require_multiple_states(self):
        if len(self.probabilities) < 2:
            raise ValueError("categorical distributions require at least two states")
        if any(not str(value).strip() for value in self.probabilities):
            raise ValueError("categorical state labels cannot be empty")
        return self


class DiscretePoint(StrictModel):
    value: StateValue
    probability: Probability

    @model_validator(mode="after")
    def validate_value_range(self):
        _validate_state_value_range(self.value)
        return self


class DiscreteParameters(StrictModel):
    points: List[DiscretePoint] = Field(
        min_length=2,
        max_length=MAX_DISTRIBUTION_STATES,
    )


class BernoulliParameters(StrictModel):
    probability_true: Probability


class BetaParameters(StrictModel):
    # Bounds keep the standard-library gamma sampler out of pathological
    # underflow loops while covering ordinary priors and observed counts.
    alpha: BetaShape
    beta: BetaShape


class NormalParameters(StrictModel):
    mean: FiniteFloat
    standard_deviation: NormalScale
    lower_bound: Optional[FiniteFloat] = None
    upper_bound: Optional[FiniteFloat] = None

    @model_validator(mode="after")
    def validate_bounds(self):
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound >= self.upper_bound
        ):
            raise ValueError("normal lower_bound must be less than upper_bound")
        return self


class TriangularParameters(StrictModel):
    minimum: FiniteFloat
    mode: FiniteFloat
    maximum: FiniteFloat

    @model_validator(mode="after")
    def validate_shape(self):
        if not self.minimum < self.maximum:
            raise ValueError("triangular minimum must be less than maximum")
        if not math.isfinite(float(self.maximum) - float(self.minimum)):
            raise ValueError("triangular range must have a finite span")
        if not self.minimum <= self.mode <= self.maximum:
            raise ValueError("triangular mode must lie between minimum and maximum")
        return self


class UniformParameters(StrictModel):
    minimum: FiniteFloat
    maximum: FiniteFloat

    @model_validator(mode="after")
    def validate_range(self):
        if not self.minimum < self.maximum:
            raise ValueError("uniform minimum must be less than maximum")
        if not math.isfinite(float(self.maximum) - float(self.minimum)):
            raise ValueError("uniform range must have a finite span")
        return self


class FixedParameters(StrictModel):
    value: StateValue

    @model_validator(mode="after")
    def validate_value_range(self):
        _validate_state_value_range(self.value)
        return self


class DistributionBase(StrictModel):
    source: str = Field(min_length=1, max_length=500)
    approval_status: ApprovalStatus = "proposed"
    proposed_by: Optional[str] = Field(default=None, max_length=200)
    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[str] = Field(default=None, max_length=100)
    rationale: str = Field(default="", max_length=4_000)


class CategoricalDistribution(DistributionBase):
    type: Literal["categorical"] = "categorical"
    parameters: CategoricalParameters


class DiscreteDistribution(DistributionBase):
    type: Literal["discrete"] = "discrete"
    parameters: DiscreteParameters


class BernoulliDistribution(DistributionBase):
    type: Literal["bernoulli"] = "bernoulli"
    parameters: BernoulliParameters


class BetaDistribution(DistributionBase):
    type: Literal["beta"] = "beta"
    parameters: BetaParameters


class NormalDistribution(DistributionBase):
    type: Literal["normal"] = "normal"
    parameters: NormalParameters


class TriangularDistribution(DistributionBase):
    type: Literal["triangular"] = "triangular"
    parameters: TriangularParameters


class UniformDistribution(DistributionBase):
    type: Literal["uniform"] = "uniform"
    parameters: UniformParameters


class FixedDistribution(DistributionBase):
    type: Literal["fixed", "deterministic"] = "fixed"
    parameters: FixedParameters


Distribution = Annotated[
    Union[
        CategoricalDistribution,
        DiscreteDistribution,
        BernoulliDistribution,
        BetaDistribution,
        NormalDistribution,
        TriangularDistribution,
        UniformDistribution,
        FixedDistribution,
    ],
    Field(discriminator="type"),
]


class Action(StrictModel):
    id: Identifier
    label: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4_000)
    status: ApprovalStatus = "proposed"
    proposed_by: Optional[str] = Field(default=None, max_length=200)
    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[str] = Field(default=None, max_length=100)


class UncertainVariable(StrictModel):
    id: Identifier
    label: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4_000)
    unit: str = Field(min_length=1, max_length=100)
    distribution: Distribution
    dependencies: List[Identifier] = Field(default_factory=list, max_length=MAX_VARIABLES)
    evidence_ids: List[Identifier] = Field(default_factory=list, max_length=10_000)
    approval_status: ApprovalStatus = "proposed"
    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[str] = Field(default=None, max_length=100)


class Outcome(StrictModel):
    """One auditable row in a complete state/action payoff table."""

    action_id: Identifier
    state: Dict[Identifier, StateValue]
    consequence: FiniteFloat
    consequence_unit: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_state_ranges(self):
        for value in self.state.values():
            _validate_state_value_range(value)
        return self


class AffinePayoff(StrictModel):
    """A deliberately small safe alternative to executable expressions."""

    action_id: Identifier
    intercept: FiniteFloat = 0.0
    coefficients: Dict[Identifier, FiniteFloat] = Field(default_factory=dict)
    consequence_unit: str = Field(min_length=1, max_length=100)


class UtilityModel(StrictModel):
    type: Literal["monetary", "utility_points"]
    risk_attitude: Literal["risk_neutral"] = "risk_neutral"
    unit: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    outcomes: List[Outcome] = Field(default_factory=list, max_length=MAX_PAYOFF_ROWS)
    affine_payoffs: List[AffinePayoff] = Field(default_factory=list, max_length=MAX_ACTIONS)
    approval_status: ApprovalStatus = "proposed"
    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[str] = Field(default=None, max_length=100)


class DecisionModel(StrictModel):
    id: Identifier
    version: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=12_000)
    consequence_unit: str = Field(min_length=1, max_length=100)
    actions: List[Action] = Field(max_length=MAX_ACTIONS)
    uncertain_variables: List[UncertainVariable] = Field(max_length=MAX_VARIABLES)
    utility_model: UtilityModel
    approval_status: ApprovalStatus = "proposed"
    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[str] = Field(default=None, max_length=100)
    model_hash: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class EvidenceObservation(StrictModel):
    variable_id: Identifier
    observation_type: Literal[
        "replace_point",
        "categorical_probabilities",
        "beta_counts",
        "normal_observation",
        "hard_range",
    ]
    value: Any
    effective_date: Optional[str] = Field(default=None, max_length=100)
    reliability_model: Optional[str] = Field(default=None, max_length=500)
    sample_size: Optional[
        Annotated[int, Field(strict=True, gt=0, le=MAX_EVIDENCE_SAMPLE_SIZE)]
    ] = None
    source_evidence_id: Identifier
    approval_status: ApprovalStatus = "proposed"
    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[str] = Field(default=None, max_length=100)


class InformationCost(StrictModel):
    cash_cost: NonNegativeFinite = 0.0
    delay_cost: NonNegativeFinite = 0.0
    organizational_burden: NonNegativeFinite = 0.0
    disclosure_risk_cost: NonNegativeFinite = 0.0
    validation_cost: NonNegativeFinite = 0.0
    total_cost: Optional[NonNegativeFinite] = None

    @model_validator(mode="after")
    def calculate_total(self):
        try:
            expected = math.fsum(
                [
                    float(self.cash_cost),
                    float(self.delay_cost),
                    float(self.organizational_burden),
                    float(self.disclosure_risk_cost),
                    float(self.validation_cost),
                ]
            )
        except OverflowError as exc:
            raise ValueError("information cost total must be finite") from exc
        if not math.isfinite(expected):
            raise ValueError("information cost total must be finite")
        if self.total_cost is not None and abs(float(self.total_cost) - expected) > 1e-9:
            raise ValueError("total_cost must equal the sum of its components")
        self.total_cost = expected
        return self


class MissingConfirmation(StrictModel):
    field: str
    item_id: Optional[str] = None
    reason: str


class CalculationTraceRow(StrictModel):
    state: Dict[str, StateValue]
    probability: NonNegativeFinite
    utility_by_action: Dict[str, FiniteFloat]
    best_action: Identifier
    best_utility: FiniteFloat


class DecisionAnalysisTrace(StrictModel):
    method: Literal["exact_enumeration", "monte_carlo"]
    model_hash: str
    seed: StrictInt
    sample_count: NonNegativeInt
    enumerated_state_count: NonNegativeInt = 0
    rows: List[CalculationTraceRow] = Field(default_factory=list)
    sample_preview: List[CalculationTraceRow] = Field(default_factory=list)
    sample_digest: Optional[str] = None


class SwitchingThreshold(StrictModel):
    variable_id: Identifier
    lower_state: StateValue
    upper_state: StateValue
    probability_of_upper_state: Probability
    action_below: Identifier
    action_above: Identifier


class ConvergenceDiagnostics(StrictModel):
    batch_count: NonNegativeInt
    standard_error_by_action: Dict[str, NonNegativeFinite] = Field(default_factory=dict)
    max_standard_error: NonNegativeFinite = 0.0
    stable_recommendation: bool = False
    recommendation_margin_to_error_ratio: NonNegativeFinite = 0.0


class NeedsConfirmationResult(StrictModel):
    status: Literal["needs_confirmation"] = "needs_confirmation"
    missing_confirmations: List[MissingConfirmation]
    model_hash: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class DecisionAnalysisResult(StrictModel):
    status: Literal["calculated"] = "calculated"
    recommended_action: Identifier
    runner_up: Optional[Identifier] = None
    recommendation_margin: NonNegativeFinite
    expected_utility_by_action: Dict[str, FiniteFloat]
    expected_regret_by_action: Dict[str, NonNegativeFinite]
    evpi: NonNegativeFinite
    evppi_by_variable: Dict[str, NonNegativeFinite]
    evppi_by_group: Dict[str, NonNegativeFinite] = Field(default_factory=dict)
    information_costs: Dict[str, InformationCost]
    net_information_value_by_variable: Dict[str, FiniteFloat]
    net_information_value_by_group: Dict[str, FiniteFloat] = Field(default_factory=dict)
    switching_thresholds: List[SwitchingThreshold]
    seed: StrictInt
    sample_count: NonNegativeInt
    model_hash: str
    model_version: str
    calculation_engine_version: str
    utility_model_version: str
    method: Literal["exact_enumeration", "monte_carlo"]
    convergence: ConvergenceDiagnostics
    warnings: List[str] = Field(default_factory=list)
    trace: DecisionAnalysisTrace


class EvidenceUpdateResult(StrictModel):
    status: Literal["applied", "not_applied_to_distribution"]
    variable_id: Identifier
    source_evidence_id: Identifier
    reason: str
    updated_model: DecisionModel


DecisionAnalysisOutcome = Union[NeedsConfirmationResult, DecisionAnalysisResult]


def _validate_state_value_range(value: StateValue) -> None:
    if isinstance(value, bool) or isinstance(value, str):
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("numeric state value is outside the supported finite range") from exc
    if not math.isfinite(numeric):
        raise ValueError("numeric state value is outside the supported finite range")
