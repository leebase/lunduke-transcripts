"""Frame candidate extraction using ffmpeg scene detection."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from lunduke_transcripts.domain.models import FrameCandidate
from lunduke_transcripts.infra.youtube_adapter import _parse_timecode_seconds

_PTS_RE = re.compile(r"pts_time:(?P<pts>\d+(?:\.\d+)?)")


@dataclass
class VideoFrameExtractor:
    """Extract scene-change frame candidates from a video file."""

    ffmpeg_binary: str = "ffmpeg"
    threshold: float = 0.25
    image_format: str = "jpg"
    timeout_seconds: int = 300

    def extract_frames(
        self,
        *,
        video_path: Path,
        output_dir: Path,
        clip_start: str | None = None,
        clip_end: str | None = None,
    ) -> list[FrameCandidate]:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_output_dir = Path(
            tempfile.mkdtemp(prefix=f".{output_dir.name}-tmp-", dir=output_dir.parent)
        )
        backup_dir: Path | None = None

        command = [self.ffmpeg_binary, "-hide_banner", "-y"]
        if clip_start:
            command.extend(["-ss", clip_start])
        command.extend(["-i", str(video_path)])
        if clip_end:
            start_seconds = _parse_timecode_seconds(clip_start) or 0.0
            end_seconds = _parse_timecode_seconds(clip_end)
            if end_seconds is None:
                raise RuntimeError("invalid_clip_range")
            duration = end_seconds - start_seconds
            if duration <= 0:
                raise RuntimeError("invalid_clip_range")
            command.extend(["-t", f"{duration:.3f}"])
        command.extend(
            [
                "-an",
                "-sn",
                "-dn",
                "-vf",
                f"select='gt(scene,{self.threshold})',showinfo",
                "-fps_mode",
                "vfr",
                str(temp_output_dir / f"%06d.{self.image_format}"),
            ]
        )
        try:
            result = subprocess.run(
                command,
                check=True,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
            timestamps = [
                float(match.group("pts"))
                for match in _PTS_RE.finditer(f"{result.stdout}\n{result.stderr}")
            ]
            image_files = sorted(temp_output_dir.glob(f"*.{self.image_format}"))
            if not image_files:
                frames = [
                    self._extract_fallback_frame(
                        video_path,
                        temp_output_dir,
                        clip_start,
                    )
                ]
            else:
                frames = [
                    FrameCandidate(
                        frame_index=index,
                        timestamp_seconds=(
                            timestamps[index]
                            if index < len(timestamps)
                            else float(index)
                        ),
                        image_path=f"frames/{image_path.name}",
                    )
                    for index, image_path in enumerate(image_files)
                ]

            if output_dir.exists():
                backup_dir = temp_output_dir.parent / f".{output_dir.name}-bak"
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                output_dir.replace(backup_dir)
            temp_output_dir.replace(output_dir)
            temp_output_dir = output_dir
            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir)
                backup_dir = None
            return frames
        except Exception:
            if (
                backup_dir is not None
                and backup_dir.exists()
                and not output_dir.exists()
            ):
                backup_dir.replace(output_dir)
            raise
        finally:
            if temp_output_dir.exists() and temp_output_dir != output_dir:
                shutil.rmtree(temp_output_dir, ignore_errors=True)
            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

    def _extract_fallback_frame(
        self, video_path: Path, output_dir: Path, clip_start: str | None
    ) -> FrameCandidate:
        fallback_path = output_dir / f"000000.{self.image_format}"
        command = [self.ffmpeg_binary, "-hide_banner", "-y"]
        if clip_start:
            command.extend(["-ss", clip_start])
        command.extend(
            [
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(fallback_path),
            ]
        )
        subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
        )
        return FrameCandidate(
            frame_index=0,
            timestamp_seconds=_parse_timecode_seconds(clip_start) or 0.0,
            image_path=f"frames/{fallback_path.name}",
            selection_kind="fallback",
        )
