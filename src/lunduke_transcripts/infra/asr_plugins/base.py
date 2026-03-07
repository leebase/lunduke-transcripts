"""ASR plugin abstractions and shared transcript helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ASRSegment:
    """A single ASR segment with timestamp boundaries in seconds."""

    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class ASRTranscript:
    """Normalized transcript output from an ASR provider plugin."""

    provider: str
    model: str
    language: str | None
    segments: list[ASRSegment]

    def to_vtt(self) -> str:
        """Render transcript segments into canonical WebVTT text."""

        lines = ["WEBVTT", ""]
        for segment in self.segments:
            lines.append(
                f"{_fmt_vtt_time(segment.start_seconds)} --> "
                f"{_fmt_vtt_time(segment.end_seconds)}"
            )
            lines.append(segment.text.strip())
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def to_segments_tsv(self) -> str:
        """Render segments as TSV for audit/debugging."""

        rows = ["start_seconds\tend_seconds\ttext"]
        for segment in self.segments:
            text = segment.text.replace("\t", " ").replace("\n", " ").strip()
            rows.append(
                f"{segment.start_seconds:.3f}\t{segment.end_seconds:.3f}\t{text}"
            )
        return "\n".join(rows) + "\n"


class ASRPlugin(Protocol):
    """Interface contract for pluggable ASR backends."""

    provider_name: str
    model_name: str

    def is_available(self) -> bool:
        """Return whether this plugin can run in current environment."""

    def transcribe(self, audio_path: Path, language: str | None) -> ASRTranscript:
        """Transcribe audio into normalized timestamped transcript."""


def _fmt_vtt_time(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    total_ms = int(round(seconds * 1000.0))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
