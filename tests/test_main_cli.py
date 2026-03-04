from __future__ import annotations

from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import lunduke_transcripts.main as main_mod
from lunduke_transcripts.domain.models import RunSummary


def test_derive_channel_name_watch_url() -> None:
    name = main_mod._derive_channel_name(  # noqa: SLF001
        "https://www.youtube.com/watch?v=i6idieq9bso&t=4370s", 1
    )
    assert name == "video-i6idieq9bso"


def test_run_command_accepts_url_without_config(monkeypatch, tmp_path) -> None:
    class _FakeStorage:
        def __init__(self, data_dir: Path) -> None:
            self.data_dir = data_dir

    class _FakeYtDlp:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeLLM:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeOrchestrator:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, options):  # noqa: ANN001
            _ = options
            now = datetime.now(tz=UTC)
            return RunSummary(
                run_id="r1",
                started_at=now,
                finished_at=now,
                status="success",
                videos_seen=1,
                videos_new=1,
                videos_processed=1,
                videos_failed=0,
                failures=[],
            )

    monkeypatch.setattr(main_mod, "Storage", _FakeStorage)
    monkeypatch.setattr(main_mod, "YtDlpAdapter", _FakeYtDlp)
    monkeypatch.setattr(main_mod, "LLMAdapter", _FakeLLM)
    monkeypatch.setattr(main_mod, "Orchestrator", _FakeOrchestrator)

    args = Namespace(
        command="run",
        config=str(tmp_path / "missing.toml"),
        url=["https://www.youtube.com/watch?v=i6idieq9bso"],
        from_date=None,
        to_date=None,
        reprocess=False,
        article=False,
        env_file=str(tmp_path / "missing.env"),
    )
    assert main_mod.run_command(args) == 0


def test_run_command_requires_config_or_url(tmp_path) -> None:
    args = Namespace(
        command="run",
        config=str(tmp_path / "missing.toml"),
        url=[],
        from_date=None,
        to_date=None,
        reprocess=False,
        article=False,
        env_file=str(tmp_path / "missing.env"),
    )
    with pytest.raises(SystemExit, match="Config file not found"):
        main_mod.run_command(args)
