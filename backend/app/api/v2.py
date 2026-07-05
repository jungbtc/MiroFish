"""MiroFish v2 API routes."""

from __future__ import annotations

import traceback
from flask import Response, jsonify, request

from . import v2_bp
from ..v2.pipeline import MiroFishV2Pipeline
from ..v2.storage import V2Storage
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.v2")


def _state_payload(state):
    return state.model_dump(mode="json")


@v2_bp.route("/run", methods=["POST"])
@v2_bp.route("/research-pack", methods=["POST"])
def run_v2_pipeline():
    """Run the v2 evidence pipeline from multipart files or JSON documents."""
    try:
        pipeline = MiroFishV2Pipeline()
        if request.content_type and "multipart/form-data" in request.content_type:
            files = request.files.getlist("files")
            question = request.form.get("question") or request.form.get("simulation_requirement") or ""
            project_name = request.form.get("project_name") or "MiroFish v2 Run"
            rounds = int(request.form.get("rounds") or 3)
            scenario_theme = request.form.get("scenario_theme") or None
            state = pipeline.run_from_uploads(files, question, project_name, rounds, scenario_theme)
        else:
            data = request.get_json() or {}
            documents = data.get("documents") or []
            question = data.get("question") or data.get("simulation_requirement") or ""
            project_name = data.get("project_name") or "MiroFish v2 Run"
            rounds = int(data.get("rounds") or 3)
            scenario_theme = data.get("scenario_theme")
            state = pipeline.run_from_inline_documents(documents, question, project_name, rounds, scenario_theme)

        return jsonify({"success": True, "data": _state_payload(state)})
    except Exception as e:
        logger.error(f"v2 run failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@v2_bp.route("/demo", methods=["GET", "POST"])
def run_v2_demo():
    try:
        rounds = int(request.args.get("rounds") or 3)
        state = MiroFishV2Pipeline().run_demo(rounds=rounds)
        return jsonify({"success": True, "data": _state_payload(state)})
    except Exception as e:
        logger.error(f"v2 demo failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@v2_bp.route("/runs/<run_id>", methods=["GET"])
def get_v2_run(run_id: str):
    try:
        state = MiroFishV2Pipeline().load_state(run_id)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return jsonify({"success": False, "error": f"Run not found: {run_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@v2_bp.route("/runs/<run_id>/resume", methods=["POST"])
def resume_v2_run(run_id: str):
    try:
        data = request.get_json() or {}
        target_rounds = int(data.get("rounds") or data.get("target_rounds") or 3)
        state = MiroFishV2Pipeline().resume_rounds(run_id, target_rounds)
        return jsonify({"success": True, "data": _state_payload(state)})
    except FileNotFoundError:
        return jsonify({"success": False, "error": f"Run not found: {run_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@v2_bp.route("/runs/<run_id>/question", methods=["POST"])
@v2_bp.route("/runs/<run_id>/questions", methods=["POST"])
def ask_v2_question(run_id: str):
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"success": False, "error": "question is required"}), 400
        answer = MiroFishV2Pipeline().answer(run_id, question)
        return jsonify({"success": True, "data": answer})
    except FileNotFoundError:
        return jsonify({"success": False, "error": f"Run not found: {run_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@v2_bp.route("/runs/<run_id>/report.md", methods=["GET"])
def get_v2_report(run_id: str):
    try:
        path = V2Storage.report_path(run_id)
        if not path.exists():
            state = MiroFishV2Pipeline().load_state(run_id)
            if not state.report:
                return jsonify({"success": False, "error": "report not generated"}), 404
            markdown = state.report.markdown
        else:
            markdown = path.read_text(encoding="utf-8")
        return Response(markdown, mimetype="text/markdown; charset=utf-8")
    except FileNotFoundError:
        return jsonify({"success": False, "error": f"Run not found: {run_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500
