"""End-to-end pipeline orchestration."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from lunduke_transcripts.config import Config
from lunduke_transcripts.domain.models import RunOptions, RunSummary
from lunduke_transcripts.infra.llm_adapter import LLMAdapter
from lunduke_transcripts.infra.storage import Storage
from lunduke_transcripts.infra.youtube_adapter import YtDlpAdapter
from lunduke_transcripts.transforms.vtt_parser import (
    parse_vtt,
    render_plain_text,
    render_timestamped_markdown,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _in_range(
    published_at: datetime | None, from_utc: datetime | None, to_utc: datetime | None
) -> bool:
    if from_utc is None and to_utc is None:
        return True
    if published_at is None:
        return False
    if from_utc and published_at < from_utc:
        return False
    if to_utc and published_at > to_utc:
        return False
    return True


class Orchestrator:
    """Coordinates discovery, extraction, cleanup, and persistence."""

    def __init__(
        self,
        config: Config,
        storage: Storage,
        youtube: YtDlpAdapter,
        llm: LLMAdapter,
    ) -> None:
        self.config = config
        self.storage = storage
        self.youtube = youtube
        self.llm = llm

    def run(self, options: RunOptions) -> RunSummary:
        self.storage.initialize()
        run_id, started_at = self.storage.start_run(options.from_utc, options.to_utc)
        failures: list[dict[str, str]] = []
        videos_seen = 0

        try:
            for channel in self.config.channels:
                discovered = self.youtube.list_videos(
                    channel.url, max_items=self.config.app.max_videos_per_channel
                )
                videos_seen += len(discovered)
                for video in discovered:
                    self.storage.upsert_video(video)
                self.storage.log_run_item(
                    run_id,
                    video_id=None,
                    step="discover",
                    status="ok",
                    message=f"{channel.name}: discovered={len(discovered)}",
                )

            candidates = self.storage.list_candidates(
                filter_from=options.from_utc,
                filter_to=options.to_utc,
                reprocess=options.reprocess,
            )
            videos_new = 0
            videos_processed = 0
            videos_failed = 0

            lang_by_channel_url = {
                c.url: (c.language or self.config.app.default_language)
                for c in self.config.channels
            }

            for candidate in candidates:
                try:
                    detailed = self.youtube.fetch_video_metadata(
                        candidate.video_url, fallback=candidate
                    )
                    self.storage.upsert_video(detailed)
                    if not _in_range(
                        detailed.published_at, options.from_utc, options.to_utc
                    ):
                        self.storage.log_run_item(
                            run_id,
                            video_id=detailed.video_id,
                            step="filter",
                            status="skipped",
                            message="outside_date_range_or_missing_publish_time",
                        )
                        continue
                    videos_new += 1
                    language = lang_by_channel_url.get(
                        detailed.channel_url, self.config.app.default_language
                    )
                    transcript = self.youtube.fetch_transcript(
                        detailed.video_url, detailed.video_id, language
                    )

                    clean_path: Path | None = None
                    clean_model: str | None = None
                    clean_prompt_version: str | None = None
                    exact_hash: str | None = None
                    exact_vtt_path: Path | None = None
                    exact_txt_path: Path | None = None

                    self.storage.write_video_metadata(
                        detailed,
                        transcript_source=transcript.source_type,
                        language=transcript.language,
                    )

                    if transcript.vtt_text:
                        cues = parse_vtt(transcript.vtt_text)
                        exact_vtt_path = self.storage.write_video_artifact(
                            detailed.video_id,
                            "transcript_exact.vtt",
                            transcript.vtt_text,
                        )
                        exact_md = render_timestamped_markdown(cues)
                        exact_txt = render_plain_text(cues)
                        exact_txt_path = self.storage.write_video_artifact(
                            detailed.video_id, "transcript_exact.md", exact_md
                        )
                        self.storage.write_video_artifact(
                            detailed.video_id, "transcript_exact.txt", exact_txt
                        )
                        exact_hash = _sha256(transcript.vtt_text)

                        if self.config.app.enable_cleanup:
                            cached = self.storage.find_clean_text_by_hash(exact_hash)
                            if cached is not None:
                                clean_text = cached
                                clean_model = "cache"
                                clean_prompt_version = self.config.llm.prompt_version
                            else:
                                clean_text, clean_model, clean_prompt_version = (
                                    self.llm.clean_transcript(exact_txt)
                                )
                            clean_path = self.storage.write_video_artifact(
                                detailed.video_id, "transcript_clean.md", clean_text
                            )

                    self.storage.upsert_transcript(
                        video_id=detailed.video_id,
                        language=transcript.language,
                        source_type=transcript.source_type,
                        exact_hash=exact_hash,
                        exact_path=exact_vtt_path,
                        exact_text_path=exact_txt_path,
                        clean_path=clean_path,
                        clean_model=clean_model,
                        clean_prompt_version=clean_prompt_version,
                    )
                    self.storage.log_run_item(
                        run_id,
                        video_id=detailed.video_id,
                        step="write",
                        status="ok",
                        message=transcript.source_type,
                    )
                    videos_processed += 1
                except Exception as exc:  # noqa: BLE001
                    videos_failed += 1
                    failures.append({"video_id": candidate.video_id, "error": str(exc)})
                    self.storage.log_run_item(
                        run_id,
                        video_id=candidate.video_id,
                        step="process",
                        status="error",
                        message=str(exc),
                    )

            status = "partial" if videos_failed else "success"
            error_summary = (
                json.dumps(failures, ensure_ascii=True) if failures else None
            )
            finished_at = self.storage.finish_run(
                run_id,
                status=status,
                videos_seen=videos_seen,
                videos_new=videos_new,
                videos_processed=videos_processed,
                videos_failed=videos_failed,
                error_summary=error_summary,
            )
            self.storage.write_run_report(run_id)
            return RunSummary(
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                videos_seen=videos_seen,
                videos_new=videos_new,
                videos_processed=videos_processed,
                videos_failed=videos_failed,
                failures=failures,
            )
        finally:
            self.storage.close()


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
