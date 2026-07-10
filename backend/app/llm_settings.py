"""Validated model settings shared by API and LLM call sites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DEFAULT_SIMULATION_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "low"

SUPPORTED_SIMULATION_MODELS = (
    "gpt-5.4-mini",
    "gpt-5.4-nano",
)
SUPPORTED_REASONING_EFFORTS = (
    "none",
    "low",
    "medium",
    "high",
    "xhigh",
)

_OPENAI_API_BASE_URL = "https://api.openai.com/v1"


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def is_official_openai_endpoint(base_url: str | None) -> bool:
    """Return whether a base URL points at OpenAI's public API."""
    return (base_url or "").rstrip("/").lower() == _OPENAI_API_BASE_URL


def uses_completion_token_param(model: str, base_url: str | None) -> bool:
    """GPT-5 Chat Completions uses ``max_completion_tokens``."""
    return is_official_openai_endpoint(base_url) and model.startswith("gpt-5")


def reasoning_effort_options(
    model: str,
    base_url: str | None,
    reasoning_effort: str | None,
) -> dict[str, str]:
    """Build optional Chat Completions reasoning arguments."""
    effort = _normalized(reasoning_effort)
    if (
        is_official_openai_endpoint(base_url)
        and model in SUPPORTED_SIMULATION_MODELS
        and effort in SUPPORTED_REASONING_EFFORTS
    ):
        return {"reasoning_effort": effort}
    return {}


def chat_completion_options(
    model: str,
    base_url: str | None,
    reasoning_effort: str | None,
    *,
    temperature: float | None = None,
) -> dict[str, str | float]:
    """Return model-compatible optional Chat Completions arguments."""
    options: dict[str, str | float] = reasoning_effort_options(
        model,
        base_url,
        reasoning_effort,
    )
    is_configurable_reasoning_model = (
        is_official_openai_endpoint(base_url)
        and model in SUPPORTED_SIMULATION_MODELS
    )
    if temperature is not None and not is_configurable_reasoning_model:
        options["temperature"] = temperature
    return options


@dataclass(frozen=True)
class SimulationLLMSettings:
    """User-selectable model settings for one simulation."""

    model: str = DEFAULT_SIMULATION_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT

    @classmethod
    def from_values(
        cls,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> "SimulationLLMSettings":
        resolved_model = _normalized(model) or DEFAULT_SIMULATION_MODEL
        resolved_effort = _normalized(reasoning_effort) or DEFAULT_REASONING_EFFORT

        if resolved_model not in SUPPORTED_SIMULATION_MODELS:
            allowed = ", ".join(SUPPORTED_SIMULATION_MODELS)
            raise ValueError(
                f"Unsupported simulation model '{resolved_model}'. Choose one of: {allowed}."
            )
        if resolved_effort not in SUPPORTED_REASONING_EFFORTS:
            allowed = ", ".join(SUPPORTED_REASONING_EFFORTS)
            raise ValueError(
                f"Unsupported reasoning effort '{resolved_effort}'. Choose one of: {allowed}."
            )

        return cls(model=resolved_model, reasoning_effort=resolved_effort)

    @classmethod
    def from_runtime_values(
        cls,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> "SimulationLLMSettings":
        """Resolve stored settings while preserving legacy compatible models."""
        resolved_model = _normalized(model) or DEFAULT_SIMULATION_MODEL
        resolved_effort = _normalized(reasoning_effort) or DEFAULT_REASONING_EFFORT
        if resolved_model in SUPPORTED_SIMULATION_MODELS:
            return cls.from_values(resolved_model, resolved_effort)
        return cls(model=resolved_model, reasoning_effort=resolved_effort)

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
        *,
        fallback: "SimulationLLMSettings | None" = None,
    ) -> "SimulationLLMSettings":
        fallback = fallback or cls()
        return cls.from_values(
            data.get("llm_model") or fallback.model,
            data.get("llm_reasoning_effort") or fallback.reasoning_effort,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "llm_model": self.model,
            "llm_reasoning_effort": self.reasoning_effort,
        }
