"""YouTube discovery and transcript acquisition via yt-dlp."""

from __future__ import annotations

import glob
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lunduke_transcripts.domain.models import TranscriptFetchResult, VideoRecord


def _parse_publish_time(entry: dict) -> datetime | None:
    timestamp = entry.get("timestamp")
    if timestamp:
        return datetime.fromtimestamp(int(timestamp), tz=UTC)

    upload_date = entry.get("upload_date")
    if isinstance(upload_date, str) and len(upload_date) == 8:
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


@dataclass
class YtDlpAdapter:
    """Adapter around yt-dlp subprocess calls."""

    binary: str = "yt-dlp"
    timeout_seconds: int = 120
    retries: int = 2
    backoff_seconds: int = 2

    def _run(
        self,
        args: list[str],
        *,
        allow_failure: bool = False,
        retry: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        attempts = self.retries + 1 if retry else 1
        last_error: subprocess.CalledProcessError | None = None
        last_timeout: subprocess.TimeoutExpired | None = None
        for attempt in range(1, attempts + 1):
            try:
                return subprocess.run(
                    [self.binary, *args],
                    check=not allow_failure,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                last_timeout = exc
                if attempt >= attempts:
                    break
                time.sleep(self.backoff_seconds * attempt)
            except subprocess.CalledProcessError as exc:
                last_error = exc
                if attempt >= attempts:
                    raise
                time.sleep(self.backoff_seconds * attempt)
        if last_timeout is not None:
            raise RuntimeError(
                f"yt_dlp_timeout: command exceeded {self.timeout_seconds}s"
            ) from last_timeout
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected yt-dlp execution path")

    def _run_json(self, args: list[str]) -> dict:
        result = self._run(args)
        return json.loads(result.stdout)

    def _video_record_from_entry(
        self,
        entry: dict,
        *,
        channel_url: str,
        default_channel_name: str,
        default_channel_id: str | None,
    ) -> VideoRecord | None:
        video_id = entry.get("id")
        if not video_id:
            return None
        return VideoRecord(
            video_id=str(video_id),
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            channel_id=(
                str(entry.get("channel_id") or default_channel_id)
                if (entry.get("channel_id") or default_channel_id)
                else None
            ),
            channel_name=str(entry.get("channel") or default_channel_name),
            channel_url=channel_url,
            title=str(entry.get("title") or video_id),
            description=(
                str(entry.get("description"))
                if entry.get("description") is not None
                else None
            ),
            published_at=_parse_publish_time(entry),
            duration_seconds=(
                int(entry["duration"]) if entry.get("duration") is not None else None
            ),
        )

    def list_videos(
        self, channel_url: str, max_items: int | None = None
    ) -> list[VideoRecord]:
        """Discover videos from a channel/videos URL."""

        args = ["--flat-playlist", "--dump-single-json"]
        if max_items:
            args.extend(["--playlist-end", str(max_items)])
        args.append(channel_url)
        payload = self._run_json(args)

        channel_name = payload.get("channel") or payload.get("uploader") or "unknown"
        channel_id = payload.get("channel_id")
        entries = payload.get("entries", [])
        videos: list[VideoRecord] = []

        if isinstance(entries, list) and entries:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                video = self._video_record_from_entry(
                    entry,
                    channel_url=channel_url,
                    default_channel_name=str(channel_name),
                    default_channel_id=str(channel_id) if channel_id else None,
                )
                if video is not None:
                    videos.append(video)
            return videos

        # Direct video URLs often return a single video payload with no "entries".
        if isinstance(payload, dict):
            video = self._video_record_from_entry(
                payload,
                channel_url=channel_url,
                default_channel_name=str(channel_name),
                default_channel_id=str(channel_id) if channel_id else None,
            )
            if video is not None:
                videos.append(video)
        return videos

    def fetch_video_metadata(
        self, video_url: str, fallback: VideoRecord
    ) -> VideoRecord:
        """Fetch detailed metadata for a single video."""

        payload = self._run_json(["--dump-single-json", "--skip-download", video_url])
        return VideoRecord(
            video_id=str(payload.get("id") or fallback.video_id),
            video_url=video_url,
            channel_id=(
                str(payload.get("channel_id"))
                if payload.get("channel_id") is not None
                else fallback.channel_id
            ),
            channel_name=str(payload.get("channel") or fallback.channel_name),
            channel_url=fallback.channel_url,
            title=str(payload.get("title") or fallback.title),
            description=(
                str(payload.get("description"))
                if payload.get("description") is not None
                else fallback.description
            ),
            published_at=_parse_publish_time(payload) or fallback.published_at,
            duration_seconds=(
                int(payload["duration"])
                if payload.get("duration") is not None
                else fallback.duration_seconds
            ),
        )

    def probe_subtitle_source(self, video_url: str, language: str) -> str:
        """Best-effort subtitle source classification from yt-dlp output."""

        result = self._run(
            ["--list-subs", "--skip-download", video_url], allow_failure=True
        )
        output = f"{result.stdout}\n{result.stderr}"
        in_manual = False
        in_auto = False
        manual_lang = False
        auto_lang = False
        for raw_line in output.splitlines():
            line = raw_line.strip()
            lower = line.lower()
            if "available subtitles" in lower and "automatic" not in lower:
                in_manual = True
                in_auto = False
                continue
            if "available automatic captions" in lower:
                in_manual = False
                in_auto = True
                continue
            if not line or line.startswith("["):
                continue
            token = line.split()[0] if line else ""
            if token.startswith(language):
                if in_manual:
                    manual_lang = True
                if in_auto:
                    auto_lang = True
        if manual_lang:
            return "manual"
        if auto_lang:
            return "auto"
        return "unknown"

    def fetch_transcript(
        self,
        video_url: str,
        video_id: str,
        language: str,
    ) -> TranscriptFetchResult:
        """Download best available subtitles as VTT text."""

        source_type = self.probe_subtitle_source(video_url, language)
        with tempfile.TemporaryDirectory() as temp_dir:
            out_tmpl = str(Path(temp_dir) / "%(id)s.%(ext)s")
            args = [
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                f"{language}.*",
                "--sub-format",
                "vtt/best",
                "--output",
                out_tmpl,
                video_url,
            ]
            self._run(args, allow_failure=True, retry=True)

            matches = sorted(glob.glob(str(Path(temp_dir) / f"{video_id}*.vtt")))
            if not matches:
                return TranscriptFetchResult(
                    source_type=(
                        "unavailable" if source_type == "unknown" else source_type
                    ),
                    language=language,
                    vtt_text=None,
                )
            transcript_path = Path(matches[0])
            return TranscriptFetchResult(
                source_type=source_type,
                language=language,
                vtt_text=transcript_path.read_text(encoding="utf-8"),
            )
