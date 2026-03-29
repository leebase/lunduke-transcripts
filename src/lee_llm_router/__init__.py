"""
Lee LLM Router — shared LLM routing kernel.

Extracted from LeeClaw/Meridian for reuse across projects.
"""

__version__ = "0.1.0"

# Core API
from lee_llm_router.client import LLMClient
from lee_llm_router.config import LLMConfig, load_config
from lee_llm_router.providers.base import FailureType, LLMRouterError
from lee_llm_router.response import LLMRequest, LLMResponse, LLMUsage
from lee_llm_router.router import LLMRouter

# Phase 1 abstractions (additive — not required for basic usage)
from lee_llm_router.policy import ProviderChoice, RoutingPolicy, SimpleRoutingPolicy
from lee_llm_router.telemetry import (
    EventSink,
    LocalFileTraceStore,
    RouterEvent,
    TraceStore,
)

__all__ = [
    "__version__",
    # Phase 0
    "LLMRouter",
    "LLMClient",
    "load_config",
    "LLMConfig",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
    "LLMRouterError",
    "FailureType",
    # Phase 1
    "RoutingPolicy",
    "SimpleRoutingPolicy",
    "ProviderChoice",
    "TraceStore",
    "LocalFileTraceStore",
    # Phase 2
    "EventSink",
    "RouterEvent",
]
