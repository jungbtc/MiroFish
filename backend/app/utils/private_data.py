"""Central outbound-use policy for confidential decision evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


PRIVATE_CONTAINER_KEYS = {
    "confidential_evidence",
    "internal_answers",
    "internal_evidence",
    "private_answers",
    "private_evidence",
    "restricted_evidence",
}
PRIVATE_CLASSIFICATIONS = {
    "confidential",
    "internal",
    "private",
    "restricted",
    "secret",
    "strictly_confidential",
}
NEVER_PRIVATE_SINKS = {
    "debug_log",
    "external_research",
    "report_agent_log",
    "web_search",
}


class PrivateDataPolicyError(ValueError):
    """Raised before private material reaches a disallowed sink."""

    def __init__(self, sink: str) -> None:
        # Do not include payload values in the public-safe message.
        super().__init__(f"Confidential data is not permitted for {sink}.")
        self.sink = sink


def _mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, Mapping) else None
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, Mapping) else None
    return None


def contains_private_data(payload: Any, *, _seen: set[int] | None = None) -> bool:
    """Conservatively identify explicitly classified private material.

    Detection is metadata based: ordinary prose containing the word
    "confidential" is not treated as secret, while evidence objects marked
    confidential/internal/restricted or prohibited from outbound use are.
    """

    if payload is None or isinstance(payload, (str, bytes, int, float, bool)):
        return False

    seen = _seen if _seen is not None else set()
    identity = id(payload)
    if identity in seen:
        return False
    seen.add(identity)

    mapping = _mapping(payload)
    if mapping is not None:
        lowered = {str(key).strip().lower(): value for key, value in mapping.items()}
        if lowered.get("confidential") is True:
            return True
        if lowered.get("outbound_external_use") is False and any(
            key in lowered for key in ("answer", "evidence_id", "observation", "value")
        ):
            return True
        for key in ("classification", "visibility", "data_classification"):
            classification = lowered.get(key)
            if (
                isinstance(classification, str)
                and classification.strip().lower() in PRIVATE_CLASSIFICATIONS
            ):
                return True
        if any(lowered.get(key) not in (None, "", [], {}, ()) for key in PRIVATE_CONTAINER_KEYS):
            return True
        return any(contains_private_data(value, _seen=seen) for value in mapping.values())

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return any(contains_private_data(item, _seen=seen) for item in payload)
    return False


def assert_private_data_allowed(
    payload: Any,
    *,
    sink: str,
    explicitly_permitted: bool = False,
) -> None:
    """Reject private payloads unless a non-public sink was explicitly allowed."""

    normalized_sink = (sink or "outbound operation").strip().lower().replace(" ", "_")
    if not contains_private_data(payload):
        return
    if explicitly_permitted and normalized_sink not in NEVER_PRIVATE_SINKS:
        return
    raise PrivateDataPolicyError(normalized_sink.replace("_", " "))


def safe_debug_payload(payload: Any) -> Any:
    """Return a fixed marker instead of serializing private request material."""

    try:
        assert_private_data_allowed(payload, sink="debug_log")
    except PrivateDataPolicyError:
        return "[REDACTED_PRIVATE_PAYLOAD]"
    return payload
