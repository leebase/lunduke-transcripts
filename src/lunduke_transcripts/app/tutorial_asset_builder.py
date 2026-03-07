"""JSON manifest builders for downstream tutorial assets."""

from __future__ import annotations

import json

from lunduke_transcripts.domain.models import FrameCandidate, VideoRecord


def _fmt_timestamp(seconds: float) -> str:
    total_ms = max(int(round(seconds * 1000.0)), 0)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def render_frame_manifest(
    *,
    video: VideoRecord,
    frames: list[FrameCandidate],
    threshold: float,
    image_format: str,
) -> str:
    """Render frame candidate metadata as JSON."""

    payload = {
        "schema_version": "1",
        "source_id": video.video_id,
        "source_kind": video.source_kind,
        "extraction_method": "ffmpeg_scene_detect",
        "threshold": threshold,
        "image_format": image_format,
        "frames": [
            {
                "frame_index": frame.frame_index,
                "timestamp_seconds": round(frame.timestamp_seconds, 3),
                "timestamp": _fmt_timestamp(frame.timestamp_seconds),
                "image_path": frame.image_path,
                "selection_kind": frame.selection_kind,
                "scene_score": frame.scene_score,
            }
            for frame in frames
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_tutorial_asset_bundle(
    *,
    video: VideoRecord,
    transcript_path: str,
    frame_manifest_path: str | None,
    frame_capture_status: str,
    frame_capture_error: str | None = None,
) -> str:
    """Render the top-level bundle manifest for later renderers."""

    payload = {
        "schema_version": "1",
        "source_id": video.video_id,
        "source_kind": video.source_kind,
        "title": video.title,
        "video_url": video.video_url,
        "local_path": video.local_path,
        "metadata_path": "metadata.json",
        "transcript_path": transcript_path,
        "frame_manifest_path": frame_manifest_path,
        "frame_capture": {
            "status": frame_capture_status,
            "error": frame_capture_error,
        },
        "artifacts": {
            "exact_vtt": "transcript_exact.vtt",
            "exact_markdown": "transcript_exact.md",
            "exact_text": "transcript_exact.txt",
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
