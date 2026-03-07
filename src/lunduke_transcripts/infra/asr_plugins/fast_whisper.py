"""fast-whisper ASR provider plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lunduke_transcripts.infra.asr_plugins.base import ASRSegment, ASRTranscript


class FastWhisperPlugin:
    """ASR plugin implementation backed by faster-whisper."""

    provider_name = "fast-whisper"

    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        compute_type: str,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model: Any | None = None

    def is_available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
        except Exception:  # noqa: BLE001
            return False
        return True

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "fast-whisper not installed. Install with `pip install faster-whisper`."
            ) from exc
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
        )
        return self._model

    def transcribe(self, audio_path: Path, language: str | None) -> ASRTranscript:
        model = self._ensure_model()
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,
        )
        segments = [
            ASRSegment(
                start_seconds=float(segment.start),
                end_seconds=float(segment.end),
                text=str(segment.text).strip(),
            )
            for segment in segments_iter
            if str(segment.text).strip()
        ]
        if not segments:
            raise RuntimeError("asr_empty_transcript")
        detected_language = (
            str(getattr(info, "language", "")).strip() or language or None
            if info is not None
            else (language or None)
        )
        return ASRTranscript(
            provider=self.provider_name,
            model=self.model_name,
            language=detected_language,
            segments=segments,
        )
