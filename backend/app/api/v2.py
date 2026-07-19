"""FOREFOLD decision API routes."""

from __future__ import annotations

import math
import re
from json import JSONDecodeError

from flask import Response, current_app, jsonify, request
from pydantic import ValidationError

from . import v2_bp
from ..v2.authorization import PublicRunRequiresFork, RunAuthorization, request_actor
from ..v2.pipeline import MiroFishV2Pipeline
from ..v2.refinement import CoreRefinementService
from ..v2.storage import ConfidentialStorageUnavailable, V2Storage
from ..models.project import ProjectManager
from ..services.report_agent import ReportManager, ReportStatus
from ..services.simulation_manager import SimulationManager
from ..services.simulation_runner import SimulationRunner
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.v2")

MAX_DOCUMENTS_PER_IMPORT = 32
MAX_DECISION_QUESTION_CHARS = 12_000
MAX_PROJECT_NAME_CHARS = 300
MAX_INTERNAL_ANSWER_CHARS = 50_000
MAX_SUBMITTED_BY_CHARS = 200
MAX_FOLLOWUP_QUESTION_CHARS = 4_000
MAX_PROPOSED_QUESTION_CHARS = 320
MIN_DECISION_SAMPLE_COUNT = 100
MAX_DECISION_SAMPLE_COUNT = 100_000
MIN_DECISION_SEED = -(2**63)
MAX_DECISION_SEED = 2**63 - 1


def _state_payload(state):
    payload = state.model_dump(mode="json")
    # The full provider prompt context can contain a large graph snapshot and
    # is never needed by browser code. Lineage flags communicate what was used.
    payload.pop("public_research_context", None)
    for document in payload.get("documents", []):
        metadata = document.get("metadata")
        if isinstance(metadata, dict):
            # Filesystem locations are implementation details and can reveal a
            # host username or deployment layout to API consumers.
            for key in list(metadata):
                if key.lower() == "path" or key.lower().endswith("_path"):
                    metadata.pop(key, None)
    for evidence in payload.get("internal_evidence", []):
        if evidence.get("confidential") or evidence.get("visibility") != "public":
            evidence["answer"] = "[REDACTED_INTERNAL_EVIDENCE]"
            evidence["answer_redacted"] = True
            evidence.pop("answer_storage_ref", None)
            evidence.pop("answer_storage_run_id", None)
    return payload


def _error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _forbidden():
    return _error("The authenticated actor cannot access this internal run.", 403)


def _fork_required(run_id: str):
    return (
        jsonify(
            {
                "success": False,
                "error": "Fork an internal child before adding private information.",
                "code": "needs_fork",
                "needs_fork": True,
                "fork_endpoint": f"/api/v2/runs/{run_id}/fork",
            }
        ),
        409,
    )


def _log_private_failure(context: str, error: Exception) -> None:
    """Log only the failure class; exception text can contain private case data."""
    logger.error("%s failed (%s)", context, type(error).__name__)


def _legacy_deep_research_disabled():
    if current_app.config.get("ENABLE_LEGACY_DEEP_RESEARCH", False):
        return None
    return _error(
        "Legacy Deep Research is disabled; continue with internal-information refinement.",
        410,
    )


def _load_or_create_core_refinement(report_id: str):
    """Resolve a completed primary report to its single refinement case."""
    report = ReportManager.get_report(report_id)
    if not report:
        raise FileNotFoundError(f"Report not found: {report_id}")
    if report.status != ReportStatus.COMPLETED:
        raise ValueError("The initial simulation report must complete before refinement.")
    if report.refinement_run_id:
        try:
            saved_state = V2Storage.load_state(report.refinement_run_id)
            RunAuthorization.assert_can_read(saved_state, request_actor())
            return CoreRefinementService().migrate_core_state(saved_state)
        except FileNotFoundError:
            # A stale link from an interrupted provisional start is repaired by
            # recreating the internal state; the core report itself is preserved.
            pass

    simulation = SimulationManager().get_simulation(report.simulation_id)
    if not simulation:
        raise ValueError("The report's source simulation could not be loaded.")
    project = ProjectManager.get_project(simulation.project_id)
    if not project:
        raise ValueError("The report's source project could not be loaded.")
    manager = SimulationManager()
    runner_state = SimulationRunner.get_run_state(simulation.simulation_id)
    state = CoreRefinementService().initialize_from_core_report(
        project_id=project.project_id,
        graph_id=report.graph_id or simulation.graph_id or project.graph_id,
        simulation_id=simulation.simulation_id,
        report_id=report.report_id,
        project_name=project.name,
        decision_question=report.simulation_requirement or project.simulation_requirement or "",
        report_markdown=report.markdown_content,
        graph_evidence={
            "graph_id": report.graph_id or simulation.graph_id or project.graph_id,
            "ontology": project.ontology or {},
            "analysis_summary": project.analysis_summary,
        },
        simulation_metadata={
            "simulation": simulation.to_dict(),
            "runtime": runner_state.to_dict() if runner_state else {},
            "configuration": manager.get_simulation_config(simulation.simulation_id) or {},
        },
    )
    report.project_id = project.project_id
    report.refinement_run_id = state.run_id
    ReportManager.save_report(report)
    return state


