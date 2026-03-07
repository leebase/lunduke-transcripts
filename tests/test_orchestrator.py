from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from lunduke_transcripts.app.orchestrator import Orchestrator
from lunduke_transcripts.config import (
    AppConfig,
    ChannelConfig,
    Config,
    FileConfig,
    LLMConfig,
    VideoConfig,
)
from lunduke_transcripts.domain.models import (
    FrameCandidate,
    RunOptions,
    TranscriptFetchResult,
    VideoRecord,
)
from lunduke_transcripts.infra.asr_plugins.base import ASRSegment, ASRTranscript
from lunduke_transcripts.infra.storage import Storage


def _dt(day: int) -> datetime:
    return datetime(2026, 2, day, 12, 0, 0, tzinfo=UTC)


class FakeYouTubeAdapter:
    def list_videos(
        self, channel_url: str, max_items: int | None = None
    ) -> list[VideoRecord]:
        _ = max_items
        return [
            VideoRecord(
                video_id="aaa111",
                title="Episode A",
                source_kind="youtube_video",
                video_url="https://www.youtube.com/watch?v=aaa111",
                channel_id="chan1",
                channel_name="Journalist",
                channel_url=channel_url,
                description="desc A",
                published_at=_dt(1),
                duration_seconds=120,
            ),
            VideoRecord(
                video_id="bbb222",
                title="Episode B",
                source_kind="youtube_video",
                video_url="https://www.youtube.com/watch?v=bbb222",
                channel_id="chan1",
                channel_name="Journalist",
                channel_url=channel_url,
                description="desc B",
                published_at=_dt(3),
                duration_seconds=180,
            ),
        ]

    def fetch_video_metadata(
        self, video_url: str | None, fallback: VideoRecord
    ) -> VideoRecord:
        _ = video_url
        return fallback

    def fetch_transcript(
        self, video_url: str | None, video_id: str, language: str
    ) -> TranscriptFetchResult:
        _ = (video_url, video_id, language)
        return TranscriptFetchResult(
            source_type="manual",
            language="en",
            vtt_text=(
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:02.000\n"
                "hello there\n\n"
                "00:00:03.000 --> 00:00:04.000\n"
                "general kenobi\n"
            ),
        )

    def download_audio_clip(
        self,
        *,
        video_url: str,
        video_id: str,
        output_dir: Path,
        clip_start: str | None,
        clip_end: str | None,
    ) -> Path:
        _ = (video_url, clip_start, clip_end)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{video_id}.mp3"
        path.write_text("fake audio", encoding="utf-8")
        return path

    def download_video_file(
        self,
        *,
        video_url: str,
        video_id: str,
        output_dir: Path,
    ) -> Path:
        _ = video_url
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{video_id}.mp4"
        path.write_text("fake video", encoding="utf-8")
        return path


