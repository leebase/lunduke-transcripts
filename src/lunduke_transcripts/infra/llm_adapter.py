"""Provider adapter for transcript cleanup."""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

from lunduke_transcripts.transforms.transcript_cleaner import (
    SYSTEM_PROMPT,
    build_cleanup_prompt,
)


@dataclass
class CleanupRequest:
    """Payload for cleanup generation."""

    model: str
    prompt_version: str
    exact_transcript: str


class LLMAdapter:
    """LLM cleanup adapter (OpenAI first, swappable interface)."""

    def __init__(self, provider: str, model: str, prompt_version: str) -> None:
        self.provider = provider
        self.model = model
        self.prompt_version = prompt_version

    def is_enabled(self) -> bool:
        if self.provider != "openai":
            return False
        return bool(os.getenv("OPENAI_API_KEY"))

    def clean_transcript(self, exact_transcript: str) -> tuple[str, str, str]:
        """Return cleaned transcript and provenance fields."""

        if self.provider != "openai":
            raise RuntimeError(f"Unsupported LLM provider: {self.provider}")
        if not self.is_enabled():
            raise RuntimeError("OPENAI_API_KEY is not set; cannot run cleanup pass")

        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_cleanup_prompt(exact_transcript)},
            ],
        )

        output_text = getattr(response, "output_text", "") or ""
        if not output_text:
            raise RuntimeError("Cleanup response contained no text")
        return output_text.strip() + "\n", self.model, self.prompt_version
