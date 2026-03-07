from __future__ import annotations

import subprocess

import pytest

from lunduke_transcripts.infra.video_frame_extractor import VideoFrameExtractor


def test_extract_frames_keeps_existing_frames_when_new_extraction_fails(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    extractor = VideoFrameExtractor(ffmpeg_binary="ffmpeg")
    output_dir = tmp_path / "frames"
    output_dir.mkdir()
    existing = output_dir / "000000.jpg"
    existing.write_text("old frame", encoding="utf-8")
    video_path = tmp_path / "demo.mp4"
    video_path.write_text("video", encoding="utf-8")

    def _fail(*args, **kwargs):
        _ = (args, kwargs)
        raise subprocess.CalledProcessError(1, "ffmpeg", stderr="boom")

    monkeypatch.setattr(subprocess, "run", _fail)

    with pytest.raises(subprocess.CalledProcessError):
        extractor.extract_frames(video_path=video_path, output_dir=output_dir)

    assert existing.exists()
    assert existing.read_text(encoding="utf-8") == "old frame"
    assert sorted(output_dir.glob("*.jpg")) == [existing]
