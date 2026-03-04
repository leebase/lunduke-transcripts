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


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider settings."""

    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    prompt_version: str = "v1"
    timeout_seconds: int = 60
    retries: int = 2
    retry_backoff_seconds: int = 2


@dataclass(frozen=True)
class ChannelConfig:
    """Channel source configuration."""

    name: str
    url: str
    language: str | None = None


@dataclass(frozen=True)
class Config:
    """Top-level app configuration."""

    app: AppConfig = field(default_factory=AppConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    channels: list[ChannelConfig] = field(default_factory=list)


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


def load_config(path: str | Path) -> Config:
    """Load TOML config from disk with safe defaults."""

    config_path = Path(path)
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    app_raw = _as_dict(raw.get("app"))
    llm_raw = _as_dict(raw.get("llm"))
    channels_raw = raw.get("channels", [])
    if not isinstance(channels_raw, list):
        raise ValueError("`channels` must be an array of tables in TOML config")

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

    return Config(app=app, llm=llm, channels=channels)