class FakeLocalMediaAdapter:
    def probe_video(self, path: str | Path) -> VideoRecord:
        local_path = Path(path)
        if not local_path.exists():
            raise RuntimeError(f"local_file_missing: {local_path}")
        return VideoRecord(
            video_id="local-demo",
            title=local_path.stem,
            source_kind="local_file",
            video_url=local_path.as_uri(),
            local_path=str(local_path),
            channel_id=None,
            channel_name=local_path.parent.name or "local-files",
            channel_url=local_path.parent.as_uri(),
            description=None,
            published_at=None,
            duration_seconds=95,
        )

    def fetch_video_metadata(
        self, local_path: str | Path, fallback: VideoRecord
    ) -> VideoRecord:
        _ = local_path
        return fallback

    def fetch_transcript(
        self, local_path: str | Path, language: str | None
    ) -> TranscriptFetchResult:
        _ = (local_path, language)
        return TranscriptFetchResult(
            source_type="sidecar_vtt",
            language=language,
            vtt_text=(
                "WEBVTT\n\n" "00:00:00.000 --> 00:00:01.500\n" "open the file menu\n"
            ),
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
        _ = (local_path, clip_start, clip_end)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{video_id}.mp3"
        path.write_text("fake local audio", encoding="utf-8")
        return path


class FakeFrameExtractor:
    def extract_frames(
        self,
        *,
        video_path: Path,
        output_dir: Path,
        clip_start: str | None = None,
        clip_end: str | None = None,
    ) -> list[FrameCandidate]:
        _ = (video_path, clip_start, clip_end)
        output_dir.mkdir(parents=True, exist_ok=True)
        first = output_dir / "000000.jpg"
        second = output_dir / "000001.jpg"
        first.write_text("frame 0", encoding="utf-8")
        second.write_text("frame 1", encoding="utf-8")
        return [
            FrameCandidate(
                frame_index=0,
                timestamp_seconds=1.0,
                image_path="frames/000000.jpg",
            ),
            FrameCandidate(
                frame_index=1,
                timestamp_seconds=3.5,
                image_path="frames/000001.jpg",
            ),
        ]


class FakeLLMAdapter:
    def __init__(self) -> None:
        self.clean_calls = 0
        self.article_calls = 0
        self.prompt_version = "v1"

    def is_enabled(self) -> bool:
        return True

    def clean_transcript(self, exact_transcript: str) -> tuple[str, str, str]:
        self.clean_calls += 1
        return exact_transcript.upper(), "fake-model", self.prompt_version

    def write_news_article(
        self, exact_markdown_transcript: str, video_title: str | None
    ) -> tuple[str, str, str]:
        self.article_calls += 1
        title = video_title or "Untitled"
        body = (
            exact_markdown_transcript.splitlines()[0]
            if exact_markdown_transcript
            else ""
        )
        return f"# {title}\n\n{body}\n", "fake-model", self.prompt_version


def _config(tmp_path) -> Config:
    return Config(
        app=AppConfig(
            data_dir=tmp_path / "data",
            enable_cleanup=True,
            frame_capture_enabled=True,
        ),
        llm=LLMConfig(provider="openai", model="gpt-4.1-mini", prompt_version="v1"),
        channels=[
            ChannelConfig(
                name="Journalist",
                url="https://www.youtube.com/@journalist/videos",
                language="en",
            )
        ],
    )


def _build_orchestrator(
    tmp_path, config: Config
) -> tuple[Storage, Orchestrator, FakeLLMAdapter]:
    storage = Storage(config.app.data_dir)
    llm = FakeLLMAdapter()
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=FakeYouTubeAdapter(),
        llm=llm,
        local_media=FakeLocalMediaAdapter(),
        frame_extractor=FakeFrameExtractor(),
    )
    return storage, orchestrator, llm


def test_date_range_and_idempotency(tmp_path) -> None:
    config = _config(tmp_path)
    _storage, orchestrator, llm = _build_orchestrator(tmp_path, config)

    summary_one = orchestrator.run(
        RunOptions(
            config_path=tmp_path / "channels.toml",
            from_utc=_dt(3).replace(hour=0, minute=0),
            to_utc=_dt(3).replace(hour=23, minute=59),
            reprocess=False,
        )
    )
    assert summary_one.videos_seen == 2
    assert summary_one.videos_new == 1
    assert summary_one.videos_processed == 1
    assert summary_one.videos_failed == 0

    summary_two = orchestrator.run(
        RunOptions(
            config_path=tmp_path / "channels.toml",
            from_utc=_dt(3).replace(hour=0, minute=0),
            to_utc=_dt(3).replace(hour=23, minute=59),
            reprocess=False,
        )
    )
    assert summary_two.videos_new == 0
    assert summary_two.videos_processed == 0

    summary_three = orchestrator.run(
        RunOptions(
            config_path=tmp_path / "channels.toml",
            from_utc=_dt(3).replace(hour=0, minute=0),
            to_utc=_dt(3).replace(hour=23, minute=59),
            reprocess=True,
        )
    )
    assert summary_three.videos_new == 1
    assert summary_three.videos_processed == 1
    assert llm.clean_calls >= 1

    transcript_json = list((tmp_path / "data" / "videos").glob("*/transcript.json"))
    frame_manifests = list((tmp_path / "data" / "videos").glob("*/frame_manifest.json"))
    tutorial_bundles = list(
        (tmp_path / "data" / "videos").glob("*/tutorial_asset_bundle.json")
    )
    assert transcript_json
    assert frame_manifests
    assert tutorial_bundles


