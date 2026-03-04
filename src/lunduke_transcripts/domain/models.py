"""Domain models for transcript pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class VideoRecord:
    """Known metadata for a YouTube video."""

    video_id: str
    video_url: str
    channel_id: str | None
    channel_name: str
    channel_url: str
    title: str
    description: str | None
    published_at: datetime | None
    duration_seconds: int | None


@dataclass
class TranscriptFetchResult:
    """Transcript extraction output for a single video."""

    source_type: str  # manual|auto|unavailable|unknown
    language: str | None
    vtt_text: str | None


@dataclass
class RunOptions:
    """Execution options for one pipeline run."""

    config_path: Path
    from_utc: datetime | None = None
    to_utc: datetime | None = None
    reprocess: bool = False


@dataclass
class RunSummary:
    """Top-level run result for reporting."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    status: str
    videos_seen: int
    videos_new: int
    videos_processed: int
    videos_failed: int
    failures: list[dict[str, str]] = field(default_factory=list)
