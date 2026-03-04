from __future__ import annotations

import subprocess

import pytest

from lunduke_transcripts.infra.youtube_adapter import YtDlpAdapter


def test_ytdlp_timeout_retries_then_succeeds(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = args
        calls["count"] += 1
        if calls["count"] == 1:
            raise subprocess.TimeoutExpired(cmd="yt-dlp", timeout=1)
        return subprocess.CompletedProcess(
            args=["yt-dlp", "--version"], returncode=0, stdout="ok", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = YtDlpAdapter(
        binary="yt-dlp", timeout_seconds=1, retries=1, backoff_seconds=0
    )
    result = adapter._run(["--version"], retry=True)
    assert result.stdout == "ok"
    assert calls["count"] == 2


def test_ytdlp_timeout_exhaustion_raises_runtime_error(monkeypatch) -> None:
    def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        raise subprocess.TimeoutExpired(cmd="yt-dlp", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = YtDlpAdapter(
        binary="yt-dlp", timeout_seconds=1, retries=1, backoff_seconds=0
    )
    with pytest.raises(RuntimeError, match="yt_dlp_timeout"):
        adapter._run(["--version"], retry=True)


def test_list_videos_handles_direct_watch_url_payload(monkeypatch) -> None:
    payload = {
        "id": "i6idieq9bso",
        "title": "My Favorite Scripture: On My Worst Day",
        "channel": "NCOC Live",
        "channel_id": "channel123",
        "timestamp": 1700000000,
        "duration": 1200,
    }
    adapter = YtDlpAdapter(binary="yt-dlp")
    monkeypatch.setattr(adapter, "_run_json", lambda args: payload)
    videos = adapter.list_videos("https://www.youtube.com/watch?v=i6idieq9bso")
    assert len(videos) == 1
    assert videos[0].video_id == "i6idieq9bso"
    assert videos[0].title.startswith("My Favorite Scripture")
