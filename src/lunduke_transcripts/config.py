"""Configuration loading and validation."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    """Application-level runtime settings."""

    data_dir: Path = Path("data")
    default_language: str = "en"
    timezone: str = "America/Chicago"
    enable_cleanup: bool = True
    enable_article: bool = False
    yt_dlp_binary: str = "yt-dlp"
    yt_dlp_timeout_seconds: int = 120
    fetch_retries: int = 2
    retry_backoff_seconds: int = 2
    max_videos_per_channel: int | None = None
    enable_asr_fallback: bool = False
    force_asr: bool = False
    asr_provider: str = "fast-whisper"
    asr_model: str = "small.en"
    asr_device: str = "auto"
    asr_compute_type: str = "auto"
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    ffmpeg_timeout_seconds: int = 300
    keep_audio_files: bool = False
    frame_capture_enabled: bool = True
    frame_capture_threshold: float = 0.25
    frame_image_format: str = "jpg"
    pandoc_binary: str = "pandoc"
    pdf_engine: str = "chromium"
    pdf_engine_binary: str = "chromium"


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider settings."""

    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    prompt_version: str = "v1"
    timeout_seconds: int = 60
    retries: int = 2
    retry_backoff_seconds: int = 2
    router_enabled: bool = False
    router_repo_path: str | None = None
    router_config_path: str | None = None
    router_trace_dir: str | None = None
    router_roles: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChannelConfig:
    """Channel source configuration."""

    name: str
    url: str
    language: str | None = None


@dataclass(frozen=True)
class VideoConfig:
    """Single video source configuration."""

    name: str
    url: str
    language: str | None = None
    clip_start: str | None = None
    clip_end: str | None = None
    force_asr: bool | None = None


@dataclass(frozen=True)
class FileConfig:
    """Local file source configuration."""

    name: str
    path: str
    language: str | None = None
    clip_start: str | None = None
    clip_end: str | None = None
    force_asr: bool | None = None


