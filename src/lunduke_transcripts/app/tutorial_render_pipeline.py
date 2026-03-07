"""Downstream render pipeline for published tutorial artifacts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from lunduke_transcripts.domain.models import RenderSummary

_MARKDOWN_IMAGE_RE = re.compile(
    r"!\[[^\]]*]\((?P<path><[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)


class TutorialRenderPipeline:
    """Render a published tutorial into downstream document formats."""

    def __init__(
        self,
        *,
        pandoc_binary: str,
        pdf_engine: str,
        pdf_engine_binary: str,
        renderer_dir: Path,
        timeout_seconds: int = 120,
    ) -> None:
        self.pandoc_binary = pandoc_binary
        self.pdf_engine = pdf_engine
        self.pdf_engine_binary = pdf_engine_binary
        self.renderer_dir = renderer_dir
        self.timeout_seconds = timeout_seconds

    def run(self, *, manifest_path: Path, target: str) -> RenderSummary:
        resolved_manifest = manifest_path.expanduser().resolve()
        tutorial_dir = resolved_manifest.parent
        render_manifest_path = tutorial_dir / "render_manifest.json"
        html_path = tutorial_dir / "tutorial_final.html"
        output_path = tutorial_dir / "tutorial_final.pdf"
        _remove_if_exists(html_path, output_path)

        try:
            if target != "pdf":
                raise RuntimeError(f"unsupported_render_target: {target}")
            if not resolved_manifest.exists():
                raise RuntimeError(f"tutorial_manifest_missing: {resolved_manifest}")

            tutorial_manifest = _load_json(resolved_manifest)
            markdown_path = _resolve_tutorial_markdown(
                tutorial_manifest=tutorial_manifest,
                tutorial_dir=tutorial_dir,
            )
            markdown_text = markdown_path.read_text(encoding="utf-8")
            image_validation = _validate_markdown_images(
                markdown_text=markdown_text,
                tutorial_dir=tutorial_dir,
            )
            if image_validation["missing_images"]:
                missing = ", ".join(image_validation["missing_images"])
                raise RuntimeError(f"missing_tutorial_images: {missing}")

            toolchain = self._resolve_toolchain()
            self._render_html(markdown_path=markdown_path, html_path=html_path)
            self._render_pdf(html_path=html_path, pdf_path=output_path)

            render_manifest = _build_render_manifest(
                source_manifest_path=resolved_manifest,
                target=target,
                toolchain=toolchain,
                image_validation=image_validation,
                html_path=html_path,
                output_path=output_path,
                status="success",
                error=None,
            )
            _write_json(render_manifest_path, render_manifest)
            return RenderSummary(
                status="success",
                tutorial_dir=tutorial_dir,
                render_manifest_path=render_manifest_path,
                target=target,
                html_path=html_path,
                output_path=output_path,
            )
        except Exception as exc:  # noqa: BLE001
            render_manifest = _build_render_manifest(
                source_manifest_path=resolved_manifest,
                target=target,
                toolchain=self._toolchain_snapshot(),
                image_validation=_failed_image_validation(exc),
                html_path=html_path,
                output_path=output_path,
                status="failed",
                error=str(exc),
            )
            tutorial_dir.mkdir(parents=True, exist_ok=True)
            _write_json(render_manifest_path, render_manifest)
            return RenderSummary(
                status="failed",
                tutorial_dir=tutorial_dir,
                render_manifest_path=render_manifest_path,
                target=target,
                html_path=html_path if html_path.exists() else None,
                output_path=output_path if output_path.exists() else None,
                failures=[str(exc)],
            )

    def _resolve_toolchain(self) -> dict[str, Any]:
        pandoc_path = _resolve_binary(self.pandoc_binary)
        pdf_engine_path = _resolve_pdf_engine_binary(
            raw_binary=self.pdf_engine_binary,
            engine_name=self.pdf_engine,
        )
        if self.pdf_engine != "chromium":
            raise RuntimeError(f"unsupported_pdf_engine: {self.pdf_engine}")
        return {
            "pandoc": {
                "binary": str(pandoc_path),
                "version": _read_binary_version(pandoc_path),
            },
            "pdf_engine": {
                "name": self.pdf_engine,
                "binary": str(pdf_engine_path),
                "version": _read_binary_version(pdf_engine_path),
            },
        }

    def _toolchain_snapshot(self) -> dict[str, Any]:
        return {
            "pandoc": {"binary": self.pandoc_binary},
            "pdf_engine": {
                "name": self.pdf_engine,
                "binary": self.pdf_engine_binary,
            },
        }

    def _render_html(self, *, markdown_path: Path, html_path: Path) -> None:
        css_path = self.renderer_dir / "tutorial.css"
        if not css_path.exists():
            raise RuntimeError(f"renderer_css_missing: {css_path}")
        command = [
            self.pandoc_binary,
            str(markdown_path),
            "--from",
            "gfm",
            "--to",
            "html5",
            "--standalone",
            "--css",
            css_path.resolve().as_uri(),
            "--resource-path",
            os.pathsep.join(
                [str(markdown_path.parent), str(markdown_path.parent.parent)]
            ),
            "--output",
            str(html_path),
        ]
        _run_command(
            command, cwd=markdown_path.parent, timeout_seconds=self.timeout_seconds
        )

    def _render_pdf(self, *, html_path: Path, pdf_path: Path) -> None:
        with tempfile.TemporaryDirectory(prefix="lunduke-render-") as profile_dir:
            command = [
                str(
                    _resolve_pdf_engine_binary(
                        raw_binary=self.pdf_engine_binary,
                        engine_name=self.pdf_engine,
                    )
                ),
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--allow-file-access-from-files",
                f"--user-data-dir={profile_dir}",
                "--print-to-pdf-no-header",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ]
            _run_browser_pdf_command(
                command,
                cwd=html_path.parent,
                timeout_seconds=self.timeout_seconds,
            )
        if not pdf_path.exists():
            raise RuntimeError(f"pdf_output_missing: {pdf_path}")


def _resolve_tutorial_markdown(
    *, tutorial_manifest: dict[str, Any], tutorial_dir: Path
) -> Path:
    artifacts = tutorial_manifest.get("artifacts", {})
    tutorial_final = artifacts.get("tutorial_final", {})
    raw_path = tutorial_final.get("path") or str(tutorial_dir / "tutorial_final.md")
    markdown_path = Path(raw_path).expanduser().resolve()
    if not markdown_path.exists():
        raise RuntimeError(f"tutorial_final_missing: {markdown_path}")
    return markdown_path


def _validate_markdown_images(
    *, markdown_text: str, tutorial_dir: Path
) -> dict[str, Any]:
    resolved_images: list[str] = []
    missing_images: list[str] = []
    for raw_match in _MARKDOWN_IMAGE_RE.finditer(markdown_text):
        raw_path = raw_match.group("path").strip()
        candidate = (
            raw_path[1:-1]
            if raw_path.startswith("<") and raw_path.endswith(">")
            else raw_path
        )
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https", "data"}:
            continue
        if parsed.scheme == "file":
            image_path = Path(unquote(parsed.path))
        else:
            image_path = (tutorial_dir / candidate).resolve()
        resolved_images.append(str(image_path))
        if not image_path.exists():
            missing_images.append(candidate)
    return {
        "status": "passed" if not missing_images else "failed",
        "resolved_images": resolved_images,
        "missing_images": missing_images,
    }


def _failed_image_validation(exc: Exception) -> dict[str, Any]:
    message = str(exc)
    if message.startswith("missing_tutorial_images: "):
        raw = message.removeprefix("missing_tutorial_images: ")
        missing_images = [item.strip() for item in raw.split(",") if item.strip()]
        return {
            "status": "failed",
            "resolved_images": [],
            "missing_images": missing_images,
        }
    return {
        "status": "unknown",
        "resolved_images": [],
        "missing_images": [],
    }


def _build_render_manifest(
    *,
    source_manifest_path: Path,
    target: str,
    toolchain: dict[str, Any],
    image_validation: dict[str, Any],
    html_path: Path,
    output_path: Path,
    status: str,
    error: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "status": status,
        "target": target,
        "source_tutorial_manifest_path": str(source_manifest_path),
        "rendered_at": datetime.now(tz=UTC).isoformat(),
        "toolchain": toolchain,
        "image_validation": image_validation,
        "outputs": {
            "html": {
                "path": str(html_path),
                "exists": html_path.exists(),
            },
            "pdf": {
                "path": str(output_path),
                "exists": output_path.exists(),
            },
        },
        "error": error,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _remove_if_exists(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def _resolve_binary(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    resolved = shutil.which(raw)
    if resolved:
        return Path(resolved).resolve()
    raise RuntimeError(f"required_binary_missing: {raw}")


def _resolve_pdf_engine_binary(*, raw_binary: str, engine_name: str) -> Path:
    if engine_name != "chromium":
        return _resolve_binary(raw_binary)
    if raw_binary == "chromium":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "google-chrome",
            raw_binary,
            "chromium-browser",
        ]
    else:
        candidates = [raw_binary]
    for candidate in candidates:
        try:
            return _resolve_binary(candidate)
        except RuntimeError:
            continue
    raise RuntimeError(f"required_binary_missing: {raw_binary}")


def _read_binary_version(binary: Path) -> str:
    try:
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return result.stdout.splitlines()[0].strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _run_command(command: list[str], *, cwd: Path, timeout_seconds: int) -> None:
    try:
        subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            f"render_command_failed: {' '.join(command)} :: {stderr or exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"render_command_timeout: {' '.join(command)}") from exc


def _run_browser_pdf_command(
    command: list[str], *, cwd: Path, timeout_seconds: int
) -> None:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + timeout_seconds
    pdf_arg = next(
        item for item in command if item.startswith("--print-to-pdf=")
    ).split("=", 1)[1]
    pdf_path = Path(pdf_arg)
    try:
        while time.monotonic() < deadline:
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=5)
                if pdf_path.exists() and pdf_path.stat().st_size > 0:
                    return
                raise RuntimeError(
                    f"render_command_failed: {' '.join(command)} :: "
                    f"{(stderr or stdout or '').strip() or process.returncode}"
                )
            time.sleep(0.5)
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
            return
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        raise RuntimeError(
            f"render_command_timeout: {' '.join(command)} :: "
            f"{(stderr or stdout or '').strip()}"
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
