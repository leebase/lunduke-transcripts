"""LLMRouter facade.

Flow: resolve role → policy.choose → build LLMRequest → compress →
      invoke provider → (fallback chain) → record telemetry → trace_store.write → return/raise.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Callable

from lee_llm_router.compression import compress
from lee_llm_router.config import LLMConfig, RoleConfig
from lee_llm_router.policy import RoutingPolicy, SimpleRoutingPolicy
from lee_llm_router.providers.base import FailureType, LLMRouterError, should_retry
from lee_llm_router.providers.registry import get as get_provider
from lee_llm_router.response import LLMRequest, LLMResponse, LLMUsage
from lee_llm_router.telemetry import (
    EventSink,
    LocalFileTraceStore,
    RouterEvent,
    TraceStore,
    record_error,
    record_success,
    start_trace,
)

logger = logging.getLogger("lee_llm_router")


class LLMRouter:
    """High-level router used by consumers and LLMClient alike."""

    def __init__(
        self,
        config: LLMConfig,
        workspace: str | None = None,
        trace_dir: Path | None = None,
        policy: RoutingPolicy | None = None,
        trace_store: TraceStore | None = None,
        event_sink: EventSink | None = None,
        on_token_usage: Callable[[LLMUsage, str, str], None] | None = None,
    ) -> None:
        self.config = config
        self.workspace = workspace
        self._policy: RoutingPolicy = policy or SimpleRoutingPolicy()
        # trace_store wins; trace_dir is a convenience shorthand for LocalFileTraceStore
        self._trace_store: TraceStore = trace_store or LocalFileTraceStore(trace_dir)
        self._event_sink = event_sink
        self._on_token_usage = on_token_usage

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event: str, request_id: str, **data: Any) -> None:
        """Emit a RouterEvent to the EventSink. Swallows all exceptions."""
        if self._event_sink is not None:
            try:
                self._event_sink.emit(
                    RouterEvent(event=event, request_id=request_id, data=data)
                )
            except Exception:
                pass

    def _build_request(
        self,
        role: str,
        messages: list[dict[str, str]],
        role_cfg: RoleConfig,
        overrides: dict[str, Any],
    ) -> LLMRequest:
        return LLMRequest(
            role=role,
            messages=compress(messages),
            model=overrides.get("model", role_cfg.model),
            temperature=float(overrides.get("temperature", role_cfg.temperature)),
            json_mode=bool(overrides.get("json_mode", role_cfg.json_mode)),
            max_tokens=overrides.get("max_tokens", role_cfg.max_tokens),
            timeout=float(overrides.get("timeout", role_cfg.timeout)),
            workspace=self.workspace,
        )

    def _log_policy_choice(
        self, request: LLMRequest, role: str, provider_name: str
    ) -> None:
        logger.info(
            "policy.choice",
            extra={
                "event": "policy.choice",
                "request_id": request.request_id,
                "role": role,
                "provider": provider_name,
                "policy": type(self._policy).__name__,
            },
        )
        self._emit(
            "policy.choice", request.request_id, role=role, provider=provider_name
        )

    def _log_fallback(
        self, request: LLMRequest, role: str, provider_name: str, attempt: int
    ) -> None:
        logger.info(
            "policy.fallback",
            extra={
                "event": "policy.fallback",
                "request_id": request.request_id,
                "role": role,
                "provider": provider_name,
                "attempt": attempt,
            },
        )
        self._emit(
            "policy.fallback",
            request.request_id,
            role=role,
            provider=provider_name,
            attempt=attempt,
        )

    def _call_token_hook(
        self, response: LLMResponse, role: str, provider_name: str
    ) -> None:
        if self._on_token_usage is not None:
            try:
                self._on_token_usage(response.usage, role, provider_name)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Sync completion
    # ------------------------------------------------------------------

    def complete(
        self,
        role: str,
        messages: list[dict[str, str]],
        **overrides: Any,
    ) -> LLMResponse:
        """Execute a completion for the given role, with fallback chain.

        Args:
            role: Role name from config (falls back to default_role if absent).
            messages: Conversation messages in OpenAI format.
            **overrides: Per-call overrides — model, temperature, json_mode,
                         max_tokens, timeout.

        Returns:
            LLMResponse on success.

        Raises:
            LLMRouterError: on any provider failure (after exhausting fallbacks).
        """
        role_cfg = self._resolve_role(role)
        choice = self._policy.choose(role, self.config)
        policy_request_overrides = dict(getattr(choice, "request_overrides", {}))
        request_overrides = {**policy_request_overrides, **overrides}
        request = self._build_request(role, messages, role_cfg, request_overrides)

        self._log_policy_choice(request, role, choice.provider_name)

        providers_to_try = [choice.provider_name] + list(role_cfg.fallback_providers)
        last_error: LLMRouterError | None = None

        for attempt, pname in enumerate(providers_to_try):
            if pname not in self.config.providers:
                continue
            if attempt > 0:
                self._log_fallback(request, role, pname, attempt)

            pcfg = self.config.providers[pname]
            provider = get_provider(pcfg.type)()
            trace = start_trace(request, provider=pcfg.name, attempt=attempt)
            t0 = time.monotonic()

            policy_provider_overrides = dict(getattr(choice, "provider_overrides", {}))
            call_config = {**pcfg.raw, **policy_provider_overrides}

            try:
                response = provider.complete(request, call_config)
                elapsed_ms = (time.monotonic() - t0) * 1000
                record_success(trace, response, elapsed_ms=elapsed_ms)
                self._trace_store.write(trace)
                self._emit(
                    "llm.complete.success",
                    request.request_id,
                    provider=pname,
                    elapsed_ms=elapsed_ms,
                )
                self._call_token_hook(response, role, pname)
                return response
            except LLMRouterError as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                record_error(trace, exc, elapsed_ms=elapsed_ms)
                self._trace_store.write(trace)
                self._emit(
                    "llm.complete.error",
                    request.request_id,
                    provider=pname,
                    failure_type=exc.failure_type.value,
                )
                is_last = attempt == len(providers_to_try) - 1
                if not should_retry(exc) or is_last:
                    raise
                last_error = exc
            except Exception as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                wrapped = LLMRouterError(
                    str(exc), failure_type=FailureType.UNKNOWN, cause=exc
                )
                record_error(trace, wrapped, elapsed_ms=elapsed_ms)
                self._trace_store.write(trace)
                self._emit(
                    "llm.complete.error",
                    request.request_id,
                    provider=pname,
                    failure_type="UNKNOWN",
                )
                raise wrapped from exc

        # Defensive: should only be reached if all providers were skipped
        raise last_error or LLMRouterError(
            "No providers available", failure_type=FailureType.PROVIDER_ERROR
        )

    # ------------------------------------------------------------------
    # Async completion
    # ------------------------------------------------------------------

    async def complete_async(
        self,
        role: str,
        messages: list[dict[str, str]],
        **overrides: Any,
    ) -> LLMResponse:
        """Async completion with fallback chain.

        Providers that implement ``complete_async`` are called natively;
        others are run in a thread via ``asyncio.to_thread``.
        """
        role_cfg = self._resolve_role(role)
        choice = self._policy.choose(role, self.config)
        policy_request_overrides = dict(getattr(choice, "request_overrides", {}))
        request_overrides = {**policy_request_overrides, **overrides}
        request = self._build_request(role, messages, role_cfg, request_overrides)

        self._log_policy_choice(request, role, choice.provider_name)

        providers_to_try = [choice.provider_name] + list(role_cfg.fallback_providers)
        last_error: LLMRouterError | None = None

        for attempt, pname in enumerate(providers_to_try):
            if pname not in self.config.providers:
                continue
            if attempt > 0:
                self._log_fallback(request, role, pname, attempt)

            pcfg = self.config.providers[pname]
            provider = get_provider(pcfg.type)()
            trace = start_trace(request, provider=pcfg.name, attempt=attempt)
            t0 = time.monotonic()
            policy_provider_overrides = dict(getattr(choice, "provider_overrides", {}))
            call_config = {**pcfg.raw, **policy_provider_overrides}

            try:
                if hasattr(provider, "complete_async"):
                    response = await provider.complete_async(request, call_config)
                else:
                    response = await asyncio.to_thread(
                        provider.complete, request, call_config
                    )
                elapsed_ms = (time.monotonic() - t0) * 1000
                record_success(trace, response, elapsed_ms=elapsed_ms)
                self._trace_store.write(trace)
                self._emit(
                    "llm.complete.success",
                    request.request_id,
                    provider=pname,
                    elapsed_ms=elapsed_ms,
                )
                self._call_token_hook(response, role, pname)
                return response
            except LLMRouterError as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                record_error(trace, exc, elapsed_ms=elapsed_ms)
                self._trace_store.write(trace)
                self._emit(
                    "llm.complete.error",
                    request.request_id,
                    provider=pname,
                    failure_type=exc.failure_type.value,
                )
                is_last = attempt == len(providers_to_try) - 1
                if not should_retry(exc) or is_last:
                    raise
                last_error = exc
            except Exception as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                wrapped = LLMRouterError(
                    str(exc), failure_type=FailureType.UNKNOWN, cause=exc
                )
                record_error(trace, wrapped, elapsed_ms=elapsed_ms)
                self._trace_store.write(trace)
                self._emit(
                    "llm.complete.error",
                    request.request_id,
                    provider=pname,
                    failure_type="UNKNOWN",
                )
                raise wrapped from exc

        raise last_error or LLMRouterError(
            "No providers available", failure_type=FailureType.PROVIDER_ERROR
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_role(self, role: str) -> RoleConfig:
        if role in self.config.roles:
            return self.config.roles[role]
        default = self.config.default_role
        if default in self.config.roles:
            return self.config.roles[default]
        raise LLMRouterError(
            f"Role {role!r} not found and default_role {default!r} also missing",
            failure_type=FailureType.PROVIDER_ERROR,
        )