def test_article_generation_writes_artifacts(tmp_path) -> None:
    config = _config(tmp_path)
    config = Config(
        app=AppConfig(
            data_dir=tmp_path / "data",
            enable_cleanup=False,
            enable_article=False,
            frame_capture_enabled=True,
        ),
        llm=config.llm,
        channels=config.channels,
    )
    _storage, orchestrator, llm = _build_orchestrator(tmp_path, config)
    summary = orchestrator.run(
        RunOptions(config_path=tmp_path / "channels.toml", generate_article=True)
    )
    assert summary.videos_processed > 0
    assert llm.article_calls > 0

    article_files = list((tmp_path / "data" / "videos").glob("*/news_article.md"))
    assert article_files, "Expected generated news_article.md files"


def test_single_video_target_is_processed(tmp_path) -> None:
    class _SingleVideoAdapter(FakeYouTubeAdapter):
        def list_videos(
            self, channel_url: str, max_items: int | None = None
        ) -> list[VideoRecord]:
            _ = max_items
            if "watch?v=only123" not in channel_url:
                return []
            return [
                VideoRecord(
                    video_id="only123",
                    title="Single Video",
                    source_kind="youtube_video",
                    video_url="https://www.youtube.com/watch?v=only123",
                    channel_id="chan1",
                    channel_name="Journalist",
                    channel_url=channel_url,
                    description="single",
                    published_at=_dt(4),
                    duration_seconds=300,
                )
            ]

    config = Config(
        app=AppConfig(data_dir=tmp_path / "data", enable_cleanup=False),
        llm=LLMConfig(provider="openai", model="gpt-4.1-mini", prompt_version="v1"),
        channels=[],
        videos=[
            VideoConfig(
                name="Direct video",
                url="https://www.youtube.com/watch?v=only123",
                language="en",
            )
        ],
    )
    storage = Storage(config.app.data_dir)
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=_SingleVideoAdapter(),
        llm=FakeLLMAdapter(),
        local_media=FakeLocalMediaAdapter(),
        frame_extractor=FakeFrameExtractor(),
    )

    summary = orchestrator.run(RunOptions(config_path=tmp_path / "channels.toml"))
    assert summary.videos_seen == 1
    assert summary.videos_new == 1
    assert summary.videos_processed == 1


def test_local_file_target_is_processed(tmp_path) -> None:
    demo_path = tmp_path / "demo.mp4"
    demo_path.write_text("fake local video", encoding="utf-8")
    config = Config(
        app=AppConfig(data_dir=tmp_path / "data", enable_cleanup=False),
        llm=LLMConfig(provider="openai", model="gpt-4.1-mini", prompt_version="v1"),
        channels=[],
        files=[
            FileConfig(
                name="Local demo",
                path=str(demo_path),
                language="en",
            )
        ],
    )
    storage = Storage(config.app.data_dir)
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=FakeYouTubeAdapter(),
        llm=FakeLLMAdapter(),
        local_media=FakeLocalMediaAdapter(),
        frame_extractor=FakeFrameExtractor(),
    )

    summary = orchestrator.run(RunOptions(config_path=tmp_path / "channels.toml"))
    assert summary.videos_seen == 1
    assert summary.videos_new == 1
    assert summary.videos_processed == 1

    transcript_json = list((tmp_path / "data" / "videos").glob("*/transcript.json"))
    assert transcript_json


