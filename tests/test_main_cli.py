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
        channel_url=[],
        video_url=[],
        video_file=[],
        from_date=None,
        to_date=None,
        reprocess=False,
        article=False,
        asr_fallback=False,
        force_asr=False,
        clip_start=None,
        clip_end=None,
        env_file=str(tmp_path / "missing.env"),
    )
    assert main_mod.run_command(args) == 0


def test_run_command_requires_config_or_url(tmp_path) -> None:
    args = Namespace(
        command="run",
        config=str(tmp_path / "missing.toml"),
        url=[],
        channel_url=[],
        video_url=[],
        video_file=[],
        from_date=None,
        to_date=None,
        reprocess=False,
        article=False,
        asr_fallback=False,
        force_asr=False,
        clip_start=None,
        clip_end=None,
        env_file=str(tmp_path / "missing.env"),
    )
    with pytest.raises(SystemExit, match="Config file not found"):
        main_mod.run_command(args)


def test_cli_url_inference_splits_channel_and_video_targets() -> None:
    base = main_mod.default_config_from_env()
    config = main_mod._with_cli_targets(  # noqa: SLF001
        base,
        urls=[
            "https://www.youtube.com/watch?v=i6idieq9bso",
            "https://www.youtube.com/@Lunduke/videos",
        ],
        channel_urls=[],
        video_urls=[],
        video_files=[],
        clip_start="00:10:00",
        clip_end="00:20:00",
        force_asr=True,
    )
    assert len(config.channels) == 1
    assert len(config.videos) == 1
    assert config.channels[0].url == "https://www.youtube.com/@Lunduke/videos"
    assert config.videos[0].url == "https://www.youtube.com/watch?v=i6idieq9bso"
    assert config.videos[0].clip_start == "00:10:00"
    assert config.videos[0].clip_end == "00:20:00"
    assert config.videos[0].force_asr is True


def test_cli_file_targets_are_supported() -> None:
    base = main_mod.default_config_from_env()
    config = main_mod._with_cli_targets(  # noqa: SLF001
        base,
        urls=[],
        channel_urls=[],
        video_urls=[],
        video_files=["/tmp/demo.mp4"],
        clip_start="00:00:10",
        clip_end="00:00:20",
        force_asr=False,
    )
    assert len(config.files) == 1
    assert config.files[0].path == "/tmp/demo.mp4"
    assert config.files[0].name == "demo"
    assert config.files[0].clip_start == "00:00:10"
    assert config.files[0].clip_end == "00:00:20"


