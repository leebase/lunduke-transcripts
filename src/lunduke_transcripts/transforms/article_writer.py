"""Prompt helpers for generating faithful news-style articles."""

from __future__ import annotations

import re

ARTICLE_SYSTEM_PROMPT = (
    "You are a careful news writer. Write a clear, publication-ready article that is "
    "strictly faithful to the provided transcript. Do not invent facts, quotes, "
    "sources, or context not present in the transcript."
)

_START_TS_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s*")
_END_TS_RE = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]\s*$")


def build_article_prompt(
    exact_markdown_transcript: str, video_title: str | None
) -> str:
    """Build the article-generation prompt from exact transcript markdown."""

    title_line = f"Original title: {video_title}\n" if video_title else ""
    return (
        "Transform the transcript into a news journal article.\n"
        "Requirements:\n"
        "- Keep claims and meaning faithful to source content.\n"
        "- Use professional journalistic tone.\n"
        "- Add one timestamp at the END of each paragraph as [HH:MM:SS].\n"
        "- Do not place timestamps at paragraph start.\n"
        "- Do not output bullet lists unless source content is naturally list-like.\n"
        "- Do not mention these instructions.\n\n"
        f"{title_line}"
        "Source transcript (timestamped markdown):\n"
        f"{exact_markdown_transcript.strip()}\n"
    )


def normalize_article_timestamps(article_text: str) -> str:
    """Move leading paragraph timestamps to paragraph endings."""

    paragraphs = article_text.strip().split("\n\n")
    normalized: list[str] = []
    for paragraph in paragraphs:
        text = paragraph.strip()
        if not text:
            continue
        match = _START_TS_RE.match(text)
        if match:
            timestamp = match.group(1)
            text = text[match.end() :].strip()
            if text and not _END_TS_RE.search(text):
                text = f"{text} [{timestamp}]"
        normalized.append(text)

    if not normalized:
        return ""
    return "\n\n".join(normalized) + "\n"