@dataclass(frozen=True)
class Config:
    """Top-level app configuration."""

    app: AppConfig = field(default_factory=AppConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    channels: list[ChannelConfig] = field(default_factory=list)
    videos: list[VideoConfig] = field(default_factory=list)
    files: list[FileConfig] = field(default_factory=list)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_bool(raw: str | bool | None, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_optional_bool(raw: str | bool | None) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


def load_env_file(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs into environment without overriding existing vars."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _build_config(
    app_raw: dict[str, Any],
    llm_raw: dict[str, Any],
    channels_raw: list[dict[str, Any]],
    videos_raw: list[dict[str, Any]],
    files_raw: list[dict[str, Any]],
) -> Config:
    app = AppConfig(
        data_dir=Path(app_raw.get("data_dir", "data")),
        default_language=str(app_raw.get("default_language", "en")),
        timezone=str(app_raw.get("timezone", "America/Chicago")),
        enable_cleanup=_parse_bool(
            os.getenv("ENABLE_CLEANUP"),
            _parse_bool(app_raw.get("enable_cleanup"), True),
        ),
        enable_article=_parse_bool(
            os.getenv("ENABLE_ARTICLE"),
            _parse_bool(app_raw.get("enable_article"), False),
        ),
        yt_dlp_binary=str(app_raw.get("yt_dlp_binary", "yt-dlp")),
        yt_dlp_timeout_seconds=int(
            app_raw.get(
                "yt_dlp_timeout_seconds",
                os.getenv("YT_DLP_TIMEOUT_SECONDS", 120),
            )
        ),
        fetch_retries=int(app_raw.get("fetch_retries", 2)),
        retry_backoff_seconds=int(app_raw.get("retry_backoff_seconds", 2)),
        max_videos_per_channel=(
            int(app_raw["max_videos_per_channel"])
            if app_raw.get("max_videos_per_channel") is not None
            else None
        ),
        enable_asr_fallback=_parse_bool(
            os.getenv("ENABLE_ASR_FALLBACK"),
            _parse_bool(app_raw.get("enable_asr_fallback"), False),
        ),
        force_asr=_parse_bool(
            os.getenv("FORCE_ASR"),
            _parse_bool(app_raw.get("force_asr"), False),
        ),
        asr_provider=str(
            os.getenv("ASR_PROVIDER", app_raw.get("asr_provider", "fast-whisper"))
        ),
        asr_model=str(os.getenv("ASR_MODEL", app_raw.get("asr_model", "small.en"))),
        asr_device=str(os.getenv("ASR_DEVICE", app_raw.get("asr_device", "auto"))),
        asr_compute_type=str(
            os.getenv("ASR_COMPUTE_TYPE", app_raw.get("asr_compute_type", "auto"))
        ),
        ffmpeg_binary=str(app_raw.get("ffmpeg_binary", "ffmpeg")),
        ffprobe_binary=str(app_raw.get("ffprobe_binary", "ffprobe")),
        ffmpeg_timeout_seconds=int(
            app_raw.get(
                "ffmpeg_timeout_seconds",
                os.getenv("FFMPEG_TIMEOUT_SECONDS", 300),
            )
        ),
        keep_audio_files=_parse_bool(
            os.getenv("KEEP_AUDIO_FILES"),
            _parse_bool(app_raw.get("keep_audio_files"), False),
        ),
        frame_capture_enabled=_parse_bool(
            os.getenv("FRAME_CAPTURE_ENABLED"),
            _parse_bool(app_raw.get("frame_capture_enabled"), True),
        ),
        frame_capture_threshold=float(
            app_raw.get(
                "frame_capture_threshold",
                os.getenv("FRAME_CAPTURE_THRESHOLD", 0.25),
            )
        ),
        frame_image_format=str(
            app_raw.get(
                "frame_image_format",
                os.getenv("FRAME_IMAGE_FORMAT", "jpg"),
            )
        ),
        pandoc_binary=str(
            os.getenv("PANDOC_BINARY", app_raw.get("pandoc_binary", "pandoc"))
        ),
        pdf_engine=str(os.getenv("PDF_ENGINE", app_raw.get("pdf_engine", "chromium"))),
        pdf_engine_binary=str(
            os.getenv(
                "PDF_ENGINE_BINARY",
                app_raw.get("pdf_engine_binary", "chromium"),
            )
        ),
    )

    llm = LLMConfig(
        provider=str(os.getenv("LLM_PROVIDER", llm_raw.get("provider", "openai"))),
        model=str(os.getenv("LLM_MODEL", llm_raw.get("model", "gpt-4.1-mini"))),
        prompt_version=str(
            os.getenv("LLM_PROMPT_VERSION", llm_raw.get("prompt_version", "v1"))
        ),
        timeout_seconds=int(
            os.getenv("LLM_TIMEOUT_SECONDS", llm_raw.get("timeout_seconds", 60))
        ),
        retries=int(os.getenv("LLM_RETRIES", llm_raw.get("retries", 2))),
        retry_backoff_seconds=int(
            os.getenv(
                "LLM_RETRY_BACKOFF_SECONDS",
                llm_raw.get("retry_backoff_seconds", 2),
            )
        ),
        router_enabled=_parse_bool(
            os.getenv("LLM_ROUTER_ENABLED"),
            _parse_bool(llm_raw.get("router_enabled"), False),
        ),
        router_repo_path=(
            str(
                os.getenv(
                    "LLM_ROUTER_REPO_PATH",
                    llm_raw.get("router_repo_path", ""),
                )
            ).strip()
            or None
        ),
        router_config_path=(
            str(
                os.getenv(
                    "LLM_ROUTER_CONFIG_PATH",
                    llm_raw.get("router_config_path", ""),
                )
            ).strip()
            or None
        ),
        router_trace_dir=(
            str(
                os.getenv(
                    "LLM_ROUTER_TRACE_DIR",
                    llm_raw.get("router_trace_dir", ""),
                )
            ).strip()
            or None
        ),
        router_roles={
            str(key): str(value)
            for key, value in _as_dict(llm_raw.get("router_roles")).items()
            if str(key).strip() and str(value).strip()
        },
    )

    channels: list[ChannelConfig] = []
    for idx, item in enumerate(channels_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"channels[{idx}] must be a table")
        name = item.get("name")
        url = item.get("url")
        if not name or not url:
            raise ValueError(f"channels[{idx}] must include non-empty `name` and `url`")
        channels.append(
            ChannelConfig(
                name=str(name),
                url=str(url),
                language=str(item["language"]) if item.get("language") else None,
            )
        )

    videos: list[VideoConfig] = []
    for idx, item in enumerate(videos_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"videos[{idx}] must be a table")
        name = item.get("name")
        url = item.get("url")
        if not name or not url:
            raise ValueError(f"videos[{idx}] must include non-empty `name` and `url`")
        videos.append(
            VideoConfig(
                name=str(name),
                url=str(url),
                language=str(item["language"]) if item.get("language") else None,
                clip_start=(
                    str(item["clip_start"]).strip()
                    if item.get("clip_start") is not None
                    else None
                ),
                clip_end=(
                    str(item["clip_end"]).strip()
                    if item.get("clip_end") is not None
                    else None
                ),
                force_asr=_parse_optional_bool(item.get("force_asr")),
            )
        )

    files: list[FileConfig] = []
    for idx, item in enumerate(files_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"files[{idx}] must be a table")
        name = item.get("name")
        path = item.get("path")
        if not name or not path:
            raise ValueError(f"files[{idx}] must include non-empty `name` and `path`")
        files.append(
            FileConfig(
                name=str(name),
                path=str(path),
                language=str(item["language"]) if item.get("language") else None,
                clip_start=(
                    str(item["clip_start"]).strip()
                    if item.get("clip_start") is not None
                    else None
                ),
                clip_end=(
                    str(item["clip_end"]).strip()
                    if item.get("clip_end") is not None
                    else None
                ),
                force_asr=_parse_optional_bool(item.get("force_asr")),
            )
        )

    return Config(
        app=app,
        llm=llm,
        channels=channels,
        videos=videos,
        files=files,
    )


def default_config_from_env() -> Config:
    """Build configuration defaults using environment overrides."""

    return _build_config(
        app_raw={},
        llm_raw={},
        channels_raw=[],
        videos_raw=[],
        files_raw=[],
    )


def load_config(path: str | Path) -> Config:
    """Load TOML config from disk with safe defaults."""

    config_path = Path(path)
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    app_raw = _as_dict(raw.get("app"))
    llm_raw = _as_dict(raw.get("llm"))
    channels_raw = raw.get("channels", [])
    videos_raw = raw.get("videos", [])
    files_raw = raw.get("files", [])
    if not isinstance(channels_raw, list):
        raise ValueError("`channels` must be an array of tables in TOML config")
    if not isinstance(videos_raw, list):
        raise ValueError("`videos` must be an array of tables in TOML config")
    if not isinstance(files_raw, list):
        raise ValueError("`files` must be an array of tables in TOML config")
    return _build_config(
        app_raw=app_raw,
        llm_raw=llm_raw,
        channels_raw=channels_raw,
        videos_raw=videos_raw,
        files_raw=files_raw,
    )
