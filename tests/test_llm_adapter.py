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


def test_run_json_task_parses_fenced_json(monkeypatch) -> None:
    adapter = LLMAdapter(
        provider="openai",
        model="gpt-4.1-mini",
        prompt_version="v1",
        timeout_seconds=1,
        retries=0,
        retry_backoff_seconds=0,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        adapter,
        "_build_client",
        lambda: types.SimpleNamespace(
            responses=types.SimpleNamespace(
                create=lambda *args, **kwargs: types.SimpleNamespace(
                    output_text='```json\n{"ok": true}\n```'
                )
            )
        ),
    )

    payload, _, _ = adapter.run_json_task(
        task_name="tutorial.review",
        system_prompt="system",
        user_prompt="user",
    )
    assert payload == {"ok": True}


def test_routed_tutorial_writer_uses_router(monkeypatch, tmp_path) -> None:
    class _FakeRouter:
        def __init__(self, config, **kwargs) -> None:  # noqa: ANN003
            self.config = config
            self.kwargs = kwargs

        def complete(self, role, messages, **overrides):  # noqa: ANN001, ANN003
            assert role == "tutorial_writer"
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert overrides["json_mode"] is False
            return types.SimpleNamespace(text="ghostwritten output", model="gpt-5.4")

    config_path = tmp_path / "router.yaml"
    config_path.write_text("llm:\n  default_role: x\n  providers: {}\n  roles: {}\n")
    monkeypatch.setattr(
        "lunduke_transcripts.infra.llm_adapter._import_router_api",
        lambda repo_path: (_FakeRouter, lambda path: {"path": str(path)}),
    )
    adapter = LLMAdapter(
        provider="openrouter",
        model="openai/gpt-4.1-mini",
        prompt_version="v1",
        timeout_seconds=1,
        retries=0,
        retry_backoff_seconds=0,
        router_enabled=True,
        router_config_path=str(config_path),
        router_roles={"tutorial.writer": "tutorial_writer"},
    )

    text, model, prompt_version = adapter.run_text_task(
        task_name="tutorial.writer",
        system_prompt="system",
        user_prompt="user",
    )

    assert text.strip() == "ghostwritten output"
    assert model == "gpt-5.4"
    assert prompt_version == "v1+router:tutorial_writer"


def test_routed_json_task_uses_router_json_mode(monkeypatch, tmp_path) -> None:
    class _FakeRouter:
        def __init__(self, config, **kwargs) -> None:  # noqa: ANN003
            self.config = config
            self.kwargs = kwargs

        def complete(self, role, messages, **overrides):  # noqa: ANN001, ANN003
            assert role == "tutorial_reviewer"
            assert overrides["json_mode"] is True
            return types.SimpleNamespace(text='{"ok": true}', model="gpt-5.4")

    config_path = tmp_path / "router.yaml"
    config_path.write_text("llm:\n  default_role: x\n  providers: {}\n  roles: {}\n")
    monkeypatch.setattr(
        "lunduke_transcripts.infra.llm_adapter._import_router_api",
        lambda repo_path: (_FakeRouter, lambda path: {"path": str(path)}),
    )
    adapter = LLMAdapter(
        provider="openrouter",
        model="openai/gpt-4.1-mini",
        prompt_version="v1",
        timeout_seconds=1,
        retries=0,
        retry_backoff_seconds=0,
        router_enabled=True,
        router_config_path=str(config_path),
        router_roles={"tutorial.technical-review": "tutorial_reviewer"},
    )

    payload, model, prompt_version = adapter.run_json_task(
        task_name="tutorial.technical-review",
        system_prompt="system",
        user_prompt="user",
    )

    assert payload == {"ok": True}
    assert model == "gpt-5.4"
    assert prompt_version == "v1+router:tutorial_reviewer"
