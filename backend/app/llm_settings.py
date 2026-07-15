"""Validated model settings shared by API and LLM call sites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


ALLOWED_MODELS = ("gpt-5.4-mini", "gpt-5.4-nano")
SUPPORTED_SIMULATION_MODELS = ALLOWED_MODELS
ALLOWED_REASONING_EFFORTS = ("none", "low", "medium", "high", "xhigh")
SUPPORTED_REASONING_EFFORTS = ALLOWED_REASONING_EFFORTS
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_SIMULATION_MODEL = DEFAULT_MODEL
DEFAULT_REASONING_EFFORT = "low"

REASONING_COMPLETION_TOKEN_MULTIPLIERS = {
    "none": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "xhigh": 6,
}
STRUCTURED_OUTPUT_REASONING_EFFORTS = {
    "none": "none",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "low",
}

_OPENAI_API_BASE_URL = "https://api.openai.com/v1"


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def validate_model(model: Optional[str]) -> str:
    """Return a supported model name or raise ValueError."""
    normalized = _normalized(model) or DEFAULT_MODEL
    if normalized not in ALLOWED_MODELS:
        allowed = ", ".join(ALLOWED_MODELS)
        raise ValueError(f"Unsupported OpenAI model '{normalized}'. Allowed models: {allowed}")
    return normalized


def validate_reasoning_effort(reasoning_effort: Optional[str]) -> str:
    """Return a supported reasoning effort or raise ValueError."""
    normalized = _normalized(reasoning_effort) or DEFAULT_REASONING_EFFORT
    if normalized not in ALLOWED_REASONING_EFFORTS:
        allowed = ", ".join(ALLOWED_REASONING_EFFORTS)
        raise ValueError(
            f"Unsupported reasoning effort '{normalized}'. Allowed reasoning efforts: {allowed}"
        )
    return normalized


def resolve_llm_settings(
    model: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
) -> tuple[str, str]:
    """Validate and return a model/reasoning-effort pair."""
    return validate_model(model), validate_reasoning_effort(reasoning_effort)


def is_official_openai_endpoint(base_url: str | None) -> bool:
    """Return whether a base URL points at OpenAI's public API."""
    return (base_url or "").rstrip("/").lower() == _OPENAI_API_BASE_URL


def uses_completion_token_param(model: str, base_url: str | None) -> bool:
    """GPT-5 Chat Completions uses ``max_completion_tokens``."""
    return is_official_openai_endpoint(base_url) and _normalized(model).startswith("gpt-5")


def reasoning_effort_options(
    model: str,
    base_url: str | None,
    reasoning_effort: str | None,
) -> dict[str, str]:
    """Build optional Chat Completions reasoning arguments."""
    effort = validate_reasoning_effort(reasoning_effort)
    if (
        is_official_openai_endpoint(base_url)
        and validate_model(model) in SUPPORTED_SIMULATION_MODELS
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
        and validate_model(model) in SUPPORTED_SIMULATION_MODELS
    )
    if temperature is not None and not is_configurable_reasoning_model:
        options["temperature"] = temperature
    return options


def reasoning_request_kwargs(
    reasoning_effort: Optional[str],
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Build Chat Completions kwargs for reasoning effort."""
    if model is not None and base_url is not None:
        return reasoning_effort_options(model, base_url, reasoning_effort)
    return {"reasoning_effort": validate_reasoning_effort(reasoning_effort)}


def structured_output_reasoning_effort(reasoning_effort: Optional[str]) -> str:
    """Return an effective reasoning effort for JSON-mode requests."""
    return STRUCTURED_OUTPUT_REASONING_EFFORTS[validate_reasoning_effort(reasoning_effort)]


def temperature_request_kwargs(
    model: Optional[str],
    temperature: Optional[float],
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Build Chat Completions kwargs for models that support custom temperature."""
    normalized_model = validate_model(model)
    if temperature is None:
        return {}
    if normalized_model.startswith("gpt-5") and (
        base_url is None or is_official_openai_endpoint(base_url)
    ):
        return {}
    return {"temperature": temperature}


def token_limit_request_kwargs(
    model: Optional[str],
    reasoning_effort: Optional[str],
    max_tokens: int,
    uses_completion_token_param: bool,
) -> Dict[str, Any]:
    """Build token-limit kwargs, reserving room for reasoning tokens when needed."""
    if not uses_completion_token_param:
        return {"max_tokens": max_tokens}

    normalized_model = validate_model(model)
    normalized_effort = validate_reasoning_effort(reasoning_effort)
    multiplier = (
        REASONING_COMPLETION_TOKEN_MULTIPLIERS[normalized_effort]
        if normalized_model.startswith("gpt-5")
        else 1
    )
    return {"max_completion_tokens": max_tokens * multiplier}


def usage_to_log_dict(response: Any) -> Dict[str, Any]:
    """Extract token usage, including reasoning tokens when available."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return {}

    def get_field(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    result = {
        "prompt_tokens": get_field(usage, "prompt_tokens"),
        "completion_tokens": get_field(usage, "completion_tokens"),
        "total_tokens": get_field(usage, "total_tokens"),
    }

    details = get_field(usage, "completion_tokens_details")
    reasoning_tokens = get_field(details, "reasoning_tokens") if details is not None else None
    if reasoning_tokens is not None:
        result["reasoning_tokens"] = reasoning_tokens

    return {key: value for key, value in result.items() if value is not None}


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
        if resolved_effort not in SUPPORTED_REASONING_EFFORTS:
            resolved_effort = DEFAULT_REASONING_EFFORT
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
