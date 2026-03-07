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


def test_undated_folder_upgrades_when_published_at_arrives(tmp_path) -> None:
    storage = Storage(tmp_path / "data")
    storage.initialize()
    initial = VideoRecord(
        video_id="vid1",
        video_url="https://www.youtube.com/watch?v=vid1",
        channel_id="chan1",
        channel_name="Channel",
        channel_url="https://www.youtube.com/@channel/videos",
        title="Fresh Title",
        description=None,
        published_at=None,
        duration_seconds=60,
    )
    storage.upsert_video(initial)
    old_path = storage.write_video_artifact("vid1", "transcript_exact.md", "x")
    assert old_path.parent.name.startswith("undated_")

    updated = VideoRecord(
        video_id="vid1",
        video_url="https://www.youtube.com/watch?v=vid1",
        channel_id="chan1",
        channel_name="Channel",
        channel_url="https://www.youtube.com/@channel/videos",
        title="Fresh Title",
        description=None,
        published_at=datetime(2026, 3, 4, 10, 0, tzinfo=UTC),
        duration_seconds=60,
    )
    storage.upsert_video(updated)
    new_path = storage.write_video_artifact("vid1", "metadata.json", "{}")
    storage.close()

    assert new_path.parent.name.startswith("2026-03-04_fresh-title__vid1")
    assert "undated_" not in new_path.parent.name
    assert not old_path.parent.exists()


def test_initialize_migrates_existing_undated_folder_and_paths(tmp_path) -> None:
    storage = Storage(tmp_path / "data")
    storage.initialize()
    video = VideoRecord(
        video_id="vid2",
        video_url="https://www.youtube.com/watch?v=vid2",
        channel_id="chan1",
        channel_name="Channel",
        channel_url="https://www.youtube.com/@channel/videos",
        title="Date Backfill",
        description=None,
        published_at=None,
        duration_seconds=60,
    )
    storage.upsert_video(video)
    undated_vtt = storage.write_video_artifact(
        "vid2", "transcript_exact.vtt", "WEBVTT\n"
    )
    storage.upsert_transcript(
        video_id="vid2",
        language="en",
        source_type="auto",
        exact_hash="h",
        exact_path=undated_vtt,
        exact_text_path=None,
        transcript_json_path=None,
        clean_path=None,
        clean_model=None,
        clean_prompt_version=None,
        article_path=None,
        article_model=None,
        article_prompt_version=None,
        frame_manifest_path=None,
        tutorial_asset_bundle_path=None,
    )
    storage.upsert_video(
        VideoRecord(
            video_id="vid2",
            video_url="https://www.youtube.com/watch?v=vid2",
            channel_id="chan1",
            channel_name="Channel",
            channel_url="https://www.youtube.com/@channel/videos",
            title="Date Backfill",
            description=None,
            published_at=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
            duration_seconds=60,
        )
    )
    storage.close()

    storage2 = Storage(tmp_path / "data")
    storage2.initialize()
    row = storage2.conn.execute(
        "SELECT artifact_dir FROM videos WHERE video_id = 'vid2'"
    ).fetchone()
    tr = storage2.conn.execute(
        "SELECT exact_path FROM transcripts WHERE video_id = 'vid2'"
    ).fetchone()
    storage2.close()

    assert row is not None
    assert row["artifact_dir"].startswith("2026-03-01_date-backfill__vid2")
    assert tr is not None
    assert "2026-03-01_date-backfill__vid2" in tr["exact_path"]
