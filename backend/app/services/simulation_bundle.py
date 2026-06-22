"""
Portable simulation bundle import/export helpers.

A bundle contains the simulation plus the linked project, graph JSON snapshot,
and latest report folder so a run can be moved between machines.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any

from ..config import Config
from ..models.project import ProjectManager
from .report_agent import ReportManager
from .simulation_manager import SimulationManager


class SimulationBundleError(Exception):
    """Raised when a bundle cannot be imported or exported."""


ID_PATTERNS = {
    "simulation": re.compile(r"^sim_[A-Za-z0-9_-]+$"),
    "project": re.compile(r"^proj_[A-Za-z0-9_-]+$"),
    "report": re.compile(r"^report_[A-Za-z0-9_-]+$"),
    "graph": re.compile(r"^graphiti_[A-Za-z0-9_-]+$"),
}

ALLOWED_TOP_LEVEL = {"bundle_manifest.json", "projects", "simulations", "reports", "graphiti_graphs"}
IGNORED_TOP_LEVEL = {"__MACOSX"}
IGNORED_FILENAMES = {".DS_Store"}


def _safe_component(value: str, kind: str) -> str:
    if not value or not ID_PATTERNS[kind].match(value):
        raise SimulationBundleError(f"Invalid {kind} id: {value}")
    return value


def _uploads_path(*parts: str) -> str:
    return os.path.abspath(os.path.join(Config.UPLOAD_FOLDER, *parts))


def _add_dir_to_zip(zip_file: zipfile.ZipFile, source_dir: str, archive_dir: str) -> int:
    if not os.path.isdir(source_dir):
        return 0

    file_count = 0
    for root, _, files in os.walk(source_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, source_dir)
            archive_path = os.path.join(archive_dir, rel_path).replace(os.sep, "/")
            zip_file.write(file_path, archive_path)
            file_count += 1
    return file_count


def _add_file_to_zip(zip_file: zipfile.ZipFile, source_path: str, archive_path: str) -> int:
    if not os.path.isfile(source_path):
        return 0
    zip_file.write(source_path, archive_path.replace(os.sep, "/"))
    return 1


def create_simulation_bundle(simulation_id: str) -> tuple[str, str]:
    """Create a temporary zip bundle for a simulation and return path + filename."""
    simulation_id = _safe_component(simulation_id, "simulation")

    manager = SimulationManager()
    state = manager.get_simulation(simulation_id)
    if not state:
        raise SimulationBundleError(f"Simulation not found: {simulation_id}")

    project_id = _safe_component(state.project_id, "project") if state.project_id else None
    graph_id = _safe_component(state.graph_id, "graph") if state.graph_id else None

    report = ReportManager.get_report_by_simulation(simulation_id)
    report_id = None
    if report and report.report_id:
        report_id = _safe_component(report.report_id, "report")

    fd, bundle_path = tempfile.mkstemp(prefix=f"{simulation_id}_", suffix=".zip")
    os.close(fd)

    manifest: dict[str, Any] = {
        "bundle_version": 1,
        "exported_at": datetime.now().isoformat(),
        "simulation_id": simulation_id,
        "project_id": project_id,
        "graph_id": graph_id,
        "report_id": report_id,
        "contents": {},
        "missing": [],
    }

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
        sim_dir = _uploads_path("simulations", simulation_id)
        count = _add_dir_to_zip(zip_file, sim_dir, f"simulations/{simulation_id}")
        manifest["contents"]["simulation_files"] = count
        if count == 0:
            manifest["missing"].append(f"simulations/{simulation_id}")

        if project_id:
            project_dir = _uploads_path("projects", project_id)
            count = _add_dir_to_zip(zip_file, project_dir, f"projects/{project_id}")
            manifest["contents"]["project_files"] = count
            if count == 0:
                manifest["missing"].append(f"projects/{project_id}")

        if graph_id:
            graph_file = _uploads_path("graphiti_graphs", f"{graph_id}.json")
            count = _add_file_to_zip(zip_file, graph_file, f"graphiti_graphs/{graph_id}.json")
            manifest["contents"]["graph_files"] = count
            if count == 0:
                manifest["missing"].append(f"graphiti_graphs/{graph_id}.json")

        if report_id:
            report_dir = _uploads_path("reports", report_id)
            count = _add_dir_to_zip(zip_file, report_dir, f"reports/{report_id}")
            manifest["contents"]["report_files"] = count
            if count == 0:
                manifest["missing"].append(f"reports/{report_id}")

        zip_file.writestr(
            "bundle_manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )

    return bundle_path, f"{simulation_id}_mirofish_bundle.zip"


def _validate_zip_member(member_name: str) -> str | None:
    normalized = member_name.replace("\\", "/")
    if not normalized or normalized.startswith("/") or normalized.startswith("../"):
        raise SimulationBundleError(f"Unsafe bundle path: {member_name}")
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        raise SimulationBundleError(f"Unsafe bundle path: {member_name}")
    if any(part == ".." for part in parts):
        raise SimulationBundleError(f"Unsafe bundle path: {member_name}")
    if parts[0] in IGNORED_TOP_LEVEL or parts[-1] in IGNORED_FILENAMES:
        return None
    if parts[0] not in ALLOWED_TOP_LEVEL:
        raise SimulationBundleError(f"Unexpected bundle folder: {parts[0]}")
    return normalized


def _extract_bundle(upload_stream) -> str:
    temp_root = tempfile.mkdtemp(prefix="mirofish_import_")
    archive_path = os.path.join(temp_root, "bundle.zip")
    extract_dir = os.path.join(temp_root, "bundle")
    os.makedirs(extract_dir, exist_ok=True)

    with open(archive_path, "wb") as f:
        shutil.copyfileobj(upload_stream, f)

    if not zipfile.is_zipfile(archive_path):
        shutil.rmtree(temp_root, ignore_errors=True)
        raise SimulationBundleError("Uploaded file is not a valid zip bundle.")

    with zipfile.ZipFile(archive_path, "r") as zip_file:
        for member in zip_file.infolist():
            normalized = _validate_zip_member(member.filename)
            if normalized is None:
                continue
            target_path = os.path.abspath(os.path.join(extract_dir, normalized))
            if not target_path.startswith(os.path.abspath(extract_dir) + os.sep):
                raise SimulationBundleError(f"Unsafe bundle path: {member.filename}")

            if member.is_dir():
                os.makedirs(target_path, exist_ok=True)
                continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with zip_file.open(member, "r") as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    return temp_root


def _copy_dir_bucket(
    source_root: str,
    dest_root: str,
    kind: str,
    conflict_policy: str,
) -> dict[str, list[str]]:
    result = {"imported": [], "skipped": []}
    if not os.path.isdir(source_root):
        return result

    os.makedirs(dest_root, exist_ok=True)
    for item in sorted(os.listdir(source_root)):
        src = os.path.join(source_root, item)
        if not os.path.isdir(src):
            continue
        _safe_component(item, kind)
        dest = os.path.join(dest_root, item)
        if os.path.exists(dest):
            if conflict_policy == "overwrite":
                shutil.rmtree(dest)
            else:
                result["skipped"].append(item)
                continue
        shutil.copytree(src, dest)
        result["imported"].append(item)
    return result


def _copy_graph_bucket(source_root: str, dest_root: str, conflict_policy: str) -> dict[str, list[str]]:
    result = {"imported": [], "skipped": []}
    if not os.path.isdir(source_root):
        return result

    os.makedirs(dest_root, exist_ok=True)
    for filename in sorted(os.listdir(source_root)):
        if not filename.endswith(".json"):
            continue
        graph_id = filename[:-5]
        _safe_component(graph_id, "graph")
        src = os.path.join(source_root, filename)
        if not os.path.isfile(src):
            continue
        dest = os.path.join(dest_root, filename)
        if os.path.exists(dest):
            if conflict_policy == "overwrite":
                os.remove(dest)
            else:
                result["skipped"].append(graph_id)
                continue
        shutil.copy2(src, dest)
        result["imported"].append(graph_id)
    return result


def import_simulation_bundle(upload_stream, conflict_policy: str = "skip") -> dict[str, Any]:
    """Import a portable simulation zip bundle into backend/uploads."""
    if conflict_policy not in {"skip", "overwrite"}:
        raise SimulationBundleError("conflict_policy must be skip or overwrite.")

    temp_root = _extract_bundle(upload_stream)
    extract_dir = os.path.join(temp_root, "bundle")
    try:
        manifest_path = os.path.join(extract_dir, "bundle_manifest.json")
        manifest: dict[str, Any] = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        projects = _copy_dir_bucket(
            os.path.join(extract_dir, "projects"),
            _uploads_path("projects"),
            "project",
            conflict_policy,
        )
        simulations = _copy_dir_bucket(
            os.path.join(extract_dir, "simulations"),
            _uploads_path("simulations"),
            "simulation",
            conflict_policy,
        )
        reports = _copy_dir_bucket(
            os.path.join(extract_dir, "reports"),
            _uploads_path("reports"),
            "report",
            conflict_policy,
        )
        graphs = _copy_graph_bucket(
            os.path.join(extract_dir, "graphiti_graphs"),
            _uploads_path("graphiti_graphs"),
            conflict_policy,
        )

        return {
            "manifest": manifest,
            "primary_simulation_id": manifest.get("simulation_id")
            or (simulations["imported"] or simulations["skipped"] or [None])[0],
            "imported": {
                "projects": projects["imported"],
                "simulations": simulations["imported"],
                "reports": reports["imported"],
                "graphs": graphs["imported"],
            },
            "skipped": {
                "projects": projects["skipped"],
                "simulations": simulations["skipped"],
                "reports": reports["skipped"],
                "graphs": graphs["skipped"],
            },
        }
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