def _coerce_rounds(value):
    if value is None:
        return 3
    if isinstance(value, bool) or isinstance(value, (list, dict)):
        raise ValueError("rounds must be an integer")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("rounds must be an integer")
    if isinstance(value, str) and not re.fullmatch(r"[+-]?\d+", value.strip()):
        raise ValueError("rounds must be an integer")
    try:
        rounds = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rounds must be an integer") from exc
    if not 1 <= rounds <= 1_000:
        raise ValueError("rounds must be between 1 and 1000")
    return rounds


def _bounded_text(value, field: str, maximum: int, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise ValueError(f"{field} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters")
    return normalized


def _bounded_integer(
    value,
    field: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return value


def _decision_calculation_options(data):
    seed = _bounded_integer(
        data.get("seed"),
        "seed",
        default=0,
        minimum=MIN_DECISION_SEED,
        maximum=MAX_DECISION_SEED,
    )
    sample_count = _bounded_integer(
        data.get("sample_count"),
        "sample_count",
        default=10_000,
        minimum=MIN_DECISION_SAMPLE_COUNT,
        maximum=MAX_DECISION_SAMPLE_COUNT,
    )
    force_method = data.get("force_method")
    if force_method not in {None, "exact_enumeration", "monte_carlo"}:
        raise ValueError("force_method must be exact_enumeration or monte_carlo")
    information_costs = data.get("information_costs")
    if information_costs is not None and not isinstance(information_costs, dict):
        raise ValueError("information_costs must be an object")
    evppi_groups = data.get("evppi_groups")
    if evppi_groups is not None:
        if not isinstance(evppi_groups, dict) or not all(
            isinstance(group_id, str)
            and isinstance(variable_ids, list)
            and all(isinstance(variable_id, str) for variable_id in variable_ids)
            for group_id, variable_ids in evppi_groups.items()
        ):
            raise ValueError("evppi_groups must map group IDs to lists of variable IDs")
    return {
        "seed": seed,
        "sample_count": sample_count,
        "information_costs": information_costs,
        "evppi_groups": evppi_groups,
        "force_method": force_method,
    }


def _validate_structured_documents(documents):
    text_keys = {"text", "report", "content", "markdown"}
    for index, document in enumerate(documents):
        for key in text_keys:
            if key in document and document[key] is not None and not isinstance(document[key], str):
                raise ValueError(f"documents[{index}].{key} must be a string")
        for key in ("filename", "title", "name", "format"):
            if key in document and document[key] is not None and not isinstance(document[key], str):
                raise ValueError(f"documents[{index}].{key} must be a string")
        for collection_key in ("sections", "claims", "citations", "sources"):
            value = document.get(collection_key)
            if value is not None and not isinstance(value, list):
                raise ValueError(f"documents[{index}].{collection_key} must be a list")
        for section_index, section in enumerate(document.get("sections") or []):
            if not isinstance(section, (str, dict)):
                raise ValueError(
                    f"documents[{index}].sections[{section_index}] must be a string or object"
                )
            if isinstance(section, dict):
                for key in ("title", "heading", "text", "content", "body"):
                    if key in section and section[key] is not None and not isinstance(section[key], str):
                        raise ValueError(
                            f"documents[{index}].sections[{section_index}].{key} must be a string"
                        )
        for claim_index, claim in enumerate(document.get("claims") or []):
            if not isinstance(claim, (str, dict)):
                raise ValueError(
                    f"documents[{index}].claims[{claim_index}] must be a string or object"
                )
            if isinstance(claim, dict):
                for key in ("id", "claim_id", "text", "claim", "statement"):
                    if key in claim and claim[key] is not None and not isinstance(claim[key], str):
                        raise ValueError(
                            f"documents[{index}].claims[{claim_index}].{key} must be a string"
                        )
                for key in ("citations", "sources"):
                    if key in claim and claim[key] is not None and not isinstance(claim[key], list):
                        raise ValueError(
                            f"documents[{index}].claims[{claim_index}].{key} must be a list"
                        )


@v2_bp.route("/run", methods=["POST"])
@v2_bp.route("/research-pack", methods=["POST"])
def run_v2_pipeline():
    """Run the v2 evidence pipeline from multipart files or JSON documents."""
    try:
        pipeline = MiroFishV2Pipeline()
        if request.content_type and "multipart/form-data" in request.content_type:
            files = request.files.getlist("files")
            question = _bounded_text(
                request.form.get("question") or request.form.get("simulation_requirement") or "",
                "question",
                MAX_DECISION_QUESTION_CHARS,
                required=True,
            )
            project_name = _bounded_text(
                request.form.get("project_name") or "FOREFOLD Run",
                "project_name",
                MAX_PROJECT_NAME_CHARS,
                required=True,
            )
            rounds = _coerce_rounds(request.form.get("rounds"))
            scenario_theme = request.form.get("scenario_theme") or None
            if not files:
                return _error("At least one completed FOREFOLD report is required.")
            if len(files) > MAX_DOCUMENTS_PER_IMPORT:
                return _error(f"At most {MAX_DOCUMENTS_PER_IMPORT} reports can be imported at once.")
            state = pipeline.run_from_uploads(files, question, project_name, rounds, scenario_theme)
        else:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return _error("JSON request body must be an object.")
            documents = data.get("documents") or []
            if not isinstance(documents, list) or not all(isinstance(item, dict) for item in documents):
                return _error("documents must be a list of structured report objects.")
            if len(documents) > MAX_DOCUMENTS_PER_IMPORT:
                return _error(f"At most {MAX_DOCUMENTS_PER_IMPORT} reports can be imported at once.")
            _validate_structured_documents(documents)
            question_value = (
                data.get("question")
                if "question" in data
                else data.get("simulation_requirement", "")
            )
            question = _bounded_text(
                question_value if question_value is not None else "",
                "question",
                MAX_DECISION_QUESTION_CHARS,
                required=True,
            )
            project_value = data.get("project_name", "FOREFOLD Run")
            project_name = _bounded_text(
                "FOREFOLD Run" if project_value is None else project_value,
                "project_name",
                MAX_PROJECT_NAME_CHARS,
                required=True,
            )
            rounds = _coerce_rounds(data.get("rounds"))
            scenario_theme = data.get("scenario_theme")
            if scenario_theme is not None and not isinstance(scenario_theme, str):
                return _error("scenario_theme must be a string.")
            if not documents:
                return _error("At least one structured FOREFOLD report is required.")
            state = pipeline.run_from_inline_documents(documents, question, project_name, rounds, scenario_theme)

        return jsonify({"success": True, "data": _state_payload(state)})
    except ValidationError as e:
        _log_private_failure("v2 import validation", e)
        return _error("Imported report could not be normalized into a decision case.", 400)
    except ValueError as e:
        _log_private_failure("v2 run rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("v2 run", e)
        return _error("Decision import failed unexpectedly.", 500)


@v2_bp.route("/demo", methods=["POST"])
def run_v2_demo():
    try:
        rounds = _coerce_rounds(request.args.get("rounds"))
    except ValueError as e:
        return _error(str(e), 400)
    try:
        state = MiroFishV2Pipeline().run_demo(rounds=rounds)
        return jsonify({"success": True, "data": _state_payload(state)})
    except Exception as e:
        _log_private_failure("v2 demo", e)
        return _error("Decision demo failed unexpectedly.", 500)


@v2_bp.route("/core/reports/<report_id>/refinement", methods=["GET"])
def get_core_report_refinement(report_id: str):
    """Return the report's continuous, locally initialized next stage."""
    try:
        state = _load_or_create_core_refinement(report_id)
        RunAuthorization.assert_can_read(state, request_actor())
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Report not found: {report_id}", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("core report refinement load", e)
        return _error("Research and decision refinement could not be loaded.", 500)


@v2_bp.route("/core/reports/<report_id>/research/start", methods=["POST"])
def start_core_report_research(report_id: str):
    disabled = _legacy_deep_research_disabled()
    if disabled:
        return disabled
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        if data.get("retry") is not None and not isinstance(data.get("retry"), bool):
            return _error("retry must be a boolean.")
        state = _load_or_create_core_refinement(report_id)
        state = CoreRefinementService().start_research(
            state.run_id,
            retry=bool(data.get("retry", False)),
        )
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Report not found: {report_id}", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("core report research start", e)
        return _error("Public Deep Research could not be started.", 500)


@v2_bp.route("/core/reports/<report_id>/research/sync", methods=["POST"])
def sync_core_report_research(report_id: str):
    disabled = _legacy_deep_research_disabled()
    if disabled:
        return disabled
    try:
        state = _load_or_create_core_refinement(report_id)
        state = CoreRefinementService().sync_research(state.run_id)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Report not found: {report_id}", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("core report research sync", e)
        return _error("Public Deep Research status could not be synchronized.", 500)


@v2_bp.route("/core/reports/<report_id>/research/cancel", methods=["POST"])
def cancel_core_report_research(report_id: str):
    disabled = _legacy_deep_research_disabled()
    if disabled:
        return disabled
    try:
        state = _load_or_create_core_refinement(report_id)
        state = CoreRefinementService().cancel_research(state.run_id)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Report not found: {report_id}", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("core report research cancellation", e)
        return _error("Public Deep Research could not be cancelled.", 500)


@v2_bp.route("/runs/<run_id>", methods=["GET"])
def get_v2_run(run_id: str):
    try:
        state = MiroFishV2Pipeline().load_state(run_id, actor=request_actor())
        if state.workflow_origin == "core_mirofish_report":
            state = CoreRefinementService().migrate_core_state(state)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("v2 run load", e)
        return _error("Decision run could not be loaded.", 500)


@v2_bp.route("/runs/<run_id>/fork", methods=["POST"])
def fork_v2_run(run_id: str):
    try:
        data = request.get_json(silent=True)
        if data is not None and not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        state = MiroFishV2Pipeline().fork_public_run(run_id, actor=request_actor())
        return jsonify({"success": True, "data": _state_payload(state)}), 201
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("v2 run fork", e)
        return _error("An internal child run could not be created.", 500)


@v2_bp.route("/runs/<run_id>/lineage", methods=["GET"])
def get_v2_run_lineage(run_id: str):
    try:
        result = MiroFishV2Pipeline().lineage(run_id, actor=request_actor())
        return jsonify({"success": True, "data": result})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("v2 run lineage", e)
        return _error("Run lineage could not be loaded.", 500)


@v2_bp.route("/runs/<parent_run_id>/compare/<child_run_id>", methods=["GET"])
def compare_v2_runs(parent_run_id: str, child_run_id: str):
    try:
        result = MiroFishV2Pipeline().compare_runs(
            parent_run_id,
            child_run_id,
            actor=request_actor(),
        )
        return jsonify({"success": True, "data": result})
    except FileNotFoundError:
        return _error("One or both runs were not found.", 404)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("v2 run comparison", e)
        return _error("Run comparison could not be loaded.", 500)


@v2_bp.route("/runs/<run_id>/compare", methods=["GET"])
def compare_v2_run_query(run_id: str):
    other_run_id = (request.args.get("with") or request.args.get("other_run_id") or "").strip()
    if not other_run_id:
        return _error("with or other_run_id is required")
    return compare_v2_runs(run_id, other_run_id)


@v2_bp.route("/runs/<run_id>/decision-model", methods=["GET"])
def get_decision_model(run_id: str):
    """Return proposal/approval status without embedding a calculation trace."""
    try:
        state = MiroFishV2Pipeline().load_state(run_id, actor=request_actor())
        return jsonify(
            {
                "success": True,
                "data": {
                    "run_id": state.run_id,
                    "run_type": state.run_type,
                    "decision_model_version_id": state.decision_model_version_id,
                    "proposal": state.decision_model_proposal,
                    "model": state.decision_model,
                    "analysis": state.decision_analysis_result,
                    "trace_id": state.decision_analysis_trace_id,
                },
            }
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("decision model load", e)
        return _error("Decision model could not be loaded.", 500)


@v2_bp.route("/runs/<run_id>/decision-model/proposals", methods=["POST"])
def propose_decision_model(run_id: str):
    """Store an unapproved model proposal; caller-supplied approvals are stripped."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        model = data.get("model")
        if not isinstance(model, dict):
            return _error("model must be an object.")
        proposed_by = data.get("proposed_by") or "user"
        proposed_by = _bounded_text(
            proposed_by,
            "proposed_by",
            MAX_SUBMITTED_BY_CHARS,
            required=True,
        )
        result = MiroFishV2Pipeline().propose_decision_model(
            run_id,
            model,
            actor=request_actor(),
            proposed_by=proposed_by,
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "proposal": result["proposal"],
                        "run": _state_payload(result["state"]),
                    },
                }
            ),
            201,
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, ValueError) as e:
        _log_private_failure("decision model proposal rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("decision model proposal", e)
        return _error("Decision-model proposal could not be stored.", 500)


@v2_bp.route("/runs/<run_id>/decision-model/confirm", methods=["POST"])
def confirm_decision_model(run_id: str):
    """Apply four explicit human confirmations, then calculate the child run."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        for field in (
            "confirm_actions",
            "confirm_consequence_unit",
            "confirm_distributions",
            "confirm_utility_model",
        ):
            if data.get(field) is not None and not isinstance(data.get(field), bool):
                return _error(f"{field} must be a boolean.")
        proposal_id = data.get("proposal_id")
        if proposal_id is not None and not isinstance(proposal_id, str):
            return _error("proposal_id must be a string.")
        options = _decision_calculation_options(data)
        result = MiroFishV2Pipeline().confirm_decision_model(
            run_id,
            {
                "proposal_id": proposal_id,
                "confirm_actions": data.get("confirm_actions") is True,
                "confirm_consequence_unit": data.get("confirm_consequence_unit") is True,
                "confirm_distributions": data.get("confirm_distributions") is True,
                "confirm_utility_model": data.get("confirm_utility_model") is True,
            },
            actor=request_actor(),
            **options,
        )
        return jsonify(
            {
                "success": True,
                "data": {
                    "analysis": result["analysis"],
                    "run": _state_payload(result["state"]),
                },
            }
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, ValueError) as e:
        _log_private_failure("decision model confirmation rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("decision model confirmation", e)
        return _error("Decision model could not be confirmed.", 500)


@v2_bp.route("/runs/<run_id>/actions/confirm", methods=["POST"])
def confirm_decision_actions(run_id: str):
    """Confirm that the reconstructed paths are real considered management actions."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        action_ids = data.get("action_ids")
        if not isinstance(action_ids, list) or not action_ids:
            return _error("action_ids must be a non-empty array.")
        if len(action_ids) > 8 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 256
            for item in action_ids
        ):
            return _error("action_ids contains an invalid action identifier.")
        confirmed_by = _bounded_text(
            data.get("confirmed_by") or "decision_owner",
            "confirmed_by",
            MAX_SUBMITTED_BY_CHARS,
            required=True,
        )
        state = MiroFishV2Pipeline().confirm_decision_actions(
            run_id,
            action_ids,
            actor=request_actor(),
            confirmed_by=confirmed_by,
        )
        return jsonify({"success": True, "data": {"run": _state_payload(state)}})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        _log_private_failure("decision action confirmation rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("decision action confirmation", e)
        return _error("Decision actions could not be confirmed.", 500)


@v2_bp.route("/runs/<run_id>/execution-owners", methods=["POST"])
def assign_execution_owners(run_id: str):
    """Assign only the named owners required by validation and expansion gates."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        owners = data.get("owners")
        if not isinstance(owners, dict) or not owners:
            return _error("owners must be a non-empty object.")
        if any(key not in {"VALIDATE", "GATE"} for key in owners):
            return _error("owners may only contain VALIDATE and GATE.")
        normalized = {
            key: _bounded_text(value, f"owners.{key}", MAX_SUBMITTED_BY_CHARS, required=True)
            for key, value in owners.items()
        }
        state = MiroFishV2Pipeline().assign_execution_owners(
            run_id,
            normalized,
            actor=request_actor(),
        )
        return jsonify({"success": True, "data": {"run": _state_payload(state)}})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        _log_private_failure("execution owner assignment rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("execution owner assignment", e)
        return _error("Execution owners could not be assigned.", 500)


@v2_bp.route("/runs/<run_id>/decision-analysis/evaluate", methods=["POST"])
def evaluate_decision_analysis(run_id: str):
    """Run bounded exact or seeded Monte Carlo analysis synchronously."""
    try:
        data = request.get_json(silent=True)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        options = _decision_calculation_options(data)
        result = MiroFishV2Pipeline().evaluate_decision_analysis(
            run_id,
            actor=request_actor(),
            **options,
        )
        return jsonify(
            {
                "success": True,
                "data": {
                    "analysis": result["analysis"],
                    "run": _state_payload(result["state"]),
                },
            }
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, ValueError) as e:
        _log_private_failure("decision analysis rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("decision analysis", e)
        return _error("Decision analysis could not be calculated.", 500)


@v2_bp.route("/runs/<run_id>/decision-analysis/waive", methods=["POST"])
def waive_quantitative_decision_analysis(run_id: str):
    """Record an explicit owner choice to finalize without numeric utility claims."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        if data.get("confirm_qualitative_decision") is not True:
            return _error(
                "confirm_qualitative_decision must be true to finalize without quantitative analysis."
            )
        confirmed_by = _bounded_text(
            data.get("confirmed_by") or "decision_owner",
            "confirmed_by",
            MAX_SUBMITTED_BY_CHARS,
            required=True,
        )
        reason = _bounded_text(
            data.get("reason")
            or "The decision owner approved an evidence-backed qualitative decision without a quantitative utility model.",
            "reason",
            1_000,
            required=True,
        )
        state = MiroFishV2Pipeline().waive_quantitative_decision_analysis(
            run_id,
            actor=request_actor(),
            confirmed_by=confirmed_by,
            reason=reason,
        )
        return jsonify({"success": True, "data": {"run": _state_payload(state)}})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        _log_private_failure("qualitative decision confirmation rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("qualitative decision confirmation", e)
        return _error("The qualitative decision could not be finalized.", 500)


@v2_bp.route(
    "/runs/<run_id>/decision-analysis/traces/<trace_id>",
    methods=["GET"],
)
def get_decision_analysis_trace(run_id: str, trace_id: str):
    try:
        trace = MiroFishV2Pipeline().load_decision_trace(
            run_id,
            trace_id,
            actor=request_actor(),
        )
        return jsonify({"success": True, "data": trace})
    except FileNotFoundError:
        return _error("Calculation trace not found.", 404)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("decision trace load", e)
        return _error("Calculation trace could not be loaded.", 500)


@v2_bp.route(
    "/runs/<run_id>/decision-analysis/evidence-proposals",
    methods=["POST"],
)
def propose_decision_evidence_update(run_id: str):
    """Persist a structured observation proposal without changing a distribution."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        observation = data.get("observation")
        if not isinstance(observation, dict):
            return _error("observation must be an object.")
        result = MiroFishV2Pipeline().propose_evidence_update(
            run_id,
            observation,
            actor=request_actor(),
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "proposal": result["proposal"],
                        "run": _state_payload(result["state"]),
                    },
                }
            ),
            201,
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, ValueError) as e:
        _log_private_failure("evidence update proposal rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("evidence update proposal", e)
        return _error("Evidence-update proposal could not be stored.", 500)


@v2_bp.route(
    "/runs/<run_id>/decision-analysis/evidence-proposals/<proposal_id>/confirm",
    methods=["POST"],
)
def confirm_decision_evidence_update(run_id: str, proposal_id: str):
    """Apply only an explicitly confirmed observation and recalculate."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        if not isinstance(data.get("confirmed"), bool):
            return _error("confirmed must be a boolean.")
        result = MiroFishV2Pipeline().confirm_evidence_update(
            run_id,
            proposal_id,
            confirmed=data["confirmed"],
            actor=request_actor(),
        )
        return jsonify(
            {
                "success": True,
                "data": {
                    "outcome": result["outcome"],
                    "run": _state_payload(result["state"]),
                },
            }
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, ValueError) as e:
        _log_private_failure("evidence update confirmation rejection", e)
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("evidence update confirmation", e)
        return _error("Evidence update could not be confirmed.", 500)


@v2_bp.route("/runs/<run_id>/resume", methods=["POST"])
def resume_v2_run(run_id: str):
    try:
        data = request.get_json() or {}
        target_rounds = int(data.get("rounds") or data.get("target_rounds") or 3)
        state = MiroFishV2Pipeline().resume_rounds(run_id, target_rounds)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("v2 resume", e)
        return _error("Decision run could not be resumed.", 500)


@v2_bp.route("/runs/<run_id>/question", methods=["POST"])
@v2_bp.route("/runs/<run_id>/questions", methods=["POST"])
def ask_v2_question(run_id: str):
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        question_value = data.get("question", "")
        if not isinstance(question_value, str):
            return _error("question must be a string.")
        question = _bounded_text(
            question_value,
            "question",
            MAX_FOLLOWUP_QUESTION_CHARS,
            required=True,
        )
        answer = MiroFishV2Pipeline().answer(run_id, question, actor=request_actor())
        return jsonify({"success": True, "data": answer})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, JSONDecodeError) as e:
        _log_private_failure("v2 evidence state validation", e)
        return _error("Decision state is invalid and could not be queried.", 500)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        _log_private_failure("v2 evidence question", e)
        return _error("Evidence question could not be answered.", 500)


@v2_bp.route("/runs/<run_id>/internal-questions", methods=["GET"])
def get_internal_questions(run_id: str):
    try:
        state = MiroFishV2Pipeline().load_state(run_id, actor=request_actor())
        return jsonify(
            {
                "success": True,
                "data": {
                    "questions": [item.model_dump(mode="json") for item in state.internal_questions],
                    "stop_evaluation": (
                        state.stop_evaluation.model_dump(mode="json") if state.stop_evaluation else None
                    ),
                },
            }
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("v2 internal question load", e)
        return _error("Internal questions could not be loaded.", 500)


@v2_bp.route("/runs/<run_id>/internal-questions", methods=["POST"])
def propose_internal_question(run_id: str):
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        question = _bounded_text(
            data.get("question"), "question", MAX_PROPOSED_QUESTION_CHARS, required=True
        )
        category = _bounded_text(data.get("category"), "category", 64, required=True)
        owner_hint = _bounded_text(
            data.get("owner_hint") or "Decision owner",
            "owner_hint",
            MAX_SUBMITTED_BY_CHARS,
            required=True,
        )
        state = MiroFishV2Pipeline().propose_internal_question(
            run_id,
            question,
            category,
            owner_hint=owner_hint,
            actor=request_actor(),
        )
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("v2 internal question proposal", e)
        return _error("Internal question could not be evaluated.", 500)


@v2_bp.route("/runs/<run_id>/answers", methods=["POST"])
def submit_internal_answer(run_id: str):
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        if data.get("question_id") is not None and not isinstance(data.get("question_id"), str):
            return _error("question_id must be a string.")
        if data.get("answer") is not None and not isinstance(data.get("answer"), str):
            return _error("answer must be a string.")
        if data.get("submitted_by") is not None and not isinstance(data.get("submitted_by"), str):
            return _error("submitted_by must be a string.")
        if data.get("interpretation") is not None and not isinstance(data.get("interpretation"), str):
            return _error("interpretation must be a string.")
        if data.get("confidential") is not None and not isinstance(data.get("confidential"), bool):
            return _error("confidential must be a boolean.")
        for field in (
            "visibility",
            "classification",
            "supersedes_evidence_id",
            "retention_policy",
            "retention_until",
        ):
            if data.get(field) is not None and not isinstance(data.get(field), str):
                return _error(f"{field} must be a string.")
        if data.get("visibility") not in {None, "internal", "restricted"}:
            return _error("visibility must be internal or restricted for private answers.")
        if data.get("outbound_external_use") is not None and not isinstance(
            data.get("outbound_external_use"), bool
        ):
            return _error("outbound_external_use must be a boolean.")
        if data.get("outbound_external_use") is True:
            return _error("Internal evidence cannot be marked for outbound external use.")
        if len(data.get("classification") or "") > 100:
            return _error("classification must be at most 100 characters")
        if len(data.get("supersedes_evidence_id") or "") > 256:
            return _error("supersedes_evidence_id must be at most 256 characters")
        if len(data.get("retention_policy") or "") > 100:
            return _error("retention_policy must be at most 100 characters")
        if len(data.get("retention_until") or "") > 64:
            return _error("retention_until must be at most 64 characters")
        question_id = str(data.get("question_id") or "").strip()
        answer = str(data.get("answer") or "").strip()
        if not question_id:
            return _error("question_id is required")
        if not answer:
            return _error("answer is required")
        if len(question_id) > 256:
            return _error("question_id must be at most 256 characters")
        if len(answer) > MAX_INTERNAL_ANSWER_CHARS:
            return _error(f"answer must be at most {MAX_INTERNAL_ANSWER_CHARS} characters")
        submitted_by = str(data.get("submitted_by") or "decision_owner").strip()
        if not submitted_by:
            return _error("submitted_by cannot be empty")
        if len(submitted_by) > MAX_SUBMITTED_BY_CHARS:
            return _error(f"submitted_by must be at most {MAX_SUBMITTED_BY_CHARS} characters")
        confidence_value = data.get("confidence", 0.8)
        if isinstance(confidence_value, bool):
            return _error("confidence must be a finite number from 0 to 1")
        try:
            confidence_value = float(confidence_value)
        except (TypeError, ValueError):
            return _error("confidence must be a finite number from 0 to 1")
        if not math.isfinite(confidence_value) or not 0 <= confidence_value <= 1:
            return _error("confidence must be a finite number from 0 to 1")
        state = MiroFishV2Pipeline().submit_internal_answer(
            run_id,
            question_id,
            answer,
            submitted_by=submitted_by,
            confidential=data.get("confidential", True),
            confidence=confidence_value,
            interpretation=data.get("interpretation"),
            actor=request_actor(),
            visibility=data.get("visibility"),
            classification=data.get("classification"),
            supersedes_evidence_id=data.get("supersedes_evidence_id"),
            retention_policy=data.get("retention_policy") or "inherit_run_policy",
            retention_until=data.get("retention_until"),
        )
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except (ValidationError, JSONDecodeError) as e:
        _log_private_failure("v2 internal evidence state validation", e)
        return _error("Decision state is invalid and could not be updated.", 500)
    except ConfidentialStorageUnavailable:
        return _error(
            "Confidential storage is unavailable until deployment key management is configured.",
            503,
        )
    except ValueError as e:
        status = 409 if "already answered" in str(e) or "has stopped" in str(e) else 400
        return _error(str(e), status)
    except Exception as e:
        _log_private_failure("v2 internal answer", e)
        return _error("Internal evidence could not be recorded.", 500)


@v2_bp.route("/runs/<run_id>/evidence/<evidence_id>/retract", methods=["POST"])
def retract_internal_evidence(run_id: str, evidence_id: str):
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request body must be an object.")
        reason = _bounded_text(data.get("reason"), "reason", 500, required=True)
        state = MiroFishV2Pipeline().retract_internal_evidence(
            run_id,
            evidence_id,
            reason=reason,
            actor=request_actor(),
        )
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except ValueError as e:
        return _error(str(e), 409)
    except Exception as e:
        _log_private_failure("v2 evidence retraction", e)
        return _error("Internal evidence could not be retracted.", 500)


@v2_bp.route("/runs/<run_id>/stop/evaluate", methods=["POST"])
def evaluate_stop(run_id: str):
    try:
        state = MiroFishV2Pipeline().evaluate_stop(run_id, actor=request_actor())
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PublicRunRequiresFork:
        return _fork_required(run_id)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("v2 stop evaluation", e)
        return _error("Stop evaluation failed unexpectedly.", 500)


@v2_bp.route("/runs/<run_id>/audit", methods=["GET"])
def get_audit_trail(run_id: str):
    try:
        state = MiroFishV2Pipeline().load_state(run_id, actor=request_actor())
        return jsonify(
            {"success": True, "data": [item.model_dump(mode="json") for item in state.audit_trail]}
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("v2 audit load", e)
        return _error("Decision audit could not be loaded.", 500)


@v2_bp.route("/runs/<run_id>/report.md", methods=["GET"])
@v2_bp.route("/runs/<run_id>/memo.md", methods=["GET"])
def get_v2_report(run_id: str):
    try:
        # State is the transaction commit point. Loading it also reconciles any
        # interrupted pre-commit artifact write; never serve a memo file that
        # may be newer than the committed case.
        state = MiroFishV2Pipeline().load_state(run_id, actor=request_actor())
        if not state.report:
            return jsonify({"success": False, "error": "report not generated"}), 404
        markdown = state.report.markdown
        return Response(markdown, mimetype="text/markdown; charset=utf-8")
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except PermissionError:
        return _forbidden()
    except Exception as e:
        _log_private_failure("v2 memo load", e)
        return _error("Decision memo could not be loaded.", 500)
