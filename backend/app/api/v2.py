"""MiroFish v2 API routes."""

from __future__ import annotations

import math
import re
from json import JSONDecodeError

from flask import Response, jsonify, request
from pydantic import ValidationError

from . import v2_bp
from ..v2.pipeline import MiroFishV2Pipeline
from ..v2.storage import V2Storage
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.v2")

MAX_DOCUMENTS_PER_IMPORT = 32
MAX_DECISION_QUESTION_CHARS = 12_000
MAX_PROJECT_NAME_CHARS = 300
MAX_INTERNAL_ANSWER_CHARS = 50_000
MAX_SUBMITTED_BY_CHARS = 200
MAX_FOLLOWUP_QUESTION_CHARS = 4_000


def _state_payload(state):
    payload = state.model_dump(mode="json")
    for document in payload.get("documents", []):
        metadata = document.get("metadata")
        if isinstance(metadata, dict):
            # Filesystem locations are implementation details and can reveal a
            # host username or deployment layout to API consumers.
            for key in list(metadata):
                if key.lower() == "path" or key.lower().endswith("_path"):
                    metadata.pop(key, None)
    for evidence in payload.get("internal_evidence", []):
        if evidence.get("confidential"):
            evidence["answer"] = "[REDACTED_INTERNAL_EVIDENCE]"
            evidence["answer_redacted"] = True
    return payload


def _error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _log_private_failure(context: str, error: Exception) -> None:
    """Log only the failure class; exception text can contain private case data."""
    logger.error("%s failed (%s)", context, type(error).__name__)


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
                request.form.get("project_name") or "MiroFish v2 Run",
                "project_name",
                MAX_PROJECT_NAME_CHARS,
                required=True,
            )
            rounds = _coerce_rounds(request.form.get("rounds"))
            scenario_theme = request.form.get("scenario_theme") or None
            if not files:
                return _error("At least one Deep Research report is required.")
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
            project_value = data.get("project_name", "MiroFish v2 Run")
            project_name = _bounded_text(
                "MiroFish v2 Run" if project_value is None else project_value,
                "project_name",
                MAX_PROJECT_NAME_CHARS,
                required=True,
            )
            rounds = _coerce_rounds(data.get("rounds"))
            scenario_theme = data.get("scenario_theme")
            if scenario_theme is not None and not isinstance(scenario_theme, str):
                return _error("scenario_theme must be a string.")
            if not documents:
                return _error("At least one structured Deep Research document is required.")
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


@v2_bp.route("/runs/<run_id>", methods=["GET"])
def get_v2_run(run_id: str):
    try:
        state = MiroFishV2Pipeline().load_state(run_id)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except Exception as e:
        _log_private_failure("v2 run load", e)
        return _error("Decision run could not be loaded.", 500)


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
        answer = MiroFishV2Pipeline().answer(run_id, question)
        return jsonify({"success": True, "data": answer})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
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
        state = MiroFishV2Pipeline().load_state(run_id)
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
    except Exception as e:
        _log_private_failure("v2 internal question load", e)
        return _error("Internal questions could not be loaded.", 500)


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
        )
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except (ValidationError, JSONDecodeError) as e:
        _log_private_failure("v2 internal evidence state validation", e)
        return _error("Decision state is invalid and could not be updated.", 500)
    except ValueError as e:
        status = 409 if "already answered" in str(e) or "has stopped" in str(e) else 400
        return _error(str(e), status)
    except Exception as e:
        _log_private_failure("v2 internal answer", e)
        return _error("Internal evidence could not be recorded.", 500)


@v2_bp.route("/runs/<run_id>/stop/evaluate", methods=["POST"])
def evaluate_stop(run_id: str):
    try:
        state = MiroFishV2Pipeline().evaluate_stop(run_id)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except Exception as e:
        _log_private_failure("v2 stop evaluation", e)
        return _error("Stop evaluation failed unexpectedly.", 500)


@v2_bp.route("/runs/<run_id>/audit", methods=["GET"])
def get_audit_trail(run_id: str):
    try:
        state = MiroFishV2Pipeline().load_state(run_id)
        return jsonify(
            {"success": True, "data": [item.model_dump(mode="json") for item in state.audit_trail]}
        )
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
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
        state = MiroFishV2Pipeline().load_state(run_id)
        if not state.report:
            return jsonify({"success": False, "error": "report not generated"}), 404
        markdown = state.report.markdown
        return Response(markdown, mimetype="text/markdown; charset=utf-8")
    except FileNotFoundError:
        return _error(f"Run not found: {run_id}", 404)
    except Exception as e:
        _log_private_failure("v2 memo load", e)
        return _error("Decision memo could not be loaded.", 500)
