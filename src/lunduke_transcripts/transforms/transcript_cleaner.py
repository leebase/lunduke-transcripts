"""Prompt construction and cleanup rules for transcript polishing."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You clean transcript text for readability without changing meaning. "
    "Do not summarize, add facts, remove substantive content, or invent details. "
    "Preserve named entities, numbers, dates, and claims. "
    "Output only the cleaned transcript body."
)


def build_cleanup_prompt(exact_transcript_text: str) -> str:
    """Build deterministic user prompt for cleanup pass."""

    return (
        "Clean the following transcript.\n"
        "Allowed edits: punctuation, sentence boundaries, paragraphing, "
        "and minimal filler cleanup.\n"
        "Disallowed edits: summarization, content deletion that changes "
        "meaning, factual changes.\n\n"
        "Transcript:\n"
        f"{exact_transcript_text.strip()}\n"
    )
