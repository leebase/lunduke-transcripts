"""Helpers for parsing and rendering WebVTT captions."""

from __future__ import annotations

import re
from dataclasses import dataclass

TIMECODE_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Cue:
    """A single timed subtitle cue."""

    start: str
    end: str
    text: str


def _clean_text(raw: str) -> str:
    cleaned = TAG_RE.sub("", raw)
    cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
    cleaned = WS_RE.sub(" ", cleaned).strip()
    return cleaned


def parse_vtt(vtt_text: str) -> list[Cue]:
    """Parse VTT into cues, stripping formatting and duplicate adjacent lines."""

    cues: list[Cue] = []
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = TIMECODE_RE.search(line)
        if not match:
            i += 1
            continue

        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            candidate = lines[i].strip()
            if "-->" not in candidate:
                text_lines.append(candidate)
            i += 1

        text = _clean_text(" ".join(text_lines))
        if text and (not cues or cues[-1].text != text):
            cues.append(
                Cue(start=match.group("start"), end=match.group("end"), text=text)
            )
        i += 1

    return cues


def render_timestamped_markdown(cues: list[Cue]) -> str:
    """Render readable timestamped transcript lines."""

    return "\n".join(f"[{cue.start[:-4]}] {cue.text}" for cue in cues) + (
        "\n" if cues else ""
    )


def render_plain_text(cues: list[Cue]) -> str:
    """Render plain transcript text without timestamps."""

    return "\n\n".join(cue.text for cue in cues) + ("\n" if cues else "")
