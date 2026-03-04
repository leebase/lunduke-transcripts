from __future__ import annotations

from datetime import UTC, datetime

from lunduke_transcripts.app.orchestrator import Orchestrator
from lunduke_transcripts.config import AppConfig, ChannelConfig, Config, LLMConfig
from lunduke_transcripts.domain.models import (
    RunOptions,
    TranscriptFetchResult,
    VideoRecord,
)
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
                video_url="https://www.youtube.com/watch?v=aaa111",
                channel_id="chan1",
                channel_name="Journalist",
                channel_url=channel_url,
                title="Episode A",
                description="desc A",
                published_at=_dt(1),
                duration_seconds=120,
            ),
            VideoRecord(
                video_id="bbb222",
                video_url="https://www.youtube.com/watch?v=bbb222",
                channel_id="chan1",
                channel_name="Journalist",
                channel_url=channel_url,
                title="Episode B",
                description="desc B",
                published_at=_dt(3),
                duration_seconds=180,
            ),
        ]

    def fetch_video_metadata(
        self, video_url: str, fallback: VideoRecord
    ) -> VideoRecord:
        _ = video_url
        return fallback

    def fetch_transcript(
        self, video_url: str, video_id: str, language: str
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


class FakeLLMAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt_version = "v1"

    def clean_transcript(self, exact_transcript: str) -> tuple[str, str, str]:
        self.calls += 1
        return exact_transcript.upper(), "fake-model", self.prompt_version


def _config(tmp_path) -> Config:
    return Config(
        app=AppConfig(
            data_dir=tmp_path / "data",
            enable_cleanup=True,
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


def test_date_range_and_idempotency(tmp_path) -> None:
    config = _config(tmp_path)
    storage = Storage(config.app.data_dir)
    youtube = FakeYouTubeAdapter()
    llm = FakeLLMAdapter()
    orchestrator = Orchestrator(
        config=config, storage=storage, youtube=youtube, llm=llm
    )

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
    assert llm.calls >= 1
