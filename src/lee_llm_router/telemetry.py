"""Structured logger + JSON trace file writers.

Event names follow the Meridian convention:
    llm.complete.start
    llm.complete.success
    llm.complete.error
    policy.choice

Trace files are written by a TraceStore. The default LocalFileTraceStore writes to:
    <workspace>/.agentleeops/traces/YYYYMMDD/<request_id>-<attempt>-<provider>.json
    .lee-llm-router/traces/YYYYMMDD/<request_id>-<attempt>-<provider>.json
    <trace_dir>/YYYYMMDD/<request_id>-<attempt>-<provider>.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import field as _field
from typing import Any, Protocol, runtime_checkable

from lee_llm_router.providers.base import LLMRouterError
from lee_llm_router.response import LLMRequest, LLMResponse

logger = logging.getLogger("lee_llm_router")


@dataclass
class TraceRecord:
    """Mutable record built up across the request lifecycle."""

    request_id: str
    role: str
    provider: str
    model: str
    started_at: str
    attempt: int = 0
    work_package_id: str | None = None
    workspace: str | None = None
    elapsed_ms: float | None = None
    failure_type: str | None = None
    error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# EventSink abstraction (Phase 2)
# ---------------------------------------------------------------------------


@dataclass
class RouterEvent:
    """Emitted at every significant step; consumable by external SessionLoggers."""

    event: str  # e.g. "llm.complete.start", "policy.choice"
    request_id: str
    data: dict[str, Any] = _field(default_factory=dict)


@runtime_checkable
class EventSink(Protocol):
    """Optional hook — implement to integrate with LeeClaw / Meridian event systems."""

    def emit(self, event: RouterEvent) -> None:
        """Receive a router event. Must not raise."""
        ...


# ---------------------------------------------------------------------------
# TraceStore abstraction (Phase 1)
# ---------------------------------------------------------------------------


@runtime_checkable
class TraceStore(Protocol):
    """Pluggable sink for trace records. Default: LocalFileTraceStore."""

    def write(self, trace: TraceRecord) -> None:
        """Persist a completed (or failed) trace record."""
        ...


class LocalFileTraceStore:
    """Writes trace records as JSON files to the local filesystem."""

    def __init__(self, trace_dir: Path | None = None) -> None:
        self._trace_dir = trace_dir

    def write(self, trace: TraceRecord) -> Path:
        return _write_trace(trace, _resolve_trace_dir(trace.workspace, self._trace_dir))


# ---------------------------------------------------------------------------
# Logging helpers (do NOT write files — file writing is TraceStore's job)
# ---------------------------------------------------------------------------


def start_trace(
    request: LLMRequest, provider: str = "", attempt: int = 0
) -> TraceRecord:
    """Create a TraceRecord and emit llm.complete.start."""
    trace = TraceRecord(
        request_id=request.request_id,
        role=request.role,
        provider=provider,
        attempt=attempt,
        model=request.model,
        started_at=datetime.now(timezone.utc).isoformat(),
        work_package_id=request.work_package_id,
        workspace=request.workspace,
    )
    logger.info(
        "llm.complete.start",
        extra={
            "event": "llm.complete.start",
            "request_id": trace.request_id,
            "role": trace.role,
            "provider": trace.provider,
            "attempt": trace.attempt,
            "model": trace.model,
            "work_package_id": trace.work_package_id,
        },
    )
    return trace


def record_success(
    trace: TraceRecord,
    response: LLMResponse,
    elapsed_ms: float = 0.0,
) -> None:
    """Update trace fields and emit llm.complete.success. File written by TraceStore."""
    trace.elapsed_ms = elapsed_ms
    trace.usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    logger.info(
        "llm.complete.success",
        extra={
            "event": "llm.complete.success",
            "request_id": trace.request_id,
            "role": trace.role,
            "provider": trace.provider,
            "attempt": trace.attempt,
            "model": trace.model,
            "elapsed_ms": elapsed_ms,
            "usage": trace.usage,
        },
    )


def record_error(
    trace: TraceRecord,
    error: LLMRouterError,
    elapsed_ms: float = 0.0,
) -> None:
    """Update trace fields and emit llm.complete.error. File written by TraceStore."""
    trace.elapsed_ms = elapsed_ms
    trace.failure_type = error.failure_type.value
    trace.error = str(error)
    logger.error(
        "llm.complete.error",
        extra={
            "event": "llm.complete.error",
            "request_id": trace.request_id,
            "role": trace.role,
            "provider": trace.provider,
            "attempt": trace.attempt,
            "model": trace.model,
            "elapsed_ms": elapsed_ms,
            "failure_type": trace.failure_type,
            "error": trace.error,
        },
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_trace_dir(workspace: str | None, override: Path | None = None) -> Path:
    if override is not None:
        return override
    if workspace:
        return Path(workspace) / ".agentleeops" / "traces"
    return Path(".lee-llm-router") / "traces"


def _write_trace(trace: TraceRecord, trace_dir: Path) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = trace_dir / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    provider_slug = (trace.provider or "provider").replace("/", "_")
    trace_path = out_dir / f"{trace.request_id}-{trace.attempt}-{provider_slug}.json"
    trace_path.write_text(json.dumps(asdict(trace), indent=2))
    return trace_path
