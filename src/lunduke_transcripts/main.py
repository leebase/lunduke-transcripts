"""CLI entry point for lunduke-transcripts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from lunduke_transcripts import __version__
from lunduke_transcripts.app.orchestrator import Orchestrator
from lunduke_transcripts.config import load_config, load_env_file
from lunduke_transcripts.domain.models import RunOptions
from lunduke_transcripts.infra.llm_adapter import LLMAdapter
from lunduke_transcripts.infra.storage import Storage
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
        "--env-file",
        default=".env",
        help="Path to env file for provider/model/API keys (default: .env)",
    )
    return parser


def run_command(args: argparse.Namespace) -> int:
    """Execute the run pipeline command."""

    load_env_file(args.env_file)
    config = load_config(args.config)
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
        timeout_seconds=config.app.yt_dlp_timeout_seconds,
        retries=config.app.fetch_retries,
        backoff_seconds=config.app.retry_backoff_seconds,
    )
    llm = LLMAdapter(
        provider=config.llm.provider,
        model=config.llm.model,
        prompt_version=config.llm.prompt_version,
        timeout_seconds=config.llm.timeout_seconds,
        retries=config.llm.retries,
        retry_backoff_seconds=config.llm.retry_backoff_seconds,
    )
    orchestrator = Orchestrator(
        config=config, storage=storage, youtube=youtube, llm=llm
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


def main() -> None:
    """Entry point for console script."""

    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        raise SystemExit(run_command(args))
    parser.print_help()
    raise SystemExit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
