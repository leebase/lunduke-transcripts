"""Canonical transcript JSON rendering."""

from __future__ import annotations

import json

from lunduke_transcripts.domain.models import VideoRecord
from lunduke_transcripts.transforms.vtt_parser import Cue


def _timecode_to_seconds(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600.0 + int(minutes) * 60.0 + float(seconds)


def render_transcript_json(
    *,
    video: VideoRecord,
    transcript_source: str,
    language: str | None,
    cues: list[Cue],
    exact_vtt_name: str,
    exact_markdown_name: str,
    exact_text_name: str,
) -> str:
    """Render normalized transcript metadata and segments as JSON."""

    payload = {
        "schema_version": "1",
        "source_id": video.video_id,
        "source_kind": video.source_kind,
        "title": video.title,
        "language": language,
        "transcript_source": transcript_source,
        "video_url": video.video_url,
        "local_path": video.local_path,
        "artifacts": {
            "exact_vtt": exact_vtt_name,
            "exact_markdown": exact_markdown_name,
            "exact_text": exact_text_name,
        },
        "segments": [
            {
                "segment_index": index,
                "start_seconds": round(_timecode_to_seconds(cue.start), 3),
                "end_seconds": round(_timecode_to_seconds(cue.end), 3),
                "start_timestamp": cue.start,
                "end_timestamp": cue.end,
                "text": cue.text,
            }
            for index, cue in enumerate(cues)
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
