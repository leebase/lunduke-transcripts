"""Local media metadata, subtitle, and audio extraction helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from lunduke_transcripts.domain.models import TranscriptFetchResult, VideoRecord
from lunduke_transcripts.infra.youtube_adapter import _parse_timecode_seconds


def _local_source_id(path: Path) -> str:
    hasher = hashlib.sha1()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    digest = hasher.hexdigest()[:16]
    return f"local-{digest}"


def _srt_to_vtt(srt_text: str) -> str:
    lines = ["WEBVTT", ""]
    for raw_line in srt_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped.isdigit():
            continue
        lines.append(line.replace(",", "."))
    return "\n".join(lines).strip() + "\n"


@dataclass
class LocalMediaAdapter:
    """Adapter for probing local media and sidecar subtitle files."""

    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    ffmpeg_timeout_seconds: int = 300

    def probe_video(self, path: str | Path) -> VideoRecord:
        """Build a stable record for a local video file."""

        local_path = Path(path).expanduser().resolve()
        if not local_path.exists():
            raise RuntimeError(f"local_file_missing: {local_path}")
        if not local_path.is_file():
            raise RuntimeError(f"local_path_not_file: {local_path}")

        duration_seconds = self._probe_duration_seconds(local_path)
        return VideoRecord(
            video_id=_local_source_id(local_path),
            title=local_path.stem,
            source_kind="local_file",
            video_url=local_path.as_uri(),
            local_path=str(local_path),
            channel_id=None,
            channel_name=local_path.parent.name or "local-files",
            channel_url=local_path.parent.as_uri(),
            description=None,
            published_at=None,
            duration_seconds=duration_seconds,
        )

    def fetch_video_metadata(
        self, local_path: str | Path, fallback: VideoRecord
    ) -> VideoRecord:
        """Refresh metadata for a known local media file."""

        refreshed = self.probe_video(local_path)
        return VideoRecord(
            video_id=fallback.video_id,
            title=refreshed.title,
            source_kind="local_file",
            video_url=refreshed.video_url,
            local_path=refreshed.local_path,
            channel_id=fallback.channel_id,
            channel_name=refreshed.channel_name,
            channel_url=refreshed.channel_url,
            description=fallback.description,
            published_at=fallback.published_at,
            duration_seconds=refreshed.duration_seconds,
        )

    def fetch_transcript(
        self, local_path: str | Path, language: str | None
    ) -> TranscriptFetchResult:
        """Read a sidecar subtitle file if present."""

        media_path = Path(local_path).expanduser().resolve()
        sidecar = self._find_sidecar(media_path, language)
        if sidecar is None:
            return TranscriptFetchResult(
                source_type="unavailable",
                language=language,
                vtt_text=None,
            )

        text = sidecar.read_text(encoding="utf-8")
        if sidecar.suffix.lower() == ".srt":
            return TranscriptFetchResult(
                source_type="sidecar_srt",
                language=language,
                vtt_text=_srt_to_vtt(text),
                source_details={"subtitle_path": str(sidecar)},
            )
        return TranscriptFetchResult(
            source_type="sidecar_vtt",
            language=language,
            vtt_text=text,
            source_details={"subtitle_path": str(sidecar)},
        )

    def extract_audio_clip(
        self,
        *,
        local_path: str | Path,
        video_id: str,
        output_dir: Path,
        clip_start: str | None,
        clip_end: str | None,
    ) -> Path:
        """Extract audio from a local video file, optionally clipping first."""

        media_path = Path(local_path).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"{video_id}.mp3"
        cmd = [self.ffmpeg_binary, "-y"]
        if clip_start:
            cmd.extend(["-ss", clip_start])
        cmd.extend(["-i", str(media_path)])
        if clip_end:
            start_seconds = _parse_timecode_seconds(clip_start) or 0.0
            end_seconds = _parse_timecode_seconds(clip_end)
            if end_seconds is None:
                raise RuntimeError("invalid_clip_range")
            duration = end_seconds - start_seconds
            if duration <= 0:
                raise RuntimeError("invalid_clip_range")
            cmd.extend(["-t", f"{duration:.3f}"])
        cmd.extend(["-vn", "-acodec", "mp3", str(audio_path)])
        subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True,
            timeout=self.ffmpeg_timeout_seconds,
        )
        return audio_path

    def _find_sidecar(self, media_path: Path, language: str | None) -> Path | None:
        candidates = [media_path.with_suffix(".vtt"), media_path.with_suffix(".srt")]
        if language:
            candidates.extend(
                [
                    media_path.with_suffix(f".{language}.vtt"),
                    media_path.with_suffix(f".{language}.srt"),
                ]
            )
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _probe_duration_seconds(self, media_path: Path) -> int | None:
        cmd = [
            self.ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(media_path),
        ]
        try:
            result = subprocess.run(
                cmd,
                check=True,
                text=True,
                capture_output=True,
                timeout=self.ffmpeg_timeout_seconds,
            )
        except Exception:
            return None
        try:
            payload = json.loads(result.stdout)
            raw_duration = payload["format"]["duration"]
            return int(round(float(raw_duration)))
        except Exception:
            return None
