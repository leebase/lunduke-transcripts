"""Single-video transcript and artifact pipeline service."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lunduke_transcripts.app.tutorial_asset_builder import (
    render_frame_manifest,
    render_tutorial_asset_bundle,
)
from lunduke_transcripts.domain.models import (
    RunOptions,
    TranscriptFetchResult,
    VideoRecord,
)
from lunduke_transcripts.infra.asr_plugins.base import ASRPlugin
from lunduke_transcripts.infra.llm_adapter import LLMAdapter
from lunduke_transcripts.infra.local_media_adapter import LocalMediaAdapter
from lunduke_transcripts.infra.storage import Storage
from lunduke_transcripts.infra.video_frame_extractor import VideoFrameExtractor
from lunduke_transcripts.infra.youtube_adapter import YtDlpAdapter
from lunduke_transcripts.transforms.transcript_json_writer import (
    render_transcript_json,
)
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


@dataclass(frozen=True)
class VideoProcessResult:
    """Outcome from processing a single video candidate."""

    count_new: bool = False
    processed: bool = False
    failed: bool = False
    failure: dict[str, str] | None = None


@dataclass(frozen=True)
class FrameCaptureResult:
    """Frame extraction outcome for bundle generation and run reporting."""

    status: str
    manifest_path: Path | None = None
    error: str | None = None


class SingleVideoTranscriber:
    """Processes one source video end-to-end and persists all artifacts."""

    def __init__(
        self,
        *,
        storage: Storage,
        youtube: YtDlpAdapter,
        llm: LLMAdapter,
        llm_prompt_version: str,
        asr_plugin: ASRPlugin | None = None,
        local_media: LocalMediaAdapter,
        frame_extractor: VideoFrameExtractor,
        enable_asr_fallback: bool = False,
        force_asr: bool = False,
        keep_audio_files: bool = False,
        enable_frame_capture: bool = True,
        frame_capture_threshold: float = 0.25,
        frame_image_format: str = "jpg",
    ) -> None:
        self.storage = storage
        self.youtube = youtube
        self.llm = llm
        self.llm_prompt_version = llm_prompt_version
        self.asr_plugin = asr_plugin
        self.local_media = local_media
        self.frame_extractor = frame_extractor
        self.enable_asr_fallback = enable_asr_fallback
        self.force_asr = force_asr
        self.keep_audio_files = keep_audio_files
        self.enable_frame_capture = enable_frame_capture
        self.frame_capture_threshold = frame_capture_threshold
        self.frame_image_format = frame_image_format

    def process(
        self,
        *,
        run_id: str,
        candidate: VideoRecord,
        options: RunOptions,
        language: str,
        cleanup_enabled: bool,
        article_enabled: bool,
        llm_enabled: bool,
        clip_start: str | None = None,
        clip_end: str | None = None,
        force_asr: bool | None = None,
    ) -> VideoProcessResult:
        count_new = False
        try:
            detailed = self._refresh_metadata(candidate)
            self.storage.upsert_video(detailed)
            if not _in_range(detailed.published_at, options.from_utc, options.to_utc):
                self.storage.log_run_item(
                    run_id,
                    video_id=detailed.video_id,
                    step="filter",
                    status="skipped",
                    message="outside_date_range_or_missing_publish_time",
                )
                return VideoProcessResult()

            count_new = True
            use_asr = force_asr if force_asr is not None else self.force_asr
            transcript = self._fetch_transcript(
                run_id=run_id,
                video=detailed,
                language=language,
                clip_start=clip_start,
                clip_end=clip_end,
                use_asr=use_asr,
            )

            clean_path: Path | None = None
            clean_model: str | None = None
            clean_prompt_version: str | None = None
            article_path: Path | None = None
            article_model: str | None = None
            article_prompt_version: str | None = None
            exact_hash: str | None = None
            exact_vtt_path: Path | None = None
            exact_text_path: Path | None = None
            transcript_json_path: Path | None = None
            frame_manifest_path: Path | None = None
            tutorial_asset_bundle_path: Path | None = None
            frame_capture_result = FrameCaptureResult(status="not_requested")
            source_details = transcript.source_details or {}

            self.storage.write_video_metadata(
                detailed,
                transcript_source=transcript.source_type,
                language=transcript.language,
                source_details=source_details,
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
                self.storage.write_video_artifact(
                    detailed.video_id, "transcript_exact.md", exact_md
                )
                exact_text_path = self.storage.write_video_artifact(
                    detailed.video_id, "transcript_exact.txt", exact_txt
                )
                if transcript.segments_tsv:
                    self.storage.write_video_artifact(
                        detailed.video_id,
                        "transcript_segments.tsv",
                        transcript.segments_tsv,
                    )
                exact_hash = _sha256(transcript.vtt_text)
                transcript_json_path = self.storage.write_video_artifact(
                    detailed.video_id,
                    "transcript.json",
                    render_transcript_json(
                        video=detailed,
                        transcript_source=transcript.source_type,
                        language=transcript.language,
                        cues=cues,
                        exact_vtt_name="transcript_exact.vtt",
                        exact_markdown_name="transcript_exact.md",
                        exact_text_name="transcript_exact.txt",
                    ),
                )
                frame_capture_result = self._write_frame_manifest(
                    run_id=run_id,
                    video=detailed,
                    clip_start=clip_start,
                    clip_end=clip_end,
                )
                frame_manifest_path = frame_capture_result.manifest_path
                tutorial_asset_bundle_path = self.storage.write_video_artifact(
                    detailed.video_id,
                    "tutorial_asset_bundle.json",
                    render_tutorial_asset_bundle(
                        video=detailed,
                        transcript_path="transcript.json",
                        frame_manifest_path=(
                            "frame_manifest.json"
                            if frame_manifest_path is not None
                            else None
                        ),
                        frame_capture_status=frame_capture_result.status,
                        frame_capture_error=frame_capture_result.error,
                    ),
                )

                if cleanup_enabled and llm_enabled:
                    try:
                        cached = self.storage.find_clean_text_by_hash(exact_hash)
                        if cached is not None:
                            clean_text = cached
                            clean_model = "cache"
                            clean_prompt_version = self.llm_prompt_version
                        else:
                            clean_text, clean_model, clean_prompt_version = (
                                self.llm.clean_transcript(exact_txt)
                            )
                        clean_path = self.storage.write_video_artifact(
                            detailed.video_id, "transcript_clean.md", clean_text
                        )
                    except Exception as exc:  # noqa: BLE001
                        self.storage.log_run_item(
                            run_id,
                            video_id=detailed.video_id,
                            step="clean",
                            status="error",
                            message=str(exc),
                        )

                if article_enabled and llm_enabled:
                    try:
                        article_text, article_model, article_prompt_version = (
                            self.llm.write_news_article(exact_md, detailed.title)
                        )
                        article_path = self.storage.write_video_artifact(
                            detailed.video_id, "news_article.md", article_text
                        )
                        article_meta = {
                            "model": article_model,
                            "prompt_version": article_prompt_version,
                            "source": "transcript_exact.md",
                            "video_id": detailed.video_id,
                            "title": detailed.title,
                        }
                        self.storage.write_video_artifact(
                            detailed.video_id,
                            "news_article_metadata.json",
                            json.dumps(article_meta, indent=2, sort_keys=True) + "\n",
                        )
                    except Exception as exc:  # noqa: BLE001
                        self.storage.log_run_item(
                            run_id,
                            video_id=detailed.video_id,
                            step="article",
                            status="error",
                            message=str(exc),
                        )

            self.storage.upsert_transcript(
                video_id=detailed.video_id,
                language=transcript.language,
                source_type=transcript.source_type,
                exact_hash=exact_hash,
                exact_path=exact_vtt_path,
                exact_text_path=exact_text_path,
                transcript_json_path=transcript_json_path,
                clean_path=clean_path,
                clean_model=clean_model,
                clean_prompt_version=clean_prompt_version,
                article_path=article_path,
                article_model=article_model,
                article_prompt_version=article_prompt_version,
                frame_manifest_path=frame_manifest_path,
                tutorial_asset_bundle_path=tutorial_asset_bundle_path,
            )
            self.storage.log_run_item(
                run_id,
                video_id=detailed.video_id,
                step="write",
                status="ok",
                message=transcript.source_type,
            )
            if frame_capture_result.status == "error":
                return VideoProcessResult(
                    count_new=True,
                    failed=True,
                    failure={
                        "video_id": detailed.video_id,
                        "error": frame_capture_result.error or "frame_capture_failed",
                    },
                )
            return VideoProcessResult(count_new=True, processed=True)
        except Exception as exc:  # noqa: BLE001
            failure = {"video_id": candidate.video_id, "error": str(exc)}
            self.storage.log_run_item(
                run_id,
                video_id=candidate.video_id,
                step="process",
                status="error",
                message=str(exc),
            )
            return VideoProcessResult(count_new=count_new, failed=True, failure=failure)

    def _refresh_metadata(self, candidate: VideoRecord) -> VideoRecord:
        if candidate.source_kind == "local_file":
            if candidate.local_path is None:
                raise RuntimeError("local_file_missing_path")
            return self.local_media.fetch_video_metadata(
                candidate.local_path, fallback=candidate
            )
        if candidate.video_url is None:
            raise RuntimeError("youtube_video_missing_url")
        return self.youtube.fetch_video_metadata(
            candidate.video_url,
            fallback=candidate,
        )

    def _fetch_transcript(
        self,
        *,
        run_id: str,
        video: VideoRecord,
        language: str,
        clip_start: str | None,
        clip_end: str | None,
        use_asr: bool,
    ) -> TranscriptFetchResult:
        if use_asr:
            return self._transcribe_or_unavailable(
                run_id=run_id,
                video=video,
                language=language,
                clip_start=clip_start,
                clip_end=clip_end,
            )

        if video.source_kind == "local_file":
            if video.local_path is None:
                raise RuntimeError("local_file_missing_path")
            transcript = self.local_media.fetch_transcript(video.local_path, language)
        else:
            if video.video_url is None:
                raise RuntimeError("youtube_video_missing_url")
            transcript = self.youtube.fetch_transcript(
                video.video_url, video.video_id, language
            )

        if transcript.vtt_text is None and self.enable_asr_fallback:
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="asr",
                status="started",
                message="caption_unavailable_fallback",
            )
            return (
                self._transcribe_via_asr(
                    run_id=run_id,
                    video=video,
                    language=language,
                    clip_start=clip_start,
                    clip_end=clip_end,
                )
                or transcript
            )
        return transcript

    def _transcribe_or_unavailable(
        self,
        *,
        run_id: str,
        video: VideoRecord,
        language: str,
        clip_start: str | None,
        clip_end: str | None,
    ) -> TranscriptFetchResult:
        transcript = self._transcribe_via_asr(
            run_id=run_id,
            video=video,
            language=language,
            clip_start=clip_start,
            clip_end=clip_end,
        )
        if transcript is not None:
            return transcript
        return TranscriptFetchResult(
            source_type="unavailable",
            language=language,
            vtt_text=None,
        )

    def _write_frame_manifest(
        self,
        *,
        run_id: str,
        video: VideoRecord,
        clip_start: str | None,
        clip_end: str | None,
    ) -> FrameCaptureResult:
        if not self.enable_frame_capture:
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="frames",
                status="skipped",
                message="frame_capture_disabled",
            )
            return FrameCaptureResult(status="disabled")

        frames_dir = (
            self.storage._video_dir_for(video.video_id) / "frames"
        )  # noqa: SLF001
        try:
            video_path = self._resolve_video_path(video)
            frames = self.frame_extractor.extract_frames(
                video_path=video_path,
                output_dir=frames_dir,
                clip_start=clip_start,
                clip_end=clip_end,
            )
            frame_manifest_path = self.storage.write_video_artifact(
                video.video_id,
                "frame_manifest.json",
                render_frame_manifest(
                    video=video,
                    frames=frames,
                    threshold=self.frame_capture_threshold,
                    image_format=self.frame_image_format,
                ),
            )
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="frames",
                status="ok",
                message=f"frames={len(frames)}",
            )
            return FrameCaptureResult(
                status="captured",
                manifest_path=frame_manifest_path,
            )
        except Exception as exc:  # noqa: BLE001
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="frames",
                status="error",
                message=str(exc),
            )
            return FrameCaptureResult(status="error", error=str(exc))

    def _resolve_video_path(self, video: VideoRecord) -> Path:
        if video.source_kind == "local_file":
            if video.local_path is None:
                raise RuntimeError("local_file_missing_path")
            return Path(video.local_path)
        if video.video_url is None:
            raise RuntimeError("youtube_video_missing_url")
        with tempfile.TemporaryDirectory() as tmp:
            downloaded = self.youtube.download_video_file(
                video_url=video.video_url,
                video_id=video.video_id,
                output_dir=Path(tmp),
            )
            persisted = self.storage.data_dir / "video_cache"
            persisted.mkdir(parents=True, exist_ok=True)
            target_path = persisted / f"{video.video_id}{downloaded.suffix}"
            shutil.copyfile(downloaded, target_path)
            return target_path

    def _transcribe_via_asr(
        self,
        *,
        run_id: str,
        video: VideoRecord,
        language: str,
        clip_start: str | None,
        clip_end: str | None,
    ) -> TranscriptFetchResult | None:
        if self.asr_plugin is None:
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="asr",
                status="skipped",
                message="asr_not_configured",
            )
            return None
        if not self.asr_plugin.is_available():
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="asr",
                status="error",
                message="asr_plugin_unavailable",
            )
            return None

        try:
            if self.keep_audio_files:
                audio_dir = self.storage.data_dir / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                audio_path = self._extract_audio_path(
                    video=video,
                    output_dir=audio_dir,
                    clip_start=clip_start,
                    clip_end=clip_end,
                )
                return self._transcribe_audio_path(
                    run_id=run_id,
                    video=video,
                    audio_path=audio_path,
                    language=language,
                    clip_start=clip_start,
                    clip_end=clip_end,
                )
            with tempfile.TemporaryDirectory() as tmp:
                audio_path = self._extract_audio_path(
                    video=video,
                    output_dir=Path(tmp),
                    clip_start=clip_start,
                    clip_end=clip_end,
                )
                return self._transcribe_audio_path(
                    run_id=run_id,
                    video=video,
                    audio_path=audio_path,
                    language=language,
                    clip_start=clip_start,
                    clip_end=clip_end,
                )
        except Exception as exc:  # noqa: BLE001
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="asr",
                status="error",
                message=str(exc),
            )
            return None

    def _extract_audio_path(
        self,
        *,
        video: VideoRecord,
        output_dir: Path,
        clip_start: str | None,
        clip_end: str | None,
    ) -> Path:
        if video.source_kind == "local_file":
            if video.local_path is None:
                raise RuntimeError("local_file_missing_path")
            return self.local_media.extract_audio_clip(
                local_path=video.local_path,
                video_id=video.video_id,
                output_dir=output_dir,
                clip_start=clip_start,
                clip_end=clip_end,
            )
        if video.video_url is None:
            raise RuntimeError("youtube_video_missing_url")
        return self.youtube.download_audio_clip(
            video_url=video.video_url,
            video_id=video.video_id,
            output_dir=output_dir,
            clip_start=clip_start,
            clip_end=clip_end,
        )

    def _transcribe_audio_path(
        self,
        *,
        run_id: str,
        video: VideoRecord,
        audio_path: Path,
        language: str,
        clip_start: str | None,
        clip_end: str | None,
    ) -> TranscriptFetchResult | None:
        try:
            asr = self.asr_plugin
            if asr is None:
                return None
            asr_transcript = asr.transcribe(audio_path=audio_path, language=language)
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="asr",
                status="ok",
                message=f"provider={asr_transcript.provider}",
            )
            source_details = {
                "asr_provider": asr_transcript.provider,
                "asr_model": asr_transcript.model,
            }
            if clip_start:
                source_details["clip_start"] = clip_start
            if clip_end:
                source_details["clip_end"] = clip_end
            return TranscriptFetchResult(
                source_type=f"asr_{asr_transcript.provider}",
                language=asr_transcript.language or language,
                vtt_text=asr_transcript.to_vtt(),
                segments_tsv=asr_transcript.to_segments_tsv(),
                source_details=source_details,
            )
        except Exception as exc:  # noqa: BLE001
            self.storage.log_run_item(
                run_id,
                video_id=video.video_id,
                step="asr",
                status="error",
                message=str(exc),
            )
            return None
