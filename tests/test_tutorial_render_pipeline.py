from __future__ import annotations

import json
from pathlib import Path

from lunduke_transcripts.app.tutorial_render_pipeline import TutorialRenderPipeline


def test_render_pipeline_creates_html_and_pdf_with_images(tmp_path) -> None:
    tutorial_dir = _make_tutorial_dir(tmp_path)
    renderer_dir = _make_renderer_dir(tmp_path)
    pandoc_path, chromium_path = _make_fake_renderer_binaries(tmp_path)
    pipeline = TutorialRenderPipeline(
        pandoc_binary=str(pandoc_path),
        pdf_engine="chromium",
        pdf_engine_binary=str(chromium_path),
        renderer_dir=renderer_dir,
    )

    summary = pipeline.run(
        manifest_path=tutorial_dir / "tutorial_manifest.json",
        target="pdf",
    )

    assert summary.status == "success"
    assert summary.html_path is not None
    assert summary.output_path is not None
    html = summary.html_path.read_text(encoding="utf-8")
    assert '<img alt="Frame"' in html
    assert "../frames/000001.jpg" in html
    assert summary.output_path.exists()
    render_manifest = json.loads(
        summary.render_manifest_path.read_text(encoding="utf-8")
    )
    assert render_manifest["image_validation"]["status"] == "passed"


def test_render_pipeline_reports_missing_images(tmp_path) -> None:
    tutorial_dir = _make_tutorial_dir(tmp_path, create_image=False)
    renderer_dir = _make_renderer_dir(tmp_path)
    pandoc_path, chromium_path = _make_fake_renderer_binaries(tmp_path)
    pipeline = TutorialRenderPipeline(
        pandoc_binary=str(pandoc_path),
        pdf_engine="chromium",
        pdf_engine_binary=str(chromium_path),
        renderer_dir=renderer_dir,
    )

    summary = pipeline.run(
        manifest_path=tutorial_dir / "tutorial_manifest.json",
        target="pdf",
    )

    assert summary.status == "failed"
    assert "missing_tutorial_images" in summary.failures[0]
    render_manifest = json.loads(
        summary.render_manifest_path.read_text(encoding="utf-8")
    )
    assert render_manifest["image_validation"]["missing_images"] == [
        "../frames/000001.jpg"
    ]
    assert render_manifest["outputs"]["html"]["exists"] is False
    assert render_manifest["outputs"]["pdf"]["exists"] is False


def test_render_pipeline_requires_tutorial_final_markdown(tmp_path) -> None:
    tutorial_dir = tmp_path / "video" / "tutorial"
    tutorial_dir.mkdir(parents=True)
    (tutorial_dir / "tutorial_manifest.json").write_text(
        json.dumps(
            {
                "artifacts": {
                    "tutorial_final": {
                        "path": str(tutorial_dir / "tutorial_final.md"),
                        "exists": False,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    renderer_dir = _make_renderer_dir(tmp_path)
    pandoc_path, chromium_path = _make_fake_renderer_binaries(tmp_path)
    pipeline = TutorialRenderPipeline(
        pandoc_binary=str(pandoc_path),
        pdf_engine="chromium",
        pdf_engine_binary=str(chromium_path),
        renderer_dir=renderer_dir,
    )

    summary = pipeline.run(
        manifest_path=tutorial_dir / "tutorial_manifest.json",
        target="pdf",
    )

    assert summary.status == "failed"
    assert "tutorial_final_missing" in summary.failures[0]


def test_render_pipeline_is_repeatable(tmp_path) -> None:
    tutorial_dir = _make_tutorial_dir(tmp_path)
    renderer_dir = _make_renderer_dir(tmp_path)
    pandoc_path, chromium_path = _make_fake_renderer_binaries(tmp_path)
    pipeline = TutorialRenderPipeline(
        pandoc_binary=str(pandoc_path),
        pdf_engine="chromium",
        pdf_engine_binary=str(chromium_path),
        renderer_dir=renderer_dir,
    )

    first = pipeline.run(
        manifest_path=tutorial_dir / "tutorial_manifest.json",
        target="pdf",
    )
    second = pipeline.run(
        manifest_path=tutorial_dir / "tutorial_manifest.json",
        target="pdf",
    )

    assert first.status == "success"
    assert second.status == "success"
    assert second.output_path is not None
    assert second.output_path.read_text(encoding="utf-8").startswith("PDF\n")


def _make_tutorial_dir(tmp_path: Path, *, create_image: bool = True) -> Path:
    tutorial_dir = tmp_path / "video" / "tutorial"
    tutorial_dir.mkdir(parents=True)
    frames_dir = tutorial_dir.parent / "frames"
    frames_dir.mkdir(parents=True)
    if create_image:
        (frames_dir / "000001.jpg").write_bytes(b"fake-jpg")
    markdown = (
        "# Demo Tutorial\n\n"
        "Intro paragraph.\n\n"
        "![Frame](../frames/000001.jpg)\n\n"
        "## Step 1\n\n"
        "Do the thing.\n"
    )
    tutorial_final = tutorial_dir / "tutorial_final.md"
    tutorial_final.write_text(markdown, encoding="utf-8")
    (tutorial_dir / "tutorial_manifest.json").write_text(
        json.dumps(
            {
                "artifacts": {
                    "tutorial_final": {
                        "path": str(tutorial_final),
                        "exists": True,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return tutorial_dir


def _make_renderer_dir(tmp_path: Path) -> Path:
    renderer_dir = tmp_path / "renderers"
    renderer_dir.mkdir()
    (renderer_dir / "tutorial.css").write_text(
        "img { max-width: 100%; }", encoding="utf-8"
    )
    return renderer_dir


def _make_fake_renderer_binaries(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pandoc_path = bin_dir / "pandoc"
    pandoc_path.write_text(
        """#!/usr/bin/env python3
import pathlib
import re
import sys

args = sys.argv[1:]
if "--version" in args:
    print("pandoc 99.0")
    raise SystemExit(0)
input_path = pathlib.Path(args[0])
output_path = pathlib.Path(args[args.index("--output") + 1])
markdown = input_path.read_text(encoding="utf-8")
def repl(match):
    return f'<img alt="{match.group(1)}" src="{match.group(2)}" />'
html_body = re.sub(r'!\\[([^\\]]*)\\]\\(([^)]+)\\)', repl, markdown)
html = "<html><body>" + html_body + "</body></html>"
output_path.write_text(html, encoding="utf-8")
""",
        encoding="utf-8",
    )
    pandoc_path.chmod(0o755)

    chromium_path = bin_dir / "chromium"
    chromium_path.write_text(
        """#!/usr/bin/env python3
import pathlib
import sys

args = sys.argv[1:]
if "--version" in args:
    print("Chromium 999.0")
    raise SystemExit(0)
pdf_arg = next(item for item in args if item.startswith("--print-to-pdf="))
pdf_path = pathlib.Path(pdf_arg.split("=", 1)[1])
html_arg = args[-1]
html_path = pathlib.Path(html_arg.replace("file://", ""))
pdf_path.write_text("PDF\\n" + html_path.read_text(encoding="utf-8"), encoding="utf-8")
""",
        encoding="utf-8",
    )
    chromium_path.chmod(0o755)
    return pandoc_path, chromium_path