def test_tutorial_command_uses_bundle_without_config(monkeypatch, tmp_path) -> None:
    class _FakeLLM:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeRegistry:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakePipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            from lunduke_transcripts.domain.models import TutorialSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            manifest_path = tutorial_dir / "tutorial_manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            return TutorialSummary(
                status="awaiting_outline_approval",
                tutorial_dir=tutorial_dir,
                manifest_path=manifest_path,
                human_outline_approved=False,
                publish_eligible=False,
            )

    monkeypatch.setattr(main_mod, "LLMAdapter", _FakeLLM)
    monkeypatch.setattr(main_mod, "TutorialAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(main_mod, "TutorialPipeline", _FakePipeline)

    bundle_path = tmp_path / "tutorial_asset_bundle.json"
    bundle_path.write_text("{}", encoding="utf-8")
    args = Namespace(
        command="tutorial",
        bundle=str(bundle_path),
        config=str(tmp_path / "missing.toml"),
        env_file=str(tmp_path / "missing.env"),
        approve_outline=False,
        reprocess=False,
        max_review_cycles=1,
        agents_dir=str(tmp_path / "agents"),
        skills_dir=str(tmp_path / "skills"),
    )

    assert main_mod.tutorial_command(args) == 0


def test_tutorial_command_renders_pdf_after_publish(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class _FakeLLM:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeRegistry:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeTutorialPipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            from lunduke_transcripts.domain.models import TutorialSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            manifest_path = tutorial_dir / "tutorial_manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            return TutorialSummary(
                status="published",
                tutorial_dir=tutorial_dir,
                manifest_path=manifest_path,
                human_outline_approved=True,
                publish_eligible=True,
            )

    class _FakeRenderPipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            captured["render_init"] = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            captured["render_run"] = kwargs
            from lunduke_transcripts.domain.models import RenderSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            render_manifest_path = tutorial_dir / "render_manifest.json"
            render_manifest_path.write_text("{}", encoding="utf-8")
            output_path = tutorial_dir / "tutorial_final.pdf"
            output_path.write_text("pdf", encoding="utf-8")
            return RenderSummary(
                status="success",
                tutorial_dir=tutorial_dir,
                render_manifest_path=render_manifest_path,
                target="pdf",
                html_path=tutorial_dir / "tutorial_final.html",
                output_path=output_path,
            )

    monkeypatch.setattr(main_mod, "LLMAdapter", _FakeLLM)
    monkeypatch.setattr(main_mod, "TutorialAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(main_mod, "TutorialPipeline", _FakeTutorialPipeline)
    monkeypatch.setattr(main_mod, "TutorialRenderPipeline", _FakeRenderPipeline)

    bundle_path = tmp_path / "tutorial_asset_bundle.json"
    bundle_path.write_text("{}", encoding="utf-8")
    args = Namespace(
        command="tutorial",
        bundle=str(bundle_path),
        config=str(tmp_path / "missing.toml"),
        env_file=str(tmp_path / "missing.env"),
        approve_outline=True,
        reprocess=False,
        max_review_cycles=1,
        agents_dir=str(tmp_path / "agents"),
        skills_dir=str(tmp_path / "skills"),
    )

    assert main_mod.tutorial_command(args) == 0
    assert captured["render_run"] == {
        "manifest_path": tmp_path / "tutorial" / "tutorial_manifest.json",
        "target": "pdf",
    }


def test_tutorial_command_fails_when_publish_render_fails(
    monkeypatch, tmp_path
) -> None:
    class _FakeLLM:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeRegistry:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeTutorialPipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            from lunduke_transcripts.domain.models import TutorialSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            manifest_path = tutorial_dir / "tutorial_manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            return TutorialSummary(
                status="published",
                tutorial_dir=tutorial_dir,
                manifest_path=manifest_path,
                human_outline_approved=True,
                publish_eligible=True,
            )

    class _FailingRenderPipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            from lunduke_transcripts.domain.models import RenderSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            render_manifest_path = tutorial_dir / "render_manifest.json"
            render_manifest_path.write_text("{}", encoding="utf-8")
            return RenderSummary(
                status="failed",
                tutorial_dir=tutorial_dir,
                render_manifest_path=render_manifest_path,
                target="pdf",
                failures=["required_binary_missing: pandoc"],
            )

    monkeypatch.setattr(main_mod, "LLMAdapter", _FakeLLM)
    monkeypatch.setattr(main_mod, "TutorialAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(main_mod, "TutorialPipeline", _FakeTutorialPipeline)
    monkeypatch.setattr(main_mod, "TutorialRenderPipeline", _FailingRenderPipeline)

    bundle_path = tmp_path / "tutorial_asset_bundle.json"
    bundle_path.write_text("{}", encoding="utf-8")
    args = Namespace(
        command="tutorial",
        bundle=str(bundle_path),
        config=str(tmp_path / "missing.toml"),
        env_file=str(tmp_path / "missing.env"),
        approve_outline=True,
        reprocess=False,
        max_review_cycles=1,
        agents_dir=str(tmp_path / "agents"),
        skills_dir=str(tmp_path / "skills"),
    )

    assert main_mod.tutorial_command(args) == 1


def test_tutorial_command_resolves_router_paths_relative_to_config(
    monkeypatch, tmp_path
) -> None:
    captured: dict[str, object] = {}

    class _FakeLLM:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            captured.update(kwargs)

    class _FakeRegistry:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakePipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            from lunduke_transcripts.domain.models import TutorialSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            manifest_path = tutorial_dir / "tutorial_manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            return TutorialSummary(
                status="awaiting_outline_approval",
                tutorial_dir=tutorial_dir,
                manifest_path=manifest_path,
                human_outline_approved=False,
                publish_eligible=False,
            )

    monkeypatch.setattr(main_mod, "LLMAdapter", _FakeLLM)
    monkeypatch.setattr(main_mod, "TutorialAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(main_mod, "TutorialPipeline", _FakePipeline)

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "channels.toml"
    config_path.write_text(
        """
[llm]
provider = "openrouter"
model = "openai/gpt-4.1-mini"
router_enabled = true
router_repo_path = "../lee-llm-router"
router_config_path = "tutorial-llm-router.yaml"
router_trace_dir = "../traces"

[llm.router_roles]
"tutorial.writer" = "tutorial_writer"
""".strip() + "\n",
        encoding="utf-8",
    )

    bundle_path = tmp_path / "tutorial_asset_bundle.json"
    bundle_path.write_text("{}", encoding="utf-8")
    args = Namespace(
        command="tutorial",
        bundle=str(bundle_path),
        config=str(config_path),
        env_file=str(tmp_path / "missing.env"),
        approve_outline=False,
        reprocess=False,
        max_review_cycles=1,
        agents_dir=str(tmp_path / "agents"),
        skills_dir=str(tmp_path / "skills"),
    )

    assert main_mod.tutorial_command(args) == 0
    assert captured["router_repo_path"] == str(
        (config_dir / "../lee-llm-router").resolve()
    )
    assert captured["router_config_path"] == str(
        (config_dir / "tutorial-llm-router.yaml").resolve()
    )
    assert captured["router_trace_dir"] == str((config_dir / "../traces").resolve())


def test_resolve_config_relative_path_falls_back_to_repo_root(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    resolved = main_mod._resolve_config_relative_path(  # noqa: SLF001
        "config/tutorial-llm-router.yaml",
        config_dir,
    )

    assert resolved == str(
        (
            main_mod._repo_root() / "config/tutorial-llm-router.yaml"
        ).resolve()  # noqa: SLF001
    )


def test_tutorial_command_reports_runtime_failure(monkeypatch, tmp_path) -> None:
    class _FakeLLM:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FakeRegistry:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

    class _FailingPipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            raise RuntimeError("tutorial_generation_requires_llm_configuration")

    monkeypatch.setattr(main_mod, "LLMAdapter", _FakeLLM)
    monkeypatch.setattr(main_mod, "TutorialAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(main_mod, "TutorialPipeline", _FailingPipeline)

    bundle_path = tmp_path / "tutorial_asset_bundle.json"
    bundle_path.write_text("{}", encoding="utf-8")
    args = Namespace(
        command="tutorial",
        bundle=str(bundle_path),
        config=str(tmp_path / "missing.toml"),
        env_file=str(tmp_path / "missing.env"),
        approve_outline=False,
        reprocess=False,
        max_review_cycles=1,
        agents_dir=str(tmp_path / "agents"),
        skills_dir=str(tmp_path / "skills"),
    )

    assert main_mod.tutorial_command(args) == 1


def test_render_command_uses_manifest_without_config(monkeypatch, tmp_path) -> None:
    class _FakePipeline:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs

        def run(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            from lunduke_transcripts.domain.models import RenderSummary

            tutorial_dir = tmp_path / "tutorial"
            tutorial_dir.mkdir(exist_ok=True)
            render_manifest_path = tutorial_dir / "render_manifest.json"
            render_manifest_path.write_text("{}", encoding="utf-8")
            return RenderSummary(
                status="success",
                tutorial_dir=tutorial_dir,
                render_manifest_path=render_manifest_path,
                target="pdf",
                html_path=tutorial_dir / "tutorial_final.html",
                output_path=tutorial_dir / "tutorial_final.pdf",
            )

    monkeypatch.setattr(main_mod, "TutorialRenderPipeline", _FakePipeline)

    manifest_path = tmp_path / "tutorial_manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    args = Namespace(
        command="render",
        manifest=str(manifest_path),
        target="pdf",
        config=str(tmp_path / "missing.toml"),
        env_file=str(tmp_path / "missing.env"),
    )

    assert main_mod.render_command(args) == 0
