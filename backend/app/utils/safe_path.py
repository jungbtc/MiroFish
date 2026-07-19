"""Safe construction of storage paths from caller-controlled identifiers.

Storage managers should never interpolate an API value directly into a path.
The helpers here deliberately accept a much smaller alphabet than a normal
filename and verify the resolved result remains below the configured root.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Pattern
from urllib.parse import unquote


SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,191}$")


class UnsafePathError(ValueError):
    """Raised when an untrusted identifier cannot safely name stored data."""

    def __init__(self, label: str = "identifier") -> None:
        # This message is safe to return to an API client. Never include the
        # submitted value, root directory, or resolved path here.
        super().__init__(f"Invalid {label}.")
        self.label = label


def validate_identifier(
    value: object,
    *,
    label: str = "identifier",
    pattern: Pattern[str] = SAFE_IDENTIFIER_PATTERN,
) -> str:
    """Validate an opaque storage identifier without normalizing it.

    URL-decoding is checked repeatedly so single- and double-encoded traversal
    strings are rejected even when this function is called outside Flask.
    Percent-encoded *benign* characters are rejected too: storage identifiers
    must arrive in their canonical form and use the explicitly allowed
    character set.
    """

    if not isinstance(value, str) or not value or value != value.strip():
        raise UnsafePathError(label)
    if os.path.isabs(value) or value in {".", ".."}:
        raise UnsafePathError(label)
    if "/" in value or "\\" in value or ".." in value:
        raise UnsafePathError(label)

    decoded = value
    for _ in range(4):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    if decoded != value:
        raise UnsafePathError(label)
    if not pattern.fullmatch(value):
        raise UnsafePathError(label)
    return value


def safe_child_path(
    root: str | os.PathLike[str],
    identifier: object,
    *,
    label: str = "identifier",
    pattern: Pattern[str] = SAFE_IDENTIFIER_PATTERN,
) -> Path:
    """Return a resolved child path proven to remain inside ``root``."""

    safe_identifier = validate_identifier(identifier, label=label, pattern=pattern)
    root_path = Path(root).expanduser().resolve(strict=False)
    candidate = (root_path / safe_identifier).resolve(strict=False)
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:  # Defensive backstop if validation changes later.
        raise UnsafePathError(label) from exc
    if candidate == root_path:
        raise UnsafePathError(label)
    return candidate


def safe_filename_path(
    root: str | os.PathLike[str],
    filename: object,
    *,
    label: str = "filename",
) -> Path:
    """Return a safe single-file path below ``root``."""

    return safe_child_path(root, filename, label=label, pattern=SAFE_FILENAME_PATTERN)
