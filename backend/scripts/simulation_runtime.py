"""Runtime efficiency helpers shared by simulation scripts."""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional


SUPPORTED_REASONING_MODELS = {"gpt-5.4-mini", "gpt-5.4-nano"}
SUPPORTED_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh"}
MINIMUM_DEFENSIBLE_LLM_SUCCESS_RATE = 0.5


def build_camel_model_config(model: str, reasoning_effort: str) -> Dict[str, str]:
    """Return CAMEL options supported by the selected OpenAI model."""
    model = (model or "").strip().lower()
    effort = (reasoning_effort or "").strip().lower()
    if model in SUPPORTED_REASONING_MODELS and effort in SUPPORTED_REASONING_EFFORTS:
        return {"reasoning_effort": effort}
    return {}


@dataclass
class SimulationHealthState:
    """Process-local accounting for real CAMEL/OpenAI request outcomes."""

    attempted_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    tool_requests_forced_to_none: int = 0
    last_error_type: Optional[str] = None
    last_error_at: Optional[str] = None
    failure_types: Dict[str, int] = field(default_factory=dict)

    def record_attempt(self, *, tool_compatibility_applied: bool = False) -> None:
        self.attempted_requests += 1
        if tool_compatibility_applied:
            self.tool_requests_forced_to_none += 1

    def record_success(self) -> None:
        self.successful_requests += 1

    def record_failure(self, exc: BaseException) -> None:
        self.failed_requests += 1
        error_type = type(exc).__name__
        self.last_error_type = error_type
        self.last_error_at = datetime.now().isoformat()
        self.failure_types[error_type] = self.failure_types.get(error_type, 0) + 1

    @property
    def success_rate(self) -> float:
        if self.attempted_requests <= 0:
            return 1.0
        return self.successful_requests / self.attempted_requests

    @property
    def status(self) -> str:
        if self.attempted_requests <= 0 or self.failed_requests <= 0:
            return "healthy"
        if self.successful_requests > 0 and self.success_rate >= MINIMUM_DEFENSIBLE_LLM_SUCCESS_RATE:
            return "degraded"
        return "failed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "attempted_requests": self.attempted_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 4),
            "minimum_success_rate": MINIMUM_DEFENSIBLE_LLM_SUCCESS_RATE,
            "tool_requests_forced_to_none": self.tool_requests_forced_to_none,
            "last_error_type": self.last_error_type,
            "last_error_at": self.last_error_at,
            "failure_types": dict(sorted(self.failure_types.items())),
        }


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def apply_runtime_overrides(
    config: Dict[str, Any],
    run_mode: str = "full",
    agents_per_hour_min_cap: Optional[int] = None,
    agents_per_hour_max_cap: Optional[int] = None,
    hard_max_active_agents: Optional[int] = None,
) -> Dict[str, Any]:
    """Return a copied config with runtime-only efficiency metadata."""
    adjusted = copy.deepcopy(config)
    runtime = adjusted.setdefault("runtime_efficiency", {})
    runtime["run_mode"] = run_mode

    min_cap = _to_int(agents_per_hour_min_cap)
    max_cap = _to_int(agents_per_hour_max_cap)
    hard_cap = _to_int(hard_max_active_agents)

    if min_cap is not None:
        runtime["agents_per_hour_min_cap"] = min_cap
    if max_cap is not None:
        runtime["agents_per_hour_max_cap"] = max_cap
    if hard_cap is not None:
        runtime["hard_max_active_agents"] = hard_cap

    return adjusted


def apply_active_agent_caps(config: Dict[str, Any], base_min: int, base_max: int) -> tuple[int, int]:
    runtime = config.get("runtime_efficiency", {})
    min_cap = _to_int(runtime.get("agents_per_hour_min_cap"))
    max_cap = _to_int(runtime.get("agents_per_hour_max_cap"))

    if min_cap is not None:
        base_min = min(base_min, min_cap)
    if max_cap is not None:
        base_max = min(base_max, max_cap)

    base_min = max(1, base_min)
    base_max = max(base_min, base_max)
    return base_min, base_max


def clamp_active_agent_target(config: Dict[str, Any], target_count: int) -> int:
    hard_cap = _to_int(config.get("runtime_efficiency", {}).get("hard_max_active_agents"))
    if hard_cap is not None:
        return min(target_count, hard_cap)
    return target_count


