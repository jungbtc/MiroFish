"""Run mode presets for simulation cost and speed control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RunModePreset:
    mode: str
    label: str
    description: str
    default_platform: str
    max_rounds_cap: Optional[int]
    agents_per_hour_min_cap: Optional[int]
    agents_per_hour_max_cap: Optional[int]
    hard_max_active_agents: Optional[int]
    context_token_limit: int
    context_error_limit: int


RUN_MODE_PRESETS = {
    "preview": RunModePreset(
        mode="preview",
        label="Preview",
        description="Fast first pass with one platform and tight activity caps.",
        default_platform="twitter",
        max_rounds_cap=40,
        agents_per_hour_min_cap=2,
        agents_per_hour_max_cap=8,
        hard_max_active_agents=10,
        context_token_limit=180_000,
        context_error_limit=3,
    ),
    "balanced": RunModePreset(
        mode="balanced",
        label="Balanced",
        description="Dual-platform run with moderate activity caps.",
        default_platform="parallel",
        max_rounds_cap=80,
        agents_per_hour_min_cap=3,
        agents_per_hour_max_cap=14,
        hard_max_active_agents=18,
        context_token_limit=220_000,
        context_error_limit=5,
    ),
    "full": RunModePreset(
        mode="full",
        label="Full Fidelity",
        description="Use the generated scenario as-is, with only the context safety guard.",
        default_platform="parallel",
        max_rounds_cap=None,
        agents_per_hour_min_cap=None,
        agents_per_hour_max_cap=None,
        hard_max_active_agents=None,
        context_token_limit=240_000,
        context_error_limit=6,
    ),
}


def normalize_run_mode(run_mode: Optional[str]) -> str:
    """Return a supported run mode, defaulting to full for backward compatibility."""
    if not run_mode:
        return "full"

    normalized = str(run_mode).strip().lower().replace("-", "_")
    aliases = {
        "fast": "preview",
        "quick": "preview",
        "economy": "preview",
        "standard": "balanced",
        "normal": "balanced",
        "full_fidelity": "full",
        "fullfidelity": "full",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in RUN_MODE_PRESETS:
        raise ValueError(f"Unsupported run_mode: {run_mode}. Options: preview, balanced, full")
    return normalized


def get_run_mode_preset(run_mode: Optional[str]) -> RunModePreset:
    return RUN_MODE_PRESETS[normalize_run_mode(run_mode)]


def resolve_run_mode(
    run_mode: Optional[str],
    platform: Optional[str],
    max_rounds: Optional[int],
) -> dict:
    """Resolve request values into the effective runtime settings."""
    preset = get_run_mode_preset(run_mode)
    effective_platform = platform or preset.default_platform
    effective_max_rounds = max_rounds

    if preset.max_rounds_cap is not None:
        if effective_max_rounds is None:
            effective_max_rounds = preset.max_rounds_cap
        else:
            effective_max_rounds = min(effective_max_rounds, preset.max_rounds_cap)

    return {
        "run_mode": preset.mode,
        "run_mode_label": preset.label,
        "run_mode_description": preset.description,
        "platform": effective_platform,
        "max_rounds": effective_max_rounds,
        "agents_per_hour_min_cap": preset.agents_per_hour_min_cap,
        "agents_per_hour_max_cap": preset.agents_per_hour_max_cap,
        "hard_max_active_agents": preset.hard_max_active_agents,
        "context_token_limit": preset.context_token_limit,
        "context_error_limit": preset.context_error_limit,
    }
