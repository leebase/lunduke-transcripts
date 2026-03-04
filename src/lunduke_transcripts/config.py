"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py310 fallback
    import tomli as tomllib


@dataclass(frozen=True)
class AppConfig:
    """Application-level runtime settings."""

    data_dir: Path = Path("data")
    default_language: str = "en"
    timezone: str = "America/Chicago"
    enable_cleanup: bool = True
    yt_dlp_binary: str = "yt-dlp"
    fetch_retries: int = 2
    retry_backoff_seconds: int = 2
    max_videos_per_channel: int | None = None


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider settings."""

    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    prompt_version: str = "v1"


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
        enable_cleanup=bool(app_raw.get("enable_cleanup", True)),
        yt_dlp_binary=str(app_raw.get("yt_dlp_binary", "yt-dlp")),
        fetch_retries=int(app_raw.get("fetch_retries", 2)),
        retry_backoff_seconds=int(app_raw.get("retry_backoff_seconds", 2)),
        max_videos_per_channel=(
            int(app_raw["max_videos_per_channel"])
            if app_raw.get("max_videos_per_channel") is not None
            else None
        ),
    )

    llm = LLMConfig(
        provider=str(llm_raw.get("provider", "openai")),
        model=str(llm_raw.get("model", "gpt-4.1-mini")),
        prompt_version=str(llm_raw.get("prompt_version", "v1")),
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
