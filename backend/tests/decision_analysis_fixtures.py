"""Small analytical fixtures whose expected values are verifiable by hand."""

from app.decision_analysis.schemas import (
    Action,
    AffinePayoff,
    BernoulliDistribution,
    BernoulliParameters,
    CategoricalDistribution,
    CategoricalParameters,
    DecisionModel,
    NormalDistribution,
    NormalParameters,
    Outcome,
    UncertainVariable,
    UtilityModel,
)


APPROVED_AT = "2026-07-18T00:00:00+00:00"
APPROVER = "decision_owner"


def approval_metadata():
    return {"approved_by": APPROVER, "approved_at": APPROVED_AT}


def binary_decision_model() -> DecisionModel:
    """Safe=40; risky=100 only in high demand, whose probability is 0.3.

    EU(safe)=40, EU(risky)=30, switching threshold=0.4, EVPI=18.
    A second independent variable has no payoff effect and therefore EVPPI=0.
    """

    approval = approval_metadata()
    variables = [
        UncertainVariable(
            id="demand",
            label="Demand",
            unit="state",
            distribution=CategoricalDistribution(
                parameters=CategoricalParameters(
                    probabilities={"low": 0.7, "high": 0.3}
                ),
                source="approved planning estimate",
                approval_status="approved",
                **approval,
            ),
            approval_status="approved",
            **approval,
        ),
        UncertainVariable(
            id="regulatory",
            label="Regulatory event",
            unit="boolean",
            distribution=BernoulliDistribution(
                parameters=BernoulliParameters(probability_true=0.5),
                source="approved planning estimate",
                approval_status="approved",
                **approval,
            ),
            approval_status="approved",
            **approval,
        ),
    ]
    outcomes = []
    for regulatory in (False, True):
        outcomes.extend(
            [
                Outcome(
                    action_id="safe",
                    state={"demand": "low", "regulatory": regulatory},
                    consequence=40.0,
                    consequence_unit="utility_points",
                ),
                Outcome(
                    action_id="safe",
                    state={"demand": "high", "regulatory": regulatory},
                    consequence=40.0,
                    consequence_unit="utility_points",
                ),
                Outcome(
                    action_id="risky",
                    state={"demand": "low", "regulatory": regulatory},
                    consequence=0.0,
                    consequence_unit="utility_points",
                ),
                Outcome(
                    action_id="risky",
                    state={"demand": "high", "regulatory": regulatory},
                    consequence=100.0,
                    consequence_unit="utility_points",
                ),
            ]
        )
    return DecisionModel(
        id="launch_decision",
        version="1.0.0",
        question="Should we choose the safe or risky launch?",
        consequence_unit="utility_points",
        actions=[
            Action(
                id="safe",
                label="Safe launch",
                status="approved",
                **approval,
            ),
            Action(
                id="risky",
                label="Risky launch",
                status="approved",
                **approval,
            ),
        ],
        uncertain_variables=variables,
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


def continuous_decision_model() -> DecisionModel:
    approval = approval_metadata()
    return DecisionModel(
        id="continuous_decision",
        version="1.0.0",
        question="Should we take a positive or negative exposure?",
        consequence_unit="utility_points",
        actions=[
            Action(id="positive", label="Positive", status="approved", **approval),
            Action(id="negative", label="Negative", status="approved", **approval),
        ],
        uncertain_variables=[
            UncertainVariable(
                id="market_move",
                label="Market move",
                unit="index_points",
                distribution=NormalDistribution(
                    parameters=NormalParameters(mean=0.3, standard_deviation=1.0),
                    source="approved forecast",
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
                    action_id="positive",
                    coefficients={"market_move": 1.0},
                    consequence_unit="utility_points",
                ),
                AffinePayoff(
                    action_id="negative",
                    coefficients={"market_move": -1.0},
                    consequence_unit="utility_points",
                ),
            ],
            approval_status="approved",
            **approval,
        ),
        approval_status="approved",
        **approval,
    )


def rare_event_decision_model() -> DecisionModel:
    """Finite fixture whose true/true joint mass underflows binary64."""

    approval = approval_metadata()
    variables = [
        UncertainVariable(
            id=variable_id,
            label=variable_id.upper(),
            unit="boolean",
            distribution=BernoulliDistribution(
                parameters=BernoulliParameters(probability_true=1e-200),
                source="approved rare-event fixture",
                approval_status="approved",
                **approval,
            ),
            approval_status="approved",
            **approval,
        )
        for variable_id in ("x", "y")
    ]
    outcomes = []
    for x in (False, True):
        for y in (False, True):
            outcomes.extend(
                [
                    Outcome(
                        action_id="rare_upside",
                        state={"x": x, "y": y},
                        consequence=(1e308 if x and y else 0.0),
                        consequence_unit="utility_points",
                    ),
                    Outcome(
                        action_id="baseline",
                        state={"x": x, "y": y},
                        consequence=1e-100,
                        consequence_unit="utility_points",
                    ),
                ]
            )
    return DecisionModel(
        id="rare_event_decision",
        version="1.0.0",
        question="Should the decision account for the joint rare event?",
        consequence_unit="utility_points",
        actions=[
            Action(id="rare_upside", label="Rare upside", status="approved", **approval),
            Action(id="baseline", label="Baseline", status="approved", **approval),
        ],
        uncertain_variables=variables,
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
