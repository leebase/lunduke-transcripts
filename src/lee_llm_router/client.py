"""Legacy-compatible LLMClient interface.

Drop-in replacement for LeeClaw's LLMClient.
Wraps LLMRouter so callers can migrate without changing call sites.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lee_llm_router.config import LLMConfig
from lee_llm_router.response import LLMResponse
from lee_llm_router.router import LLMRouter


class LLMClient:
    """Thin wrapper around LLMRouter preserving the LeeClaw call signature."""

    def __init__(
        self,
        config: LLMConfig,
        workspace: str | None = None,
        trace_dir: Path | None = None,
    ) -> None:
        self._router = LLMRouter(config, workspace=workspace, trace_dir=trace_dir)

    def complete(
        self,
        role: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> LLMResponse:
        return self._router.complete(role, messages, **kwargs)
