"""Runtime efficiency helpers shared by simulation scripts."""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any, Callable, Dict, Optional


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

    current = OpenAIModel._arequest_chat_completion
    if not getattr(current, "_mirofish_context_guard", False):
        original = current

        async def guarded_request(self, messages, tools=None):
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
            return await original(self, messages, tools)

        guarded_request._mirofish_context_guard = True
        OpenAIModel._arequest_chat_completion = guarded_request

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
