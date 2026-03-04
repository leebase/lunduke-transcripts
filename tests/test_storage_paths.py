from datetime import UTC, datetime

from lunduke_transcripts.domain.models import VideoRecord
from lunduke_transcripts.infra.storage import Storage


def test_artifacts_use_title_based_directory(tmp_path) -> None:
    storage = Storage(tmp_path / "data")
    storage.initialize()
    video = VideoRecord(
        video_id="abc123",
        video_url="https://www.youtube.com/watch?v=abc123",
        channel_id="chan1",
        channel_name="Channel",
        channel_url="https://www.youtube.com/@channel/videos",
        title="A Big Story: Rust & Python?!",
        description=None,
        published_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        duration_seconds=60,
    )
    storage.upsert_video(video)

    metadata_path = storage.write_video_metadata(
        video, transcript_source="manual", language="en"
    )
    artifact_path = storage.write_video_artifact(
        video.video_id, "transcript_exact.md", "x"
    )
    storage.close()

    expected_dir = "2026-03-01_a-big-story-rust-python__abc123"
    assert metadata_path.parent.name == expected_dir
    assert artifact_path.parent.name == expected_dir


def test_legacy_video_id_folder_is_migrated(tmp_path) -> None:
    storage = Storage(tmp_path / "data")
    storage.initialize()
    video = VideoRecord(
        video_id="legacy1",
        video_url="https://www.youtube.com/watch?v=legacy1",
        channel_id="chan1",
        channel_name="Channel",
        channel_url="https://www.youtube.com/@channel/videos",
        title="Legacy Name",
        description=None,
        published_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        duration_seconds=60,
    )
    storage.upsert_video(video)
    legacy_dir = storage.videos_dir / "legacy1"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    (legacy_dir / "transcript_exact.md").write_text("legacy", encoding="utf-8")

    artifact_path = storage.write_video_artifact(video.video_id, "metadata.json", "{}")
    storage.close()

    assert artifact_path.parent.name.startswith("2026-02-01_legacy-name__legacy1")
    assert not legacy_dir.exists()