def describe_runtime_efficiency(config: Dict[str, Any]) -> str:
    runtime = config.get("runtime_efficiency", {})
    if not runtime:
        return "run_mode=full"
    return json.dumps(runtime, ensure_ascii=False, sort_keys=True)


class ContextGuardError(RuntimeError):
    """Raised before a model call that is likely to exceed the context window."""


class ContextGuardState:
    def __init__(self, token_limit: int, error_limit: int):
        self.token_limit = token_limit
        self.error_limit = error_limit
        self.prevented_requests = 0
        self.api_context_errors = 0
        self.last_estimated_tokens = 0
        self.max_estimated_tokens = 0

    @property
    def total_events(self) -> int:
        return self.prevented_requests + self.api_context_errors

    def record_prevented(self, estimated_tokens: int) -> None:
        self.prevented_requests += 1
        self.last_estimated_tokens = estimated_tokens
        self.max_estimated_tokens = max(self.max_estimated_tokens, estimated_tokens)

    def record_api_error(self, message: str) -> None:
        self.api_context_errors += 1
        match = re.search(r"resulted in (\d+) tokens", message)
        if match:
            tokens = int(match.group(1))
            self.last_estimated_tokens = tokens
            self.max_estimated_tokens = max(self.max_estimated_tokens, tokens)

    def should_stop(self) -> bool:
        return self.error_limit > 0 and self.total_events >= self.error_limit


_context_guard: Optional[ContextGuardState] = None
_context_log_handler_installed = False
_simulation_health = SimulationHealthState()


def reset_simulation_health() -> SimulationHealthState:
    global _simulation_health
    _simulation_health = SimulationHealthState()
    return _simulation_health


def get_simulation_health() -> SimulationHealthState:
    return _simulation_health


def _tool_compatibility_required(model: Any, request_config: Dict[str, Any], tools: Any) -> bool:
    model_value = getattr(model, "value", model)
    normalized_model = str(model_value or "").strip().lower()
    if normalized_model.startswith("modeltype."):
        normalized_model = normalized_model.rsplit(".", 1)[-1].replace("_", "-")
    return bool(
        tools
        and normalized_model in SUPPORTED_REASONING_MODELS
        and str(request_config.get("reasoning_effort") or "").strip().lower() != "none"
    )


def _message_to_text(message: Any) -> str:
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        parts = []
        for key in ("role", "content", "name", "tool_calls", "function_call"):
            if key in message:
                parts.append(str(message.get(key) or ""))
        return "\n".join(parts)

    content = getattr(message, "content", None)
    role = getattr(message, "role", None)
    if content is not None or role is not None:
        return f"{role or ''}\n{content or ''}"

    return str(message)