def test_missing_local_file_is_reported_as_failure(tmp_path) -> None:
    missing_path = tmp_path / "missing.mp4"
    config = Config(
        app=AppConfig(data_dir=tmp_path / "data", enable_cleanup=False),
        llm=LLMConfig(provider="openai", model="gpt-4.1-mini", prompt_version="v1"),
        channels=[],
        files=[
            FileConfig(
                name="Missing demo",
                path=str(missing_path),
                language="en",
            )
        ],
    )
    storage = Storage(config.app.data_dir)
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=FakeYouTubeAdapter(),
        llm=FakeLLMAdapter(),
        local_media=FakeLocalMediaAdapter(),
        frame_extractor=FakeFrameExtractor(),
    )

    summary = orchestrator.run(RunOptions(config_path=tmp_path / "channels.toml"))
    assert summary.status == "failed"
    assert summary.videos_seen == 0
    assert summary.videos_failed == 1
    assert summary.failures


def test_frame_capture_failure_marks_run_failed_but_keeps_bundle(tmp_path) -> None:
    class _FailingFrameExtractor:
        def extract_frames(
            self,
            *,
            video_path: Path,
            output_dir: Path,
            clip_start: str | None = None,
            clip_end: str | None = None,
        ) -> list[FrameCandidate]:
            _ = (video_path, output_dir, clip_start, clip_end)
            raise RuntimeError("ffmpeg_scene_detect_failed")

    config = _config(tmp_path)
    config = Config(
        app=AppConfig(
            data_dir=tmp_path / "data",
            enable_cleanup=False,
            frame_capture_enabled=True,
        ),
        llm=config.llm,
        channels=config.channels,
    )
    storage = Storage(config.app.data_dir)
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=FakeYouTubeAdapter(),
        llm=FakeLLMAdapter(),
        local_media=FakeLocalMediaAdapter(),
        frame_extractor=_FailingFrameExtractor(),
    )

    summary = orchestrator.run(RunOptions(config_path=tmp_path / "channels.toml"))
    assert summary.status == "failed"
    assert summary.videos_new == 2
    assert summary.videos_processed == 0
    assert summary.videos_failed == 2
    assert summary.failures

    bundles = sorted(
        (tmp_path / "data" / "videos").glob("*/tutorial_asset_bundle.json")
    )
    assert bundles
    payload = json.loads(bundles[0].read_text(encoding="utf-8"))
    assert payload["frame_manifest_path"] is None
    assert payload["frame_capture"]["status"] == "error"
    assert payload["frame_capture"]["error"] == "ffmpeg_scene_detect_failed"

    transcripts = sorted((tmp_path / "data" / "videos").glob("*/transcript.json"))
    assert transcripts


def test_asr_fallback_when_captions_unavailable(tmp_path) -> None:
    class _NoCaptionAdapter(FakeYouTubeAdapter):
        def fetch_transcript(
            self, video_url: str | None, video_id: str, language: str
        ) -> TranscriptFetchResult:
            _ = (video_url, video_id, language)
            return TranscriptFetchResult(
                source_type="unavailable",
                language=language,
                vtt_text=None,
            )

    class _FakeAsrPlugin:
        provider_name = "fast-whisper"
        model_name = "small.en"

        def is_available(self) -> bool:
            return True

        def transcribe(self, audio_path, language):
            _ = audio_path
            return ASRTranscript(
                provider=self.provider_name,
                model=self.model_name,
                language=language,
                segments=[
                    ASRSegment(1.0, 2.0, "hello there"),
                    ASRSegment(3.0, 4.0, "general kenobi"),
                ],
            )

    config = _config(tmp_path)
    config = Config(
        app=AppConfig(
            data_dir=tmp_path / "data",
            enable_cleanup=False,
            enable_asr_fallback=True,
        ),
        llm=config.llm,
        channels=config.channels,
    )
    storage = Storage(config.app.data_dir)
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=_NoCaptionAdapter(),
        llm=FakeLLMAdapter(),
        asr_plugin=_FakeAsrPlugin(),
        local_media=FakeLocalMediaAdapter(),
        frame_extractor=FakeFrameExtractor(),
    )
    summary = orchestrator.run(RunOptions(config_path=tmp_path / "channels.toml"))
    assert summary.videos_processed > 0

    metadata_files = list((tmp_path / "data" / "videos").glob("*/metadata.json"))
    assert metadata_files
    metadata = metadata_files[0].read_text(encoding="utf-8")
    assert "asr_fast-whisper" in metadata
