"""End-to-end orchestration wrapper for channel/video targets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lunduke_transcripts.app.single_video_transcriber import SingleVideoTranscriber
from lunduke_transcripts.config import Config
from lunduke_transcripts.domain.models import RunOptions, RunSummary
from lunduke_transcripts.infra.asr_plugins.base import ASRPlugin
from lunduke_transcripts.infra.llm_adapter import LLMAdapter
from lunduke_transcripts.infra.local_media_adapter import LocalMediaAdapter
from lunduke_transcripts.infra.storage import Storage
from lunduke_transcripts.infra.video_frame_extractor import VideoFrameExtractor
from lunduke_transcripts.infra.youtube_adapter import YtDlpAdapter


@dataclass(frozen=True)
class TargetSettings:
    language: str
    clip_start: str | None = None
    clip_end: str | None = None
    force_asr: bool | None = None


class Orchestrator:
    """Coordinates discovery, filtering, per-video processing, and run reporting."""

    def __init__(
        self,
        config: Config,
        storage: Storage,
        youtube: YtDlpAdapter,
        llm: LLMAdapter,
        asr_plugin: ASRPlugin | None = None,
        local_media: LocalMediaAdapter | None = None,
        frame_extractor: VideoFrameExtractor | None = None,
    ) -> None:
        self.config = config
        self.storage = storage
        self.youtube = youtube
        self.llm = llm
        self.asr_plugin = asr_plugin
        self.local_media = local_media or LocalMediaAdapter(
            ffmpeg_binary=config.app.ffmpeg_binary,
            ffprobe_binary=config.app.ffprobe_binary,
            ffmpeg_timeout_seconds=config.app.ffmpeg_timeout_seconds,
        )
        self.frame_extractor = frame_extractor or VideoFrameExtractor(
            ffmpeg_binary=config.app.ffmpeg_binary,
            threshold=config.app.frame_capture_threshold,
            image_format=config.app.frame_image_format,
            timeout_seconds=config.app.ffmpeg_timeout_seconds,
        )

    def run(self, options: RunOptions) -> RunSummary:
        self.storage.initialize()
        run_id, started_at = self.storage.start_run(options.from_utc, options.to_utc)
        failures: list[dict[str, str]] = []
        videos_seen = 0
        cleanup_enabled = self.config.app.enable_cleanup
        article_enabled = self.config.app.enable_article or options.generate_article
        llm_enabled = bool(getattr(self.llm, "is_enabled", lambda: True)())
        processor = SingleVideoTranscriber(
            storage=self.storage,
            youtube=self.youtube,
            llm=self.llm,
            llm_prompt_version=self.config.llm.prompt_version,
            asr_plugin=self.asr_plugin,
            local_media=self.local_media,
            frame_extractor=self.frame_extractor,
            enable_asr_fallback=self.config.app.enable_asr_fallback,
            force_asr=self.config.app.force_asr,
            keep_audio_files=self.config.app.keep_audio_files,
            enable_frame_capture=self.config.app.frame_capture_enabled,
            frame_capture_threshold=self.config.app.frame_capture_threshold,
            frame_image_format=self.config.app.frame_image_format,
        )

        try:
            discovered_video_ids: set[str] = set()
            target_settings: dict[str, TargetSettings] = {}
            discovery_failures = 0

            for channel in self.config.channels:
                discovered = self.youtube.list_videos(
                    channel.url, max_items=self.config.app.max_videos_per_channel
                )
                videos_seen += len(discovered)
                for video in discovered:
                    self.storage.upsert_video(video)
                    discovered_video_ids.add(video.video_id)
                    target_settings[video.video_id] = TargetSettings(
                        language=(channel.language or self.config.app.default_language),
                    )
                self.storage.log_run_item(
                    run_id,
                    video_id=None,
                    step="discover",
                    status="ok",
                    message=f"{channel.name}: discovered={len(discovered)}",
                )

            for video_target in self.config.videos:
                discovered = self.youtube.list_videos(video_target.url, max_items=1)
                videos_seen += len(discovered)
                for video in discovered:
                    self.storage.upsert_video(video)
                    discovered_video_ids.add(video.video_id)
                    target_settings[video.video_id] = TargetSettings(
                        language=(
                            video_target.language or self.config.app.default_language
                        ),
                        clip_start=video_target.clip_start,
                        clip_end=video_target.clip_end,
                        force_asr=video_target.force_asr,
                    )
                self.storage.log_run_item(
                    run_id,
                    video_id=None,
                    step="discover",
                    status="ok",
                    message=f"{video_target.name}: discovered={len(discovered)}",
                )

            for file_target in self.config.files:
                try:
                    record = self.local_media.probe_video(Path(file_target.path))
                    self.storage.upsert_video(record)
                    discovered_video_ids.add(record.video_id)
                    target_settings[record.video_id] = TargetSettings(
                        language=(
                            file_target.language or self.config.app.default_language
                        ),
                        clip_start=file_target.clip_start,
                        clip_end=file_target.clip_end,
                        force_asr=file_target.force_asr,
                    )
                    videos_seen += 1
                    self.storage.log_run_item(
                        run_id,
                        video_id=record.video_id,
                        step="discover",
                        status="ok",
                        message=f"{file_target.name}: discovered=1",
                    )
                except Exception as exc:  # noqa: BLE001
                    discovery_failures += 1
                    failures.append({"video_id": file_target.path, "error": str(exc)})
                    self.storage.log_run_item(
                        run_id,
                        video_id=None,
                        step="discover",
                        status="error",
                        message=f"{file_target.name}: {exc}",
                    )

            if discovered_video_ids:
                candidates = self.storage.list_candidates(
                    channel_urls=None,
                    video_ids=sorted(discovered_video_ids),
                    filter_from=options.from_utc,
                    filter_to=options.to_utc,
                    reprocess=options.reprocess,
                )
            else:
                candidates = []

            videos_new = 0
            videos_processed = 0
            videos_failed = 0

            if (cleanup_enabled or article_enabled) and not llm_enabled:
                self.storage.log_run_item(
                    run_id,
                    video_id=None,
                    step="llm",
                    status="skipped",
                    message="llm_not_configured",
                )

            for candidate in candidates:
                settings = target_settings.get(
                    candidate.video_id,
                    TargetSettings(language=self.config.app.default_language),
                )
                result = processor.process(
                    run_id=run_id,
                    candidate=candidate,
                    options=options,
                    language=settings.language,
                    cleanup_enabled=cleanup_enabled,
                    article_enabled=article_enabled,
                    llm_enabled=llm_enabled,
                    clip_start=settings.clip_start,
                    clip_end=settings.clip_end,
                    force_asr=settings.force_asr,
                )
                if result.count_new:
                    videos_new += 1
                if result.processed:
                    videos_processed += 1
                if result.failed:
                    videos_failed += 1
                    if result.failure is not None:
                        failures.append(result.failure)

            total_failed = videos_failed + discovery_failures
            status = "success"
            if total_failed:
                status = "failed" if videos_processed == 0 else "partial"
            error_summary = (
                json.dumps(failures, ensure_ascii=True) if failures else None
            )
            finished_at = self.storage.finish_run(
                run_id,
                status=status,
                videos_seen=videos_seen,
                videos_new=videos_new,
                videos_processed=videos_processed,
                videos_failed=total_failed,
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
                videos_failed=total_failed,
                failures=failures,
            )
        finally:
            self.storage.close()


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