def estimate_message_tokens(messages: Any) -> int:
    """Conservative token estimate without adding tokenizer dependencies."""
    if not isinstance(messages, (list, tuple)):
        messages = [messages]
    chars = 0
    for message in messages:
        chars += len(_message_to_text(message))
    return max(1, chars // 3)


def install_context_guard(token_limit: int, error_limit: int) -> ContextGuardState:
    """Install a CAMEL/OpenAI preflight guard for oversized chat requests."""
    global _context_guard, _context_log_handler_installed

    _context_guard = ContextGuardState(token_limit=token_limit, error_limit=error_limit)

    try:
        from camel.models.openai_model import OpenAIModel
    except Exception as exc:  # pragma: no cover - depends on optional runtime package
        print(f"[ContextGuard] Unable to patch OpenAIModel: {exc}")
        return _context_guard

    reset_simulation_health()
    current = OpenAIModel._arequest_chat_completion
    if not getattr(current, "_mirofish_context_guard", False):
        async def guarded_request(self, messages, tools=None):
            import copy

            state = _context_guard
            if state and state.token_limit > 0:
                estimated_tokens = estimate_message_tokens(messages)
                if tools:
                    estimated_tokens += estimate_message_tokens(tools)
                if estimated_tokens > state.token_limit:
                    state.record_prevented(estimated_tokens)
                    raise ContextGuardError(
                        "MIROFISH_CONTEXT_GUARD: estimated "
                        f"{estimated_tokens} input tokens exceeds safety limit "
                        f"{state.token_limit}. Reduce active agents, rounds, or compact memory."
                    )
            request_config = copy.deepcopy(self.model_config_dict)
            compatibility_applied = _tool_compatibility_required(
                self.model_type, request_config, tools
            )
            if tools:
                request_config["tools"] = tools
            if compatibility_applied:
                request_config["reasoning_effort"] = "none"
            request_config = self._sanitize_config(request_config)

            health = get_simulation_health()
            health.record_attempt(tool_compatibility_applied=compatibility_applied)
            try:
                response = await self._async_client.chat.completions.create(
                    messages=messages,
                    model=self.model_type,
                    **request_config,
                )
            except Exception as exc:
                health.record_failure(exc)
                raise
            health.record_success()
            return response

        guarded_request._mirofish_context_guard = True
        OpenAIModel._arequest_chat_completion = guarded_request

    current_sync = OpenAIModel._request_chat_completion
    if not getattr(current_sync, "_mirofish_tool_compatibility", False):
        def guarded_sync_request(self, messages, tools=None):
            import copy

            request_config = copy.deepcopy(self.model_config_dict)
            compatibility_applied = _tool_compatibility_required(
                self.model_type, request_config, tools
            )
            if tools:
                request_config["tools"] = tools
            if compatibility_applied:
                request_config["reasoning_effort"] = "none"
            request_config = self._sanitize_config(request_config)

            health = get_simulation_health()
            health.record_attempt(tool_compatibility_applied=compatibility_applied)
            try:
                response = self._client.chat.completions.create(
                    messages=messages,
                    model=self.model_type,
                    **request_config,
                )
            except Exception as exc:
                health.record_failure(exc)
                raise
            health.record_success()
            return response

        guarded_sync_request._mirofish_tool_compatibility = True
        OpenAIModel._request_chat_completion = guarded_sync_request

    if not _context_log_handler_installed:
        class _ContextLogHandler(logging.Handler):
            def emit(self, record):
                state = _context_guard
                if not state:
                    return
                message = record.getMessage()
                if "context_length_exceeded" in message or "Input tokens exceed" in message:
                    state.record_api_error(message)

        logging.getLogger().addHandler(_ContextLogHandler())
        _context_log_handler_installed = True

    print(
        "[ContextGuard] enabled "
        f"(token_limit={token_limit}, error_limit={error_limit})"
    )
    return _context_guard


def get_context_guard_state() -> Optional[ContextGuardState]:
    return _context_guard


def is_context_guard_error(exc: BaseException) -> bool:
    text = str(exc)
    return (
        isinstance(exc, ContextGuardError)
        or "MIROFISH_CONTEXT_GUARD" in text
        or "context_length_exceeded" in text
        or "Input tokens exceed" in text
    )


async def guarded_env_step(
    env: Any,
    actions: Dict[Any, Any],
    log_info: Callable[[str], None],
    context_label: str,
) -> bool:
    """Run env.step and convert context failures into a skipped step."""
    state = get_context_guard_state()
    before_events = state.total_events if state else 0

    try:
        await env.step(actions)
    except Exception as exc:
        if not is_context_guard_error(exc):
            raise
        log_info(f"Context guard skipped {context_label}: {exc}")
        return False

    state = get_context_guard_state()
    if state and state.total_events > before_events:
        delta = state.total_events - before_events
        log_info(
            f"Context guard detected {delta} oversized request(s) during {context_label}; "
            f"last_estimated_tokens={state.last_estimated_tokens}"
        )
        return False

    return True


def context_guard_should_stop() -> bool:
    state = get_context_guard_state()
    return bool(state and state.should_stop())


def context_guard_summary() -> str:
    state = get_context_guard_state()
    if not state:
        return "Context guard disabled"
    return (
        "Context guard summary: "
        f"prevented={state.prevented_requests}, "
        f"api_context_errors={state.api_context_errors}, "
        f"max_estimated_tokens={state.max_estimated_tokens}, "
        f"limit={state.token_limit}"
    )


def simulation_health_summary() -> str:
    health = get_simulation_health().to_dict()
    return (
        "LLM request health: "
        f"status={health['status']}, attempted={health['attempted_requests']}, "
        f"successful={health['successful_requests']}, failed={health['failed_requests']}, "
        f"success_rate={health['success_rate']:.1%}, "
        f"tool_compatibility_overrides={health['tool_requests_forced_to_none']}"
    )
