from __future__ import annotations

import types

import pytest

from lunduke_transcripts.infra.llm_adapter import LLMAdapter


class _FakeResponses:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.calls = 0

    def create(self, *args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        self.calls += 1
        if self.mode == "retry-then-pass" and self.calls == 1:
            raise TimeoutError("transient timeout")
        if self.mode == "always-timeout":
            raise TimeoutError("persistent timeout")
        return types.SimpleNamespace(output_text="cleaned output")


class _FakeClient:
    def __init__(self, mode: str) -> None:
        self.responses = _FakeResponses(mode)


def test_llm_retry_then_success(monkeypatch) -> None:
    adapter = LLMAdapter(
        provider="openai",
        model="gpt-4.1-mini",
        prompt_version="v1",
        timeout_seconds=1,
        retries=1,
        retry_backoff_seconds=0,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        adapter, "_build_client", lambda: _FakeClient("retry-then-pass")
    )
    cleaned, _, _ = adapter.clean_transcript("hello world")
    assert cleaned.strip() == "cleaned output"


def test_llm_timeout_exhaustion_raises(monkeypatch) -> None:
    adapter = LLMAdapter(
        provider="openai",
        model="gpt-4.1-mini",
        prompt_version="v1",
        timeout_seconds=1,
        retries=1,
        retry_backoff_seconds=0,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(adapter, "_build_client", lambda: _FakeClient("always-timeout"))
    with pytest.raises(RuntimeError, match="llm_timeout"):
        adapter.clean_transcript("hello world")
