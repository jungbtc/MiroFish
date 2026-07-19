"""Minimal authorization boundary for private v2 decision branches.

This module deliberately does not pretend the existing shared API key is an
enterprise identity system. It provides the strongest identity currently
available (a local-workspace actor or a non-reversible credential fingerprint)
and keeps the production blocker visible in every run state.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Optional

from flask import current_app, has_request_context, request

from .schemas import V2RunState


PRODUCTION_AUTH_BLOCKER = (
    "Local or shared API-key access is not user/tenant authentication; "
    "production multi-user deployment requires an external identity provider."
)


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    tenant_id: str = "local-workspace"
    credential_kind: str = "local_workspace"
    production_auth_blocker: str = PRODUCTION_AUTH_BLOCKER


def local_actor() -> ActorContext:
    return ActorContext(actor_id="local-workspace")


def _provided_key() -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("X-MiroFish-Key", "").strip()


def request_actor() -> ActorContext:
    """Resolve the authenticated request to a stable, non-secret actor ID."""
    if not has_request_context():
        return local_actor()
    configured = str(current_app.config.get("V2_API_KEY") or "")
    provided = _provided_key()
    # The app-level before-request guard authenticates this value. Recheck here
    # so this helper remains safe when used in isolated route tests.
    if configured and provided and hmac.compare_digest(provided, configured):
        fingerprint = hashlib.sha256(configured.encode("utf-8")).hexdigest()[:16]
        return ActorContext(
            actor_id=f"shared-key:{fingerprint}",
            credential_kind="shared_api_key_fingerprint",
        )
    return local_actor()


class PublicRunRequiresFork(PermissionError):
    """A private mutation was aimed at a public baseline."""


class RunAuthorization:
    """Authorization interface that can later be backed by a real IdP."""

    @staticmethod
    def assert_can_read(state: V2RunState, actor: Optional[ActorContext] = None) -> None:
        actor = actor or local_actor()
        if state.run_type == "public":
            return
        RunAuthorization._assert_internal_owner(state, actor)

    @staticmethod
    def assert_can_mutate(state: V2RunState, actor: Optional[ActorContext] = None) -> None:
        actor = actor or local_actor()
        if state.run_type != "internal":
            raise PublicRunRequiresFork(
                "Public runs are immutable decision baselines; fork an internal child first."
            )
        RunAuthorization._assert_internal_owner(state, actor)

    @staticmethod
    def assert_can_fork(state: V2RunState, actor: Optional[ActorContext] = None) -> None:
        actor = actor or local_actor()
        if state.run_type != "public":
            raise ValueError("Only a public baseline can be forked into an internal decision run.")
        if state.tenant_id != actor.tenant_id:
            raise PermissionError("The authenticated actor cannot access this run.")

    @staticmethod
    def _assert_internal_owner(state: V2RunState, actor: ActorContext) -> None:
        if state.tenant_id != actor.tenant_id:
            raise PermissionError("The authenticated actor cannot access this run.")
        owners = set(state.owner_actor_ids)
        owners.add(state.owner_actor_id)
        if actor.actor_id in owners:
            return
        # Pre-lineage states had no actor identity. Keep those readable through
        # the already-authenticated shared credential, without granting access
        # to any newly forked branch owned by a different actor.
        if state.schema_version < "2.2" and owners == {"local-workspace"}:
            return
        raise PermissionError("The authenticated actor does not own this internal run.")
