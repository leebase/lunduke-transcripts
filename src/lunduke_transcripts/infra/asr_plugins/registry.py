"""ASR plugin registry/factory."""

from __future__ import annotations

from lunduke_transcripts.config import AppConfig
from lunduke_transcripts.infra.asr_plugins.base import ASRPlugin
from lunduke_transcripts.infra.asr_plugins.fast_whisper import FastWhisperPlugin


def build_asr_plugin(app: AppConfig) -> ASRPlugin | None:
    """Build configured ASR plugin instance or return None when disabled."""

    provider = app.asr_provider.strip().lower()
    if provider in {"", "none", "disabled", "off"}:
        return None
    if provider in {"fast-whisper", "faster-whisper"}:
        return FastWhisperPlugin(
            model_name=app.asr_model,
            device=app.asr_device,
            compute_type=app.asr_compute_type,
        )
    raise ValueError(f"Unsupported ASR provider: {app.asr_provider}")


def plugin_source_details(plugin: ASRPlugin | None) -> dict[str, str]:
    """Return plugin details for metadata persistence."""

    if plugin is None:
        return {}
    return {
        "asr_provider": str(getattr(plugin, "provider_name", "")),
        "asr_model": str(getattr(plugin, "model_name", "")),
    }
