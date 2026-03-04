"""Provider adapter for transcript cleanup and article generation."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from lunduke_transcripts.transforms.article_writer import (
    ARTICLE_SYSTEM_PROMPT,
    build_article_prompt,
    normalize_article_timestamps,
)
from lunduke_transcripts.transforms.transcript_cleaner import (
    SYSTEM_PROMPT,
    build_cleanup_prompt,
)


class LLMAdapter:
    """LLM adapter with OpenAI and OpenRouter support."""

    def __init__(self, provider: str, model: str, prompt_version: str) -> None:
        self.provider = provider.strip().lower()
        self.model = model
        self.prompt_version = prompt_version

    def _api_key(self) -> str:
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        if self.provider == "openrouter":
            return os.getenv("OPENROUTER_API_KEY", "")
        return ""

    def is_enabled(self) -> bool:
        return bool(self._api_key())

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

        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )
        output_text = getattr(response, "output_text", "") or ""
        if not output_text:
            raise RuntimeError("LLM response contained no text")
        return output_text.strip() + "\n"

    def clean_transcript(self, exact_transcript: str) -> tuple[str, str, str]:
        """Return cleaned transcript text and provenance."""

        cleaned = self._run_prompt(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_cleanup_prompt(exact_transcript),
        )
        return cleaned, self.model, self.prompt_version

    def write_news_article(
        self, exact_markdown_transcript: str, video_title: str | None
    ) -> tuple[str, str, str]:
        """Generate a faithful news-style article with paragraph timestamps."""

        article = self._run_prompt(
            system_prompt=ARTICLE_SYSTEM_PROMPT,
            user_prompt=build_article_prompt(exact_markdown_transcript, video_title),
        )
        article = normalize_article_timestamps(article)
        return article, self.model, self.prompt_version
