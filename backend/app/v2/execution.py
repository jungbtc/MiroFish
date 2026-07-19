"""Compile accepted decision evidence into an auditable execution contract."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .schemas import ExecutionAction, ExecutionFact, ExecutionPlan, V2RunState


PLACEHOLDER_OWNER = re.compile(
    r"\b(?:decision owner|executive sponsor|operating lead|program owner|strategy\s*&\s*finance|"
    r"operating owner|finance approver|analytics owner|risk and compliance approver|"
    r"name required|owner not assigned)\b",
    re.IGNORECASE,
)
OBSERVABLE_CONDITION = re.compile(
    r"\d|\b(?:approved|available|completed?|cleared|resolved|zero|none|no unresolved|"
    r"pass(?:es|ed)?|breach(?:es|ed)?|incident|complaint|suspend(?:ed)?|terminate(?:d)?)\b",
    re.IGNORECASE,
)


class DecisionExecutionCompiler:
    """Turn evidence into the smallest complete set of execution stages.

    The compiler is deterministic: language generation can polish a plan later,
    but cannot decide whether a binding constraint needs a gate or stop trigger.
    """

    VERSION = "execution_compiler_v1"

    @staticmethod
    def is_placeholder_owner(value: str) -> bool:
        return bool(PLACEHOLDER_OWNER.search(value or ""))

    def compile(self, state: V2RunState) -> ExecutionPlan:
        leader = self._leading_action(state)
        facts = self._extract_facts(state)
        actions = self._build_actions(state, leader, facts)
        coverage = self._coverage(facts, actions)
        executability = self._validate(actions, facts, coverage)
        return ExecutionPlan(
            version=self.VERSION,
            decision_action_id=getattr(leader, "hypothesis_id", None),
            decision_action_label=(
                getattr(leader, "label", None)
                or "No executable management action has been selected"
            ),
            facts=facts,
            actions=actions,
            coverage=coverage,
            executability=executability,
            ready=bool(executability["ready"]),
            generated_at=datetime.now().isoformat(),
        )

    def _leading_action(self, state: V2RunState):
        candidates = [item for item in state.hypotheses if item.status != "pruned"]
        return max(candidates, key=lambda item: item.support_score, default=None)

    def _extract_facts(self, state: V2RunState) -> List[ExecutionFact]:
        questions = {item.question_id: item for item in state.internal_questions}
        facts: List[ExecutionFact] = []
        answered_question_ids = set()
        seen = set()

        for evidence in state.internal_evidence:
            if evidence.retracted or not evidence.decision_usable:
                continue
            question = questions.get(evidence.question_id)
            if not question:
                continue
            answered_question_ids.add(question.question_id)
            clauses = self._clauses(evidence.answer)
            for clause_index, clause in enumerate(clauses):
                for fact_type in self._fact_types(clause, question.category):
                    key = (fact_type, re.sub(r"\W+", " ", clause.lower()).strip())
                    if key in seen:
                        continue
                    seen.add(key)
                    value, unit = self._measurement(clause)
                    fact_id = self._id(
                        "execution_fact",
                        f"{evidence.evidence_id}:{clause_index}:{fact_type}",
                    )
                    facts.append(
                        ExecutionFact(
                            fact_id=fact_id,
                            fact_type=fact_type,
                            statement=self._normalize_statement(clause),
                            value=value,
                            unit=unit,
                            scope=self._scope(clause),
                            clarity=(
                                "high"
                                if value is not None or self._binding_language(clause)
                                else "medium"
                            ),
                            binding=self._is_binding(clause, fact_type),
                            source_question_id=question.question_id,
                            source_question_category=question.category,
                            source_answer_id=evidence.evidence_id,
                            approved_by=(
                                question.owner_hint
                                if PLACEHOLDER_OWNER.search(evidence.submitted_by or "")
                                else (evidence.submitted_by or question.owner_hint)
                            ),
                        )
                    )

        for question in state.internal_questions:
            if question.question_id in answered_question_ids or question.status == "answered":
                continue
            facts.append(
                ExecutionFact(
                    fact_id=self._id("execution_fact", f"unknown:{question.question_id}"),
                    fact_type="unknown",
                    statement=self._normalize_statement(question.question),
                    scope="selected action",
                    clarity="low",
                    binding=False,
                    source_question_id=question.question_id,
                    source_question_category=question.category,
                    approved_by=question.owner_hint,
                )
            )

        existing_statements = {item.statement.lower() for item in facts}
        for assumption in state.assumptions:
            if assumption.status.lower() in {"resolved", "confirmed", "closed"}:
                continue
            statement = self._normalize_statement(assumption.text)
            if statement.lower() in existing_statements:
                continue
            facts.append(
                ExecutionFact(
                    fact_id=self._id("execution_fact", f"assumption:{assumption.assumption_id}"),
                    fact_type="assumption",
                    statement=statement,
                    scope="selected action",
                    clarity="medium",
                    binding=False,
                    source_claim_id=(assumption.source_claim_ids or [None])[0],
                )
            )
            if sum(item.fact_type == "assumption" for item in facts) >= 3:
                break

        risk_pattern = re.compile(
            r"\b(?:union|labor|workload|employee|barista|customer conflict|complaint|opposition|"
            r"privacy|security|regulatory|service disruption)\b",
            re.IGNORECASE,
        )
        for claim in state.claims:
            if not risk_pattern.search(claim.text):
                continue
            statement = self._normalize_statement(claim.text)
            if statement.lower() in existing_statements:
                continue
            facts.append(
                ExecutionFact(
                    fact_id=self._id("execution_fact", f"risk:{claim.claim_id}"),
                    fact_type="stakeholder_risk",
                    statement=statement,
                    scope="affected stakeholders",
                    clarity="medium" if claim.citations else "low",
                    binding=False,
                    source_claim_id=claim.claim_id,
                )
            )
            if sum(item.fact_type == "stakeholder_risk" for item in facts) >= 3:
                break

        return facts[:32]

    def _clauses(self, answer: str) -> List[str]:
        text = re.sub(r"\s+", " ", answer or "").strip()
        if not text or text == "[REDACTED_INTERNAL_EVIDENCE]":
            return []
        primary = [
            item.strip(" ,")
            for item in re.split(r"(?<!\d)\.(?!\d)|[;\n]+", text)
            if item.strip(" ,")
        ]
        clauses: List[str] = []
        for item in primary:
            fragments = [
                part.strip(" ,")
                for part in re.split(r"\s+(?:and|but)\s+", item, flags=re.IGNORECASE)
                if part.strip(" ,")
            ]
            clauses.extend(fragments if len(fragments) > 1 else [item])
        return clauses[:16]

    def _fact_types(self, clause: str, category: str) -> List[str]:
        lower = clause.lower()
        types: List[str] = []
        patterns = (
            ("stop_trigger", r"\b(?:pause|suspend|reverse|terminate|stop after|shutdown|breach)\b"),
            ("budget", r"[$€£]|\b(?:budget|funding|spend|cost|loss|payback|contribution|tranche)\b"),
            ("owner", r"\b(?:owner|owned by|accountable|responsible|led by|approver)\b"),
            ("capacity", r"\b(?:capacity|staff|headcount|fte|labor hours?|stores?|locations?|sites?)\b"),
            ("success_metric", r"\b(?:success|target|conversion|transactions?|revenue|margin|profit|retention|churn|improvement)\b"),
            ("guardrail", r"\b(?:guardrail|must not|no more than|maximum|minimum|wait|delay|p95|ceiling|downside)\b"),
            ("hard_constraint", r"\b(?:will not approve|not permitted|not allowed|prohibited|cannot|must not|only if|non-negotiable|disqualif)\b"),
            ("dependency", r"\b(?:depends on|dependency|requires?|until|before launch|clearance|consultation|review completed|testing)\b"),
            ("stakeholder_risk", r"\b(?:union|workload|conflict|complaint|opposition|overtime|remake|refund)\b"),
        )
        for fact_type, pattern in patterns:
            if re.search(pattern, lower):
                types.append(fact_type)

        if not types:
            fallback = {
                "strategic_success": "objective",
                "constraints": "hard_constraint",
                "financial_capacity": "budget",
                "execution_capacity": "capacity",
                "risk_tolerance": "guardrail",
                "timing": "dependency",
            }.get(category, "assumption")
            types.append(fallback)
        elif category == "strategic_success" and "success_metric" not in types:
            types.append("objective")
        return list(dict.fromkeys(types))[:3]

    def _measurement(self, clause: str) -> Tuple[Optional[float], Optional[str]]:
        currency = re.search(
            r"([$€£])\s*([0-9]+(?:\.[0-9]+)?)\s*(million|billion|m|bn|k|thousand)?",
            clause,
            re.IGNORECASE,
        )
        if currency:
            multiplier = {
                "billion": 1_000_000_000,
                "bn": 1_000_000_000,
                "million": 1_000_000,
                "m": 1_000_000,
                "thousand": 1_000,
                "k": 1_000,
            }.get((currency.group(3) or "").lower(), 1)
            unit = {"$": "USD", "€": "EUR", "£": "GBP"}[currency.group(1)]
            return float(currency.group(2)) * multiplier, unit
        percent = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", clause)
        if percent:
            return float(percent.group(1)), "percent"
        measured = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*(seconds?|minutes?|hours?|days?|weeks?|months?|years?|stores?|locations?|sites?|fte|people|orders?|transactions?)\b",
            clause,
            re.IGNORECASE,
        )
        if measured:
            return float(measured.group(1)), measured.group(2).lower()
        return None, None

    def _binding_language(self, clause: str) -> bool:
        return bool(
            re.search(
                r"\b(?:must|shall|required|only|approved|capped?|maximum|minimum|at least|"
                r"no more than|will not|cannot|not permitted|not allowed|until)\b",
                clause,
                re.IGNORECASE,
            )
        )

    def _is_binding(self, clause: str, fact_type: str) -> bool:
        return fact_type in {"hard_constraint", "budget", "capacity", "guardrail", "stop_trigger"} and (
            self._binding_language(clause) or self._measurement(clause)[0] is not None
        )

    def _scope(self, clause: str) -> str:
        lower = clause.lower()
        if "pilot" in lower or re.search(r"\b\d+[- ]stores?\b", lower):
            return "initial operating tranche"
        if "national" in lower or "all stores" in lower:
            return "full rollout"
        if "union" in lower:
            return "union-represented operations"
        return "selected action"

    def _normalize_statement(self, value: str) -> str:
        text = re.sub(r"\s+", " ", value or "").strip(" ,.;")
        if not text:
            return "Unspecified execution condition"
        return text[:1].upper() + text[1:]

    def _build_actions(self, state: V2RunState, leader, facts: Sequence[ExecutionFact]) -> List[ExecutionAction]:
        by_type: Dict[str, List[ExecutionFact]] = defaultdict(list)
        for fact in facts:
            by_type[fact.fact_type].append(fact)

        label = getattr(leader, "label", None) or "the selected management action"
        role = getattr(leader, "decision_role", "alternative")
        accountable = (state.action_confirmation or {}).get("confirmed_by") or "Executive sponsor (name required)"
        execution_owner = self._owner(
            by_type["capacity"] + by_type["owner"],
            "Program director (name required)",
        )
        finance_owner = self._owner(by_type["budget"], "Finance approver (name required)")
        risk_owner = self._owner(
            by_type["hard_constraint"] + by_type["guardrail"],
            "Risk and compliance approver (name required)",
        )
        measurement_owner = self._owner(
            by_type["success_metric"] + by_type["objective"],
            "Analytics owner (name required)",
        )
        assigned_owners = state.execution_owner_assignments or {}
        measurement_owner = assigned_owners.get("VALIDATE", measurement_owner)
        finance_owner = assigned_owners.get("GATE", finance_owner)

        resource_facts = by_type["budget"] + by_type["capacity"]
        resource_boundary = self._join_statements(
            resource_facts,
            "No approved budget or capacity allocation is recorded.",
            2,
        )
        constraint_facts = by_type["hard_constraint"] + by_type["guardrail"]
        metric_facts = by_type["success_metric"] + by_type["objective"]
        dependency_facts = by_type["dependency"]
        unknown_facts = by_type["unknown"] + by_type["assumption"]
        stop_facts = by_type["stop_trigger"] + by_type["guardrail"] + by_type["hard_constraint"]
        risk_facts = by_type["stakeholder_risk"]

        if role == "defer":
            titles = {
                "COMMIT": f"Authorize and bound {label.lower()}",
                "DESIGN": "Define the shutdown, preservation, and re-entry operating model",
                "BUILD": "Deliver the suspension, communication, and resource-release package",
                "VALIDATE": "Close the unknowns that could justify reopening the decision",
                "GATE": "Evaluate whether re-entry conditions have been met",
                "PAUSE_REVERSE": "Prevent unauthorized spend or execution while the decision is deferred",
            }
        else:
            titles = {
                "COMMIT": f"Authorize the bounded first commitment for {label}",
                "DESIGN": "Translate every binding constraint into the operating model",
                "BUILD": "Deliver the operating controls, readiness package, and measurement system",
                "VALIDATE": "Run the bounded validation and resolve material assumptions",
                "GATE": "Evaluate the next commitment against every acceptance threshold",
                "PAUSE_REVERSE": "Suspend or reverse the strategy when a binding guardrail fails",
            }

        specs = [
            (
                "COMMIT", "Stage 0 · Commitment", titles["COMMIT"], accountable,
                "A signed decision charter that authorizes scope, resources, accountability, exclusions, and the first release of funds.",
                "Day 0",
                resource_facts + constraint_facts + by_type["owner"],
                dependency_facts,
                "Do not release resources; return the decision to action confirmation.",
            ),
            (
                "DESIGN", "Stage 1 · Operating-model design", titles["DESIGN"], execution_owner,
                "An approved operating-model specification covering scope rules, workflow controls, escalation, stakeholder safeguards, and local suspension authority.",
                "Day 7",
                constraint_facts + risk_facts + by_type["capacity"],
                dependency_facts,
                "Return the selected path to redesign; do not begin build work.",
            ),
            (
                "BUILD", "Stage 2 · Readiness", titles["BUILD"], execution_owner,
                "A release-ready package of product or process controls, training, communications, measurement definitions, and an operating dashboard.",
                "Day 21",
                dependency_facts + constraint_facts + metric_facts,
                dependency_facts,
                "Block launch until every failed readiness criterion is remediated and re-approved.",
            ),
            (
                "VALIDATE", "Stage 3 · Validation", titles["VALIDATE"], measurement_owner,
                "A checkpoint evidence pack comparing the selected tranche with its approved baseline or control and resolving each material unknown.",
                "First operating checkpoint",
                metric_facts + unknown_facts + risk_facts + by_type["capacity"],
                dependency_facts,
                "Continue only within the current tranche; redesign or stop if a material assumption cannot be tested.",
            ),
            (
                "GATE", "Stage 4 · Expansion gate", titles["GATE"], finance_owner,
                "A signed gate decision recording every passed and failed threshold and the exact next allowed commitment.",
                "End of first approved checkpoint",
                metric_facts + constraint_facts + resource_facts + risk_facts,
                dependency_facts,
                "Do not expand. Continue the bounded tranche, redesign a named component, or terminate.",
            ),
            (
                "PAUSE_REVERSE", "Stage 5 · Pause / reverse", titles["PAUSE_REVERSE"], risk_owner,
                "A tested store-, team-, or program-level suspension protocol with named authority, notification steps, and recovery or termination criteria.",
                "Effective before launch; monitored continuously",
                stop_facts + by_type["budget"] + risk_facts,
                dependency_facts,
                "Suspend the affected scope immediately; terminate the commitment when recovery within the approved boundary is no longer credible.",
            ),
        ]

        actions: List[ExecutionAction] = []
        for index, (action_type, stage, title, owner, deliverable, deadline, criteria_facts, deps, failure) in enumerate(specs, 1):
            criteria = self._criteria(criteria_facts, action_type)
            evidence_ids = sorted({fact.fact_id for fact in criteria_facts})
            dependencies = [fact.statement for fact in deps[:3]]
            if index > 1:
                dependencies.insert(0, f"A-{index - 1:02d} deliverable accepted")
            actions.append(
                ExecutionAction(
                    action_id=f"A-{index:02d}",
                    action_type=action_type,
                    stage=stage,
                    title=title,
                    purpose=self._purpose(action_type, label),
                    owner=owner,
                    accountable_executive=accountable,
                    contributors=self._contributors(action_type),
                    start_condition=(
                        "Management action set confirmed"
                        if index == 1
                        else f"A-{index - 1:02d} accepted"
                    ),
                    deliverable=deliverable,
                    deadline=deadline,
                    budget_or_capacity=resource_boundary,
                    acceptance_criteria=criteria,
                    dependencies=dependencies[:4],
                    evidence_source_ids=evidence_ids,
                    failure_response=failure,
                    status="ready" if state.decision_completion.get("actions_confirmed") else "draft",
                )
            )
        return actions

    def _criteria(self, facts: Sequence[ExecutionFact], action_type: str) -> List[str]:
        unique = list(dict.fromkeys(fact.statement for fact in facts))
        if action_type == "GATE" and not unique:
            return ["No measurable expansion threshold is approved; expansion is prohibited."]
        if action_type == "PAUSE_REVERSE" and not unique:
            return ["No observable pause or reversal condition is approved; launch is prohibited."]
        if not unique:
            return ["Required execution input is missing and must be approved before this stage can pass."]
        if action_type == "GATE":
            unique.append("A strong upside metric cannot override a failed legal, labor, customer, operating, or financial guardrail.")
        return unique[:6]

    def _owner(self, facts: Sequence[ExecutionFact], fallback: str) -> str:
        for fact in facts:
            candidate = (fact.approved_by or "").strip()
            if candidate and not PLACEHOLDER_OWNER.search(candidate):
                return candidate
        return fallback

    def _join_statements(self, facts: Sequence[ExecutionFact], fallback: str, limit: int) -> str:
        statements = list(dict.fromkeys(fact.statement for fact in facts))
        return " · ".join(statements[:limit]) if statements else fallback

    def _purpose(self, action_type: str, label: str) -> str:
        purposes = {
            "COMMIT": f"Authorize only the resources and scope required to begin {label}, without silently approving later expansion.",
            "DESIGN": "Convert accepted constraints and stakeholder risks into explicit operating rules before work begins.",
            "BUILD": "Create the concrete systems, process controls, training, and instrumentation required to operate the decision safely.",
            "VALIDATE": "Test material assumptions and measure the approved objective and guardrails under bounded exposure.",
            "GATE": "Allow the next commitment only when every binding threshold passes; record which facts caused the outcome.",
            "PAUSE_REVERSE": "Make suspension and reversal executable before a breach occurs, with no dependence on ad hoc escalation.",
        }
        return purposes[action_type]

    def _contributors(self, action_type: str) -> List[str]:
        return {
            "COMMIT": ["Finance", "Legal / compliance", "Operations"],
            "DESIGN": ["Operations", "Product / process", "Legal / compliance", "Affected frontline teams"],
            "BUILD": ["Product / technology", "Operations", "Training / communications", "Analytics"],
            "VALIDATE": ["Analytics", "Operations", "Finance", "Risk / compliance"],
            "GATE": ["Executive steering group", "Finance", "Operations", "Risk / compliance"],
            "PAUSE_REVERSE": ["Operations", "Risk / compliance", "Customer support", "Finance"],
        }[action_type]

    def _coverage(self, facts: Sequence[ExecutionFact], actions: Sequence[ExecutionAction]) -> Dict:
        mapped = {fact_id for action in actions for fact_id in action.evidence_source_ids}
        binding = [fact for fact in facts if fact.binding and fact.clarity == "high"]
        unmapped = [fact.fact_id for fact in binding if fact.fact_id not in mapped]
        return {
            "binding_fact_count": len(binding),
            "mapped_binding_fact_count": len(binding) - len(unmapped),
            "unmapped_binding_fact_ids": unmapped,
            "coverage_percent": round(
                100 * (len(binding) - len(unmapped)) / len(binding), 1
            ) if binding else 100.0,
            "complete": not unmapped,
            "warning": (
                "Decision-relevant evidence not operationalized."
                if unmapped else None
            ),
        }

    def _validate(self, actions: Sequence[ExecutionAction], facts: Sequence[ExecutionFact], coverage: Dict) -> Dict:
        action_count = max(1, len(actions))
        ownership = sum(
            not PLACEHOLDER_OWNER.search(action.owner)
            and not PLACEHOLDER_OWNER.search(action.accountable_executive)
            for action in actions
        ) / action_count
        deliverables = sum(bool(action.deliverable.strip()) for action in actions) / action_count
        timing = sum(bool(action.deadline.strip()) for action in actions) / action_count
        metric_actions = [action for action in actions if action.action_type in {"VALIDATE", "GATE", "PAUSE_REVERSE"}]
        metric_coverage = sum(
            any(OBSERVABLE_CONDITION.search(item) for item in action.acceptance_criteria)
            for action in metric_actions
        ) / max(1, len(metric_actions))
        dependency_resolution = sum(bool(action.dependencies) for action in actions) / action_count
        has_resources = any(
            fact.fact_type in {"budget", "capacity"}
            and fact.binding
            and fact.value is not None
            for fact in facts
        )
        resource_feasibility = 1.0 if has_resources else 0.0
        pause = next((item for item in actions if item.action_type == "PAUSE_REVERSE"), None)
        reversal_clarity = 1.0 if pause and any(
            OBSERVABLE_CONDITION.search(item) for item in pause.acceptance_criteria
        ) else 0.0

        dimensions = {
            "ownership_completeness": round(100 * ownership, 1),
            "deliverable_specificity": round(100 * deliverables, 1),
            "timing_specificity": round(100 * timing, 1),
            "metric_coverage": round(100 * metric_coverage, 1),
            "dependency_resolution": round(100 * dependency_resolution, 1),
            "resource_feasibility": round(100 * resource_feasibility, 1),
            "reversal_clarity": round(100 * reversal_clarity, 1),
        }
        score = round(
            20 * ownership
            + 20 * deliverables
            + 15 * timing
            + 15 * metric_coverage
            + 10 * dependency_resolution
            + 10 * resource_feasibility
            + 10 * reversal_clarity,
            1,
        )

        failures: List[str] = []
        for action in actions:
            if PLACEHOLDER_OWNER.search(action.owner) or PLACEHOLDER_OWNER.search(action.accountable_executive):
                failures.append(f"{action.action_id}: replace placeholder ownership with named accountable roles.")
            if not action.deadline.strip():
                failures.append(f"{action.action_id}: deadline is missing.")
            if not action.deliverable.strip():
                failures.append(f"{action.action_id}: deliverable is missing.")
        if not has_resources:
            failures.append("No binding budget or capacity allocation is recorded for the first commitment.")
        gate = next((item for item in actions if item.action_type == "GATE"), None)
        if not gate or not any(OBSERVABLE_CONDITION.search(item) for item in gate.acceptance_criteria):
            failures.append("The expansion gate has no measurable or observable acceptance criterion.")
        if reversal_clarity == 0:
            failures.append("The pause / reverse action has no numerical or observable trigger.")
        if not coverage.get("complete"):
            failures.append("Decision-relevant evidence not operationalized.")

        failures = list(dict.fromkeys(failures))
        return {
            "score": score,
            "dimensions": dimensions,
            "hard_failures": failures,
            "ready": score >= 80 and not failures,
        }

    @staticmethod
    def _id(prefix: str, value: str) -> str:
        return f"{prefix}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]}"
