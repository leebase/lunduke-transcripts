"""Provider adapter for transcript cleanup and article generation."""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from openai import APITimeoutError, OpenAI

from lunduke_transcripts.transforms.article_writer import (
    ARTICLE_SYSTEM_PROMPT,
    build_article_prompt,
    normalize_article_timestamps,
)
from lunduke_transcripts.transforms.transcript_cleaner import (
    SYSTEM_PROMPT,
    build_cleanup_prompt,
)


def _import_router_api(
    router_repo_path: str | None,
) -> tuple[type[Any], Any]:
    try:
        module = importlib.import_module("lee_llm_router")
    except ImportError as exc:
        if router_repo_path:
            src_path = Path(router_repo_path).expanduser() / "src"
            if not src_path.exists():
                raise RuntimeError(
                    f"llm_router_repo_src_not_found: {src_path}"
                ) from exc
            src_str = str(src_path)
            if src_str not in sys.path:
                sys.path.insert(0, src_str)
            module = importlib.import_module("lee_llm_router")
        else:
            raise RuntimeError(
                "llm_router_import_failed: install lee-llm-router or set "
                "LLM_ROUTER_REPO_PATH"
            ) from exc
    return module.LLMRouter, module.load_config


class LLMAdapter:
    """LLM adapter with OpenAI and OpenRouter support."""

    def __init__(
        self,
        provider: str,
        model: str,
        prompt_version: str,
        *,
        timeout_seconds: int = 60,
        retries: int = 2,
        retry_backoff_seconds: int = 2,
        router_enabled: bool = False,
        router_repo_path: str | None = None,
        router_config_path: str | None = None,
        router_trace_dir: str | None = None,
        router_roles: dict[str, str] | None = None,
    ) -> None:
        self.provider = provider.strip().lower()
        self.model = model
        self.prompt_version = prompt_version
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.router_enabled = router_enabled
        self.router_repo_path = router_repo_path
        self.router_config_path = router_config_path
        self.router_trace_dir = router_trace_dir
        self.router_roles = dict(router_roles or {})
        self._router: Any | None = None

    def _api_key(self) -> str:
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        if self.provider == "openrouter":
            return os.getenv("OPENROUTER_API_KEY", "")
        return ""

    def is_enabled(self) -> bool:
        return bool(self._api_key()) or bool(
            self.router_enabled and self.router_config_path and self.router_roles
        )

    def _build_client(self) -> OpenAI:
        if self.provider == "openai":
            base_url = os.getenv("OPENAI_BASE_URL")
            kwargs: dict[str, Any] = {"api_key": self._api_key()}
            if base_url:
                kwargs["base_url"] = base_url
            return OpenAI(**kwargs)

        if self.provider == "openrouter":
            kwargs = {
                "api_key": self._api_key(),
                "base_url": os.getenv(
                    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
                ),
            }
            return OpenAI(**kwargs)

        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    def _extra_headers(self) -> dict[str, str] | None:
        if self.provider != "openrouter":
            return None
        headers: dict[str, str] = {}
        referer = os.getenv("OPENROUTER_HTTP_REFERER")
        app_title = os.getenv("OPENROUTER_APP_TITLE")
        if referer:
            headers["HTTP-Referer"] = referer
        if app_title:
            headers["X-Title"] = app_title
        return headers or None

    def _run_prompt(self, *, system_prompt: str, user_prompt: str) -> str:
        if not self.is_enabled():
            key_name = (
                "OPENAI_API_KEY" if self.provider == "openai" else "OPENROUTER_API_KEY"
            )
            raise RuntimeError(f"{key_name} is not set; cannot run LLM pass")

        client = self._build_client()
        kwargs: dict[str, Any] = {}
        headers = self._extra_headers()
        if headers:
            kwargs["extra_headers"] = headers

        attempts = self.retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                output_text = getattr(response, "output_text", "") or ""
                if not output_text:
                    raise RuntimeError("llm_empty_response")
                return output_text.strip() + "\n"
            except (APITimeoutError, TimeoutError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                time.sleep(self.retry_backoff_seconds * attempt)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= attempts:
                    break
                time.sleep(self.retry_backoff_seconds * attempt)

        if isinstance(last_error, (APITimeoutError, TimeoutError)):
            raise RuntimeError(
                f"llm_timeout: request exceeded {self.timeout_seconds}s"
            ) from last_error
        raise RuntimeError(f"llm_request_failed: {last_error}") from last_error

    def _router_role_for_task(self, task_name: str) -> str | None:
        if not self.router_enabled:
            return None
        role = self.router_roles.get(task_name)
        if not role:
            return None
        return role.strip() or None

    def _load_router(self) -> Any:
        if self._router is not None:
            return self._router
        if not self.router_config_path:
            raise RuntimeError("llm_router_config_path_missing")

        config_path = Path(self.router_config_path).expanduser()
        if not config_path.exists():
            raise RuntimeError(f"llm_router_config_not_found: {config_path}")

        router_cls, load_config = _import_router_api(self.router_repo_path)
        router_config = load_config(config_path)
        router_kwargs: dict[str, Any] = {}
        if self.router_trace_dir:
            router_kwargs["trace_dir"] = Path(self.router_trace_dir).expanduser()
        else:
            router_kwargs["workspace"] = str(Path.cwd())
        self._router = router_cls(router_config, **router_kwargs)
        return self._router

    def _run_router_task(
        self,
        *,
        task_name: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool,
    ) -> tuple[str, str, str] | None:
        role = self._router_role_for_task(task_name)
        if role is None:
            return None

        router = self._load_router()
        try:
            response = router.complete(
                role=role,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                json_mode=json_mode,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"llm_router_request_failed[{task_name}]: {exc}"
            ) from exc

        text = str(getattr(response, "text", "") or "").strip()
        if not text:
            raise RuntimeError(f"llm_router_empty_response[{task_name}]")
        model = str(getattr(response, "model", "") or self.model)
        prompt_version = f"{self.prompt_version}+router:{role}"
        return text + "\n", model, prompt_version

    def run_text_task(
        self, *, task_name: str, system_prompt: str, user_prompt: str
    ) -> tuple[str, str, str]:
        """Run a generic text task and return text plus provenance."""

        routed = self._run_router_task(
            task_name=task_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=False,
        )
        if routed is not None:
            return routed
        text = self._run_prompt(system_prompt=system_prompt, user_prompt=user_prompt)
        return text, self.model, self.prompt_version

    def run_json_task(
        self, *, task_name: str, system_prompt: str, user_prompt: str
    ) -> tuple[dict[str, Any], str, str]:
        """Run a generic JSON task and parse the model output."""

        routed = self._run_router_task(
            task_name=task_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        if routed is not None:
            text, model, prompt_version = routed
        else:
            text, model, prompt_version = self.run_text_task(
                task_name=task_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        try:
            return _parse_json_response(text), model, prompt_version
        except ValueError as exc:
            raise RuntimeError(f"llm_invalid_json[{task_name}]: {exc}") from exc

    def clean_transcript(self, exact_transcript: str) -> tuple[str, str, str]:
        """Return cleaned transcript text and provenance."""

        cleaned, model, prompt_version = self.run_text_task(
            task_name="transcript-cleanup",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_cleanup_prompt(exact_transcript),
        )
        return cleaned, model, prompt_version

    def write_news_article(
        self, exact_markdown_transcript: str, video_title: str | None
    ) -> tuple[str, str, str]:
        """Generate a faithful news-style article with paragraph timestamps."""

        article, model, prompt_version = self.run_text_task(
            task_name="news-article",
            system_prompt=ARTICLE_SYSTEM_PROMPT,
            user_prompt=build_article_prompt(exact_markdown_transcript, video_title),
        )
        article = normalize_article_timestamps(article)
        return article, model, prompt_version


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(?P<body>.*?)```", re.DOTALL)


def _parse_json_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    candidates = [stripped]
    for match in _JSON_BLOCK_RE.finditer(stripped):
        candidates.append(match.group("body").strip())

    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(stripped[first_brace : last_brace + 1])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
        raise ValueError("expected JSON object response")
    raise ValueError("could not parse model response as JSON object")
