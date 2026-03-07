"""Domain models for transcript and artifact pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class VideoRecord:
    """Known metadata for a source video."""

    video_id: str
    title: str
    source_kind: str = "youtube_video"
    video_url: str | None = None
    local_path: str | None = None
    channel_id: str | None = None
    channel_name: str = "unknown"
    channel_url: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True)
class FrameCandidate:
    """A captured frame candidate stored as a file artifact."""

    frame_index: int
    timestamp_seconds: float
    image_path: str
    selection_kind: str = "scene_candidate"
    scene_score: float | None = None


@dataclass
class TranscriptFetchResult:
    """Transcript extraction output for a single video."""

    source_type: str  # manual|auto|unavailable|unknown
    language: str | None
    vtt_text: str | None
    segments_tsv: str | None = None
    source_details: dict[str, str] | None = None


@dataclass
class RunOptions:
    """Execution options for one pipeline run."""

    config_path: Path
    from_utc: datetime | None = None
    to_utc: datetime | None = None
    reprocess: bool = False
    generate_article: bool = False


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


@dataclass
class TutorialSummary:
    """Top-level result for tutorial generation from one bundle."""

    status: str
    tutorial_dir: Path
    manifest_path: Path
    human_outline_approved: bool
    publish_eligible: bool
    reused_cached_outputs: bool = False
    review_cycles: int = 0
    failures: list[str] = field(default_factory=list)


@dataclass
class RenderSummary:
    """Top-level result for one tutorial render target."""

    status: str
    tutorial_dir: Path
    render_manifest_path: Path
    target: str
    html_path: Path | None = None
    output_path: Path | None = None
    failures: list[str] = field(default_factory=list)
