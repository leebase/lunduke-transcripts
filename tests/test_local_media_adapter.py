from __future__ import annotations

from lunduke_transcripts.infra.local_media_adapter import LocalMediaAdapter


def test_probe_video_id_is_stable_across_touch_and_rename(tmp_path) -> None:
    adapter = LocalMediaAdapter()
    original = tmp_path / "demo.mp4"
    original.write_text("same content", encoding="utf-8")

    first = adapter.probe_video(original)
    original.touch()
    touched = adapter.probe_video(original)

    renamed = tmp_path / "renamed-demo.mp4"
    original.rename(renamed)
    moved = adapter.probe_video(renamed)

    assert touched.video_id == first.video_id
    assert moved.video_id == first.video_id
