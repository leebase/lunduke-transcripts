"""RoutingPolicy abstraction (Phase 1 — additive).

A RoutingPolicy accepts a role name + config snapshot and returns a
ProviderChoice (which provider to use, plus any overrides). The router
logs every choice as a `policy.choice` event for auditability.

Default: SimpleRoutingPolicy — resolves role.provider, preserving P0 behaviour.
Custom policies (cost-aware, A/B, canary) can be injected via LLMRouter.__init__.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lee_llm_router.config import LLMConfig


@dataclass
class ProviderChoice:
    """Result returned by a RoutingPolicy."""

    provider_name: str
    provider_overrides: dict[str, Any] = field(default_factory=dict)
    request_overrides: dict[str, Any] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)  # legacy alias

    def __post_init__(self) -> None:
        if self.overrides:
            if self.provider_overrides:
                self.provider_overrides = {**self.overrides, **self.provider_overrides}
            else:
                self.provider_overrides = dict(self.overrides)
        # Keep overrides attribute pointing at provider_overrides for legacy readers.
        self.overrides = self.provider_overrides


@runtime_checkable
class RoutingPolicy(Protocol):
    """Interface for provider selection strategies."""

    def choose(self, role: str, config: LLMConfig) -> ProviderChoice:
        """Return the provider to use for this role + config snapshot."""
        ...


class SimpleRoutingPolicy:
    """Default policy: resolve role → use role.provider, no overrides.

    Falls back to config.default_role when the requested role is absent,
    matching the same semantics as LLMRouter._resolve_role().
    """

    def choose(self, role: str, config: LLMConfig) -> ProviderChoice:
        role_cfg = config.roles.get(role) or config.roles.get(config.default_role)
        if role_cfg is None:
            from lee_llm_router.providers.base import FailureType, LLMRouterError

            raise LLMRouterError(
                f"SimpleRoutingPolicy: no role config for {role!r} "
                f"and default_role {config.default_role!r} also missing",
                failure_type=FailureType.PROVIDER_ERROR,
            )
        return ProviderChoice(provider_name=role_cfg.provider)
