from __future__ import annotations

import pytest

from lunduke_transcripts.config import AppConfig
from lunduke_transcripts.infra.asr_plugins.registry import build_asr_plugin


def test_build_asr_plugin_fast_whisper() -> None:
    app = AppConfig(asr_provider="fast-whisper")
    plugin = build_asr_plugin(app)
    assert plugin is not None
    assert plugin.provider_name == "fast-whisper"


def test_build_asr_plugin_none() -> None:
    app = AppConfig(asr_provider="none")
    assert build_asr_plugin(app) is None


def test_build_asr_plugin_invalid() -> None:
    app = AppConfig(asr_provider="unknown-asr")
    with pytest.raises(ValueError, match="Unsupported ASR provider"):
        build_asr_plugin(app)
