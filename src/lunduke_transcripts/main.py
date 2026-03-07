"""CLI entry point for lunduke-transcripts."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime, time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from lunduke_transcripts import __version__
from lunduke_transcripts.app.orchestrator import Orchestrator
from lunduke_transcripts.app.tutorial_agent_registry import TutorialAgentRegistry
from lunduke_transcripts.app.tutorial_pipeline import TutorialPipeline
from lunduke_transcripts.app.tutorial_render_pipeline import TutorialRenderPipeline
from lunduke_transcripts.config import (
    ChannelConfig,
    Config,
    FileConfig,
    VideoConfig,
    default_config_from_env,
    load_config,
    load_env_file,
)
from lunduke_transcripts.domain.models import RenderSummary, RunOptions
from lunduke_transcripts.infra.asr_plugins.registry import build_asr_plugin
from lunduke_transcripts.infra.llm_adapter import LLMAdapter
from lunduke_transcripts.infra.local_media_adapter import LocalMediaAdapter
from lunduke_transcripts.infra.storage import Storage
from lunduke_transcripts.infra.video_frame_extractor import VideoFrameExtractor
from lunduke_transcripts.infra.youtube_adapter import YtDlpAdapter


def _parse_date(value: str, tz_name: str, *, end_of_day: bool) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:  # noqa: PERF203
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}', expected YYYY-MM-DD"
        ) from exc
    zone = ZoneInfo(tz_name)
    dt = datetime.combine(parsed, time.max if end_of_day else time.min, tzinfo=zone)
    return dt.astimezone(UTC)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(
        prog="lunduke-transcripts",
        description="Download exact and cleaned transcripts for YouTube channels.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run transcript pipeline")
    run_parser.add_argument(
        "--config",
        default="config/channels.toml",
        help="Path to TOML config (default: config/channels.toml)",
    )
    run_parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="Direct YouTube target URL (video/channel/playlist). Can be repeated.",
    )
    run_parser.add_argument(
        "--channel-url",
        action="append",
        default=[],
        help="Explicit YouTube channel/videos URL target. Can be repeated.",
    )
    run_parser.add_argument(
        "--video-url",
        action="append",
        default=[],
        help="Explicit single YouTube video URL target. Can be repeated.",
    )
    run_parser.add_argument(
        "--video-file",
        action="append",
        default=[],
        help="Explicit local video file target. Can be repeated.",
    )
    run_parser.add_argument(
        "--from", dest="from_date", help="Published date start (YYYY-MM-DD)"
    )
    run_parser.add_argument(
        "--to", dest="to_date", help="Published date end (YYYY-MM-DD)"
    )
    run_parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Reprocess videos even if previously handled",
    )
    run_parser.add_argument(
        "--article",
        action="store_true",
        help="Generate a faithful news-style article from the exact transcript",
    )
    run_parser.add_argument(
        "--asr-fallback",
        action="store_true",
        help="Enable ASR fallback when captions are unavailable",
    )
    run_parser.add_argument(
        "--force-asr",
        action="store_true",
        help="Force ASR path even when captions are available",
    )
    run_parser.add_argument(
        "--clip-start",
        help="Optional clip start for CLI video targets (HH:MM:SS)",
    )
    run_parser.add_argument(
        "--clip-end",
        help="Optional clip end for CLI video targets (HH:MM:SS)",
    )
    run_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file for provider/model/API keys (default: .env)",
    )

    tutorial_parser = subparsers.add_parser(
        "tutorial",
        help="Generate tutorial artifacts from a tutorial asset bundle",
    )
    tutorial_parser.add_argument(
        "--bundle",
        required=True,
        help="Path to tutorial_asset_bundle.json",
    )
    tutorial_parser.add_argument(
        "--config",
        default="config/channels.toml",
        help="Path to TOML config for LLM settings (default: config/channels.toml)",
    )
    tutorial_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file for provider/model/API keys (default: .env)",
    )
    tutorial_parser.add_argument(
        "--approve-outline",
        action="store_true",
        help="Mark the outline package as human-approved and continue the pipeline",
    )
    tutorial_parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-run tutorial generation even if cached outputs match",
    )
    tutorial_parser.add_argument(
        "--max-review-cycles",
        type=int,
        default=1,
        help="Maximum automatic review-response cycles (default: 1)",
    )
    tutorial_parser.add_argument(
        "--agents-dir",
        default=str(_repo_root() / "agents"),
        help="Directory containing tutorial agent role files",
    )
    tutorial_parser.add_argument(
        "--skills-dir",
        default=str(_repo_root() / "skills"),
        help="Directory containing tutorial skill files",
    )
    tutorial_parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Publish Markdown only and skip the automatic downstream HTML/PDF render",
    )

    render_parser = subparsers.add_parser(
        "render",
        help="Render a published tutorial manifest into downstream formats",
    )
    render_parser.add_argument(
        "--manifest",
        required=True,
        help="Path to tutorial_manifest.json",
    )
    render_parser.add_argument(
        "--target",
        choices=["pdf"],
        default="pdf",
        help="Render target (default: pdf)",
    )
    render_parser.add_argument(
        "--config",
        default="config/channels.toml",
        help=(
            "Path to TOML config for renderer settings "
            "(default: config/channels.toml)"
        ),
    )
    render_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file for renderer overrides (default: .env)",
    )
    return parser


def _derive_channel_name(url: str, idx: int) -> str:
    parsed = urlparse(url)
    if parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            return f"video-{video_id}"
    if parsed.path:
        tail = parsed.path.rstrip("/").split("/")[-1]
        if tail:
            return tail
    return f"url-target-{idx}"


def _derive_video_name(url: str, idx: int) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        tail = parsed.path.strip("/")
        if tail:
            return f"video-{tail}"
    if parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            return f"video-{video_id}"
    parts = [part for part in parsed.path.split("/") if part]
    if "shorts" in parts:
        shorts_idx = parts.index("shorts")
        if shorts_idx + 1 < len(parts):
            return f"video-{parts[shorts_idx + 1]}"
    return f"video-target-{idx}"


def _derive_file_name(path: str, idx: int) -> str:
    value = Path(path).expanduser()
    if value.stem:
        return value.stem
    return f"file-target-{idx}"


def _is_video_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return bool(parsed.path.strip("/"))
    if parsed.path == "/watch":
        return bool(parse_qs(parsed.query).get("v"))
    parts = [part for part in parsed.path.split("/") if part]
    return "shorts" in parts


def _with_cli_targets(
    config: Config,
    urls: list[str],
    channel_urls: list[str],
    video_urls: list[str],
    video_files: list[str],
    clip_start: str | None,
    clip_end: str | None,
    force_asr: bool,
) -> Config:
    inferred_channels: list[str] = []
    inferred_videos: list[str] = []
    for url in urls:
        if _is_video_url(url):
            inferred_videos.append(url)
        else:
            inferred_channels.append(url)

    effective_channel_urls = [*channel_urls, *inferred_channels]
    effective_video_urls = [*video_urls, *inferred_videos]

    channels = [
        ChannelConfig(
            name=_derive_channel_name(url, idx),
            url=url,
            language=config.app.default_language,
        )
        for idx, url in enumerate(effective_channel_urls, start=1)
    ]
    videos = [
        VideoConfig(
            name=_derive_video_name(url, idx),
            url=url,
            language=config.app.default_language,
            clip_start=clip_start,
            clip_end=clip_end,
            force_asr=True if force_asr else None,
        )
        for idx, url in enumerate(effective_video_urls, start=1)
    ]
    files = [
        FileConfig(
            name=_derive_file_name(path, idx),
            path=path,
            language=config.app.default_language,
            clip_start=clip_start,
            clip_end=clip_end,
            force_asr=True if force_asr else None,
        )
        for idx, path in enumerate(video_files, start=1)
    ]
    return Config(
        app=config.app,
        llm=config.llm,
        channels=channels,
        videos=videos,
        files=files,
    )


def run_command(args: argparse.Namespace) -> int:
    """Execute the run pipeline command."""

    load_env_file(args.env_file)
    has_cli_targets = bool(
        args.url or args.channel_url or args.video_url or args.video_file
    )
    config_path = Path(args.config)
    if config_path.exists():
        config = load_config(config_path)
    elif has_cli_targets:
        config = default_config_from_env()
    else:
        raise SystemExit(
            f"Config file not found: {config_path}. Provide --config or pass "
            "--url/--channel-url/--video-url/--video-file."
        )
    if has_cli_targets:
        config = _with_cli_targets(
            config=config,
            urls=args.url,
            channel_urls=args.channel_url,
            video_urls=args.video_url,
            video_files=args.video_file,
            clip_start=args.clip_start,
            clip_end=args.clip_end,
            force_asr=bool(args.force_asr),
        )
    app_cfg = config.app
    if args.asr_fallback:
        app_cfg = replace(app_cfg, enable_asr_fallback=True)
    if args.force_asr:
        app_cfg = replace(app_cfg, force_asr=True)
    if app_cfg is not config.app:
        config = Config(
            app=app_cfg,
            llm=config.llm,
            channels=config.channels,
            videos=config.videos,
            files=config.files,
        )
    if not config.channels and not config.videos and not config.files:
        raise SystemExit(
            "No targets configured. Add [[channels]]/[[videos]]/[[files]] in config "
            "or pass --url/--channel-url/--video-url/--video-file values."
        )
    from_utc = (
        _parse_date(args.from_date, config.app.timezone, end_of_day=False)
        if args.from_date
        else None
    )
    to_utc = (
        _parse_date(args.to_date, config.app.timezone, end_of_day=True)
        if args.to_date
        else None
    )
    if from_utc and to_utc and from_utc > to_utc:
        raise SystemExit("--from must be less than or equal to --to")

    storage = Storage(config.app.data_dir)
    youtube = YtDlpAdapter(
        binary=config.app.yt_dlp_binary,
        ffmpeg_binary=config.app.ffmpeg_binary,
        timeout_seconds=config.app.yt_dlp_timeout_seconds,
        ffmpeg_timeout_seconds=config.app.ffmpeg_timeout_seconds,
        retries=config.app.fetch_retries,
        backoff_seconds=config.app.retry_backoff_seconds,
    )
    asr_plugin = build_asr_plugin(config.app)
    router_repo_path = _resolve_config_relative_path(
        config.llm.router_repo_path,
        config_path.parent,
    )
    router_config_path = _resolve_config_relative_path(
        config.llm.router_config_path,
        config_path.parent,
    )
    router_trace_dir = _resolve_config_relative_path(
        config.llm.router_trace_dir,
        config_path.parent,
    )
    llm = LLMAdapter(
        provider=config.llm.provider,
        model=config.llm.model,
        prompt_version=config.llm.prompt_version,
        timeout_seconds=config.llm.timeout_seconds,
        retries=config.llm.retries,
        retry_backoff_seconds=config.llm.retry_backoff_seconds,
        router_enabled=config.llm.router_enabled,
        router_repo_path=router_repo_path,
        router_config_path=router_config_path,
        router_trace_dir=router_trace_dir,
        router_roles=config.llm.router_roles,
    )
    local_media = LocalMediaAdapter(
        ffmpeg_binary=config.app.ffmpeg_binary,
        ffprobe_binary=config.app.ffprobe_binary,
        ffmpeg_timeout_seconds=config.app.ffmpeg_timeout_seconds,
    )
    frame_extractor = VideoFrameExtractor(
        ffmpeg_binary=config.app.ffmpeg_binary,
        threshold=config.app.frame_capture_threshold,
        image_format=config.app.frame_image_format,
        timeout_seconds=config.app.ffmpeg_timeout_seconds,
    )
    orchestrator = Orchestrator(
        config=config,
        storage=storage,
        youtube=youtube,
        llm=llm,
        asr_plugin=asr_plugin,
        local_media=local_media,
        frame_extractor=frame_extractor,
    )
    summary = orchestrator.run(
        RunOptions(
            config_path=Path(args.config),
            from_utc=from_utc,
            to_utc=to_utc,
            reprocess=bool(args.reprocess),
            generate_article=bool(args.article),
        )
    )

    payload = {
        "run_id": summary.run_id,
        "status": summary.status,
        "videos_seen": summary.videos_seen,
        "videos_new": summary.videos_new,
        "videos_processed": summary.videos_processed,
        "videos_failed": summary.videos_failed,
        "started_at": summary.started_at.isoformat(),
        "finished_at": summary.finished_at.isoformat(),
        "failures": summary.failures,
    }
    print(json.dumps(payload, indent=2))
    return 0 if summary.status in {"success", "partial"} else 1


def tutorial_command(args: argparse.Namespace) -> int:
    """Execute the multi-agent tutorial generation pipeline."""

    load_env_file(args.env_file)
    config_path = Path(args.config)
    if config_path.exists():
        config = load_config(config_path)
    else:
        config = default_config_from_env()
    router_repo_path = _resolve_config_relative_path(
        config.llm.router_repo_path,
        config_path.parent,
    )
    router_config_path = _resolve_config_relative_path(
        config.llm.router_config_path,
        config_path.parent,
    )
    router_trace_dir = _resolve_config_relative_path(
        config.llm.router_trace_dir,
        config_path.parent,
    )
    llm = LLMAdapter(
        provider=config.llm.provider,
        model=config.llm.model,
        prompt_version=config.llm.prompt_version,
        timeout_seconds=config.llm.timeout_seconds,
        retries=config.llm.retries,
        retry_backoff_seconds=config.llm.retry_backoff_seconds,
        router_enabled=config.llm.router_enabled,
        router_repo_path=router_repo_path,
        router_config_path=router_config_path,
        router_trace_dir=router_trace_dir,
        router_roles=config.llm.router_roles,
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=Path(args.agents_dir).expanduser().resolve(),
            skills_dir=Path(args.skills_dir).expanduser().resolve(),
        ),
    )
    render_summary: RenderSummary | None = None
    try:
        summary = pipeline.run(
            bundle_path=Path(args.bundle),
            approve_outline=bool(args.approve_outline),
            reprocess=bool(args.reprocess),
            max_review_cycles=max(int(args.max_review_cycles), 0),
        )
        render_attempted = summary.status == "published" and not bool(args.skip_render)
        if render_attempted:
            render_summary = _build_render_pipeline(config=config).run(
                manifest_path=summary.manifest_path,
                target="pdf",
            )
        overall_status = _tutorial_command_status(
            tutorial_status=summary.status,
            render_summary=render_summary,
            render_skipped=bool(args.skip_render),
        )
        payload = {
            "status": overall_status,
            "tutorial_status": summary.status,
            "tutorial_dir": str(summary.tutorial_dir),
            "manifest_path": str(summary.manifest_path),
            "human_outline_approved": summary.human_outline_approved,
            "publish_eligible": summary.publish_eligible,
            "reused_cached_outputs": summary.reused_cached_outputs,
            "review_cycles": summary.review_cycles,
            "failures": summary.failures,
            "render_attempted": render_attempted,
            "render_status": _tutorial_render_status(
                tutorial_status=summary.status,
                render_summary=render_summary,
                render_skipped=bool(args.skip_render),
            ),
            "render_manifest_path": (
                str(render_summary.render_manifest_path) if render_summary else None
            ),
            "render_output_path": (
                str(render_summary.output_path)
                if render_summary and render_summary.output_path
                else None
            ),
            "render_failures": render_summary.failures if render_summary else [],
        }
        print(json.dumps(payload, indent=2))
        return 1 if overall_status == "partial" else 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "status": "failed",
                    "bundle": str(Path(args.bundle).expanduser()),
                    "error": str(exc),
                },
                indent=2,
            )
        )
        return 1


def render_command(args: argparse.Namespace) -> int:
    """Render a published tutorial manifest into downstream document formats."""

    load_env_file(args.env_file)
    config_path = Path(args.config)
    if config_path.exists():
        config = load_config(config_path)
    else:
        config = default_config_from_env()

    pipeline = _build_render_pipeline(config=config)
    summary = pipeline.run(
        manifest_path=Path(args.manifest),
        target=str(args.target),
    )
    payload = {
        "status": summary.status,
        "target": summary.target,
        "tutorial_dir": str(summary.tutorial_dir),
        "render_manifest_path": str(summary.render_manifest_path),
        "html_path": str(summary.html_path) if summary.html_path else None,
        "output_path": str(summary.output_path) if summary.output_path else None,
        "failures": summary.failures,
    }
    print(json.dumps(payload, indent=2))
    return 0 if summary.status == "success" else 1


def _build_render_pipeline(*, config: Config) -> TutorialRenderPipeline:
    return TutorialRenderPipeline(
        pandoc_binary=config.app.pandoc_binary,
        pdf_engine=config.app.pdf_engine,
        pdf_engine_binary=config.app.pdf_engine_binary,
        renderer_dir=_repo_root() / "renderers",
    )


def _tutorial_command_status(
    *,
    tutorial_status: str,
    render_summary: RenderSummary | None,
    render_skipped: bool,
) -> str:
    if tutorial_status != "published":
        return tutorial_status
    if render_summary is None:
        return "published"
    if render_summary.status == "success":
        return "published"
    if render_skipped:
        return "published"
    return "partial"


def _tutorial_render_status(
    *,
    tutorial_status: str,
    render_summary: RenderSummary | None,
    render_skipped: bool,
) -> str | None:
    if render_summary is not None:
        return render_summary.status
    if tutorial_status == "published" and render_skipped:
        return "skipped"
    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_config_relative_path(value: str | None, config_dir: Path) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path)
    config_relative = (config_dir / path).resolve()
    if config_relative.exists():
        return str(config_relative)
    repo_relative = (_repo_root() / path).resolve()
    if path.parts[:1] == ("config",) and repo_relative.exists():
        return str(repo_relative)
    return str(config_relative)


def main() -> None:
    """Entry point for console script."""

    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        raise SystemExit(run_command(args))
    if args.command == "tutorial":
        raise SystemExit(tutorial_command(args))
    if args.command == "render":
        raise SystemExit(render_command(args))
    parser.print_help()
    raise SystemExit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
