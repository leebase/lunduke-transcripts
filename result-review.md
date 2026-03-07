# lunduke-transcripts Result Review

> **Running log of completed work.** Newest entries at the top.
>
> Each entry documents what was built, why it matters, and how to verify it works.

---

## 2026-03-06 — Downstream PDF Renderer Delivered

Implemented a downstream renderer that converts a published tutorial manifest
into HTML and PDF while validating screenshot references before render.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Render CLI | Added `lunduke-transcripts render --manifest ... --target pdf` |
| Render pipeline | Added a separate renderer that reads `tutorial_manifest.json`, validates Markdown image references, renders `tutorial_final.html` with Pandoc, and prints `tutorial_final.pdf` with a Chrome-family browser engine |
| Render artifacts | Added `render_manifest.json` with toolchain, output paths, and image validation status |
| Image safety | Added pre-render image validation and stale-output cleanup so failed renders do not pretend to have fresh HTML/PDF |
| Validation | Added tests for HTML/PDF creation, missing-image failures, repeatable renders, and render CLI behavior |

### Why It Matters

- Turns the reviewed Markdown tutorial into a format a reader can actually consume without leaving the project folder.
- Keeps rendering separate from LLM generation so document styling iterations are cheap and deterministic.
- Makes screenshot preservation a hard contract instead of a best-effort side effect.

### How to Verify

1. Install renderer tools:
   - `brew install pandoc chromium`
2. Generate or reuse a published tutorial directory containing `tutorial_manifest.json`.
3. Render the tutorial:
   - `.venv/bin/python -m lunduke_transcripts.main render --manifest /path/to/tutorial/tutorial_manifest.json --target pdf`
4. Verify outputs:
   - `tutorial_final.html`
   - `tutorial_final.pdf`
   - `render_manifest.json`
5. Confirm screenshots are visible in HTML/PDF and that missing images cause a clean failure before render.

## 2026-03-06 — Sprint 8 Multi-Agent Tutorial Generation Delivered

Implemented a downstream tutorial pipeline that consumes `tutorial_asset_bundle.json`
and produces reviewed written tutorials using repo-local agent and skill files.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Tutorial CLI | Added `lunduke-transcripts tutorial --bundle ...` with outline approval, cache reuse, and review-cycle controls |
| Agent system | Added repo-local `agents/` role files and tutorial-specific `skills/` loaded at runtime |
| Tutorial artifacts | Added `tutorial_definition.json`, `lesson_outline.json`, `evidence_map.json`, `frame_selection_plan.json`, review artifacts, `tutorial_manifest.json`, and `tutorial_final.md` |
| Review loop | Added validator, technical review, adversarial review, and review-response rerouting before publish |
| Caching/provenance | Added manifest-based cache reuse keyed by bundle contents plus agent/skill digests |
| Validation | Added tests for approval gating, adversarial blocking, writer-only reroute recovery, text-only validation, skill-version invalidation, and CLI failure handling |

### Why It Matters

- Turns the extracted transcript/frame bundle into an actual reviewed tutorial workflow instead of leaving rendering entirely hypothetical.
- Makes prompt behavior editable through versioned repo files while preserving reproducibility through manifest digests.
- Mirrors the project's code discipline by forcing validation and review before a tutorial is publish-eligible.

### How to Verify

1. Run checks:
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
2. Create or reuse a video directory containing `tutorial_asset_bundle.json`.
3. Generate the outline package:
   - `.venv/bin/python -m lunduke_transcripts.main tutorial --bundle /path/to/tutorial_asset_bundle.json`
4. Approve and continue:
   - `.venv/bin/python -m lunduke_transcripts.main tutorial --bundle /path/to/tutorial_asset_bundle.json --approve-outline`
5. Verify tutorial outputs under `tutorial/`:
   - `tutorial_definition.json`
   - `lesson_outline.json`
   - `evidence_map.json`
   - `frame_selection_plan.json`
   - `tutorial_validation_report.json`
   - `technical_review_report.json`
   - `adversarial_review_report.json`
   - `tutorial_revision_plan.json`
   - `tutorial_manifest.json`
   - `tutorial_final.md` when publish-eligible

## 2026-03-06 — Sprint 7 Closeout Remediation Completed

Closed the Sprint 7 review findings by hardening frame extraction, bundle
generation, and local source identity behavior.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Bundle contract | `tutorial_asset_bundle.json` is now written whenever `transcript.json` exists and records `frame_capture.status` plus any extraction error |
| Frame safety | Frame extraction now stages into a temporary directory and only replaces `frames/` after success |
| Local IDs | Added regression coverage to keep local source IDs stable across `touch` and rename operations |
| Architecture docs | Added `architecture.md` and aligned the review process with an actual technical decision log |
| Validation | Added regression tests for frame capture failure handling and frame preservation on failed reruns |

### Why It Matters

- Prevents a nominally successful run from hiding a missing canonical bundle.
- Preserves the last known-good screenshots when a reprocess fails.
- Keeps local artifact trees stable for the same media file even when its filesystem metadata changes.

### How to Verify

1. Run automated checks:
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
2. Run a local-file flow with a sidecar caption file:
   - `.venv/bin/python -m lunduke_transcripts.main run --config /tmp/test-config.toml --video-file /path/to/demo.mp4`
3. Verify the bundle output:
   - `tutorial_asset_bundle.json` exists whenever `transcript.json` exists
   - `frame_capture.status` is `captured` on success or `error` on extractor failure
4. Re-run the same command and confirm `videos_new = 0`.
5. Run with a missing local file path and confirm the CLI exits with status `failed`.

## 2026-03-06 — Sprint 7 Tutorial Asset Extraction Delivered

Implemented the extraction phase that turns a YouTube video or local media file
into reusable transcript and frame artifacts for later tutorial generation.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Local ingest | Added local file targets via `[[files]]` config and `--video-file` CLI support |
| Transcript package | Added canonical `transcript.json` with normalized segment timing and provenance |
| Frame extraction | Added `ffmpeg` scene-change frame capture into per-video `frames/` directories |
| Frame manifest | Added `frame_manifest.json` referencing image files and timestamps |
| Bundle manifest | Added `tutorial_asset_bundle.json` as the top-level downstream package |
| Validation | Added tests for local file config parsing, bundle artifacts, rerun idempotency, and missing-file failure handling |

### Why It Matters

- Separates extraction from later rendering so Markdown, HTML, PDF, and PPTX work can build on stable inputs.
- Supports both YouTube and local `.mp4` workflows in one pipeline.
- Keeps image binaries out of JSON while preserving the metadata needed for later generators.

### How to Verify

1. Activate the venv and run checks:
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
2. Run a local file flow with sidecar captions:
   - `.venv/bin/python -m lunduke_transcripts.main run --config /tmp/test-config.toml --video-file /path/to/demo.mp4`
3. Verify outputs under the configured data dir:
   - `transcript_exact.vtt`
   - `transcript.json`
   - `frame_manifest.json`
   - `tutorial_asset_bundle.json`
   - `frames/*.jpg`
4. Re-run the same command and confirm `videos_new = 0`.

---

## 2026-03-06 — Planned Transcript + Frame Asset Extraction Phase

Updated the planning docs to define the next implementation phase around canonical
transcript and screen-grab artifacts for downstream tutorial generation.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Product scope | Expanded product definition to include local video ingest, transcript JSON, frame manifests, and tutorial asset bundles |
| Technical design | Reworked design around source-agnostic ingest, scene-detection-based frame extraction, and JSON contracts |
| Sprint plan | Added Sprint 7 focused on transcript extraction, frame capture, and canonical asset packaging |
| Session memory | Updated `context.md` and `WHERE_AM_I.md` to reflect the new phase and locked decisions |

### Why It Matters

- Clarifies that screenshots are stored as files on disk, not embedded in JSON.
- Establishes one canonical intermediate package for future Markdown, HTML, PDF, and PPTX generators.
- Narrows the next build phase to extraction and packaging, which reduces scope risk.

### How to Verify

1. Read [product-definition.md](product-definition.md)
2. Read [design.md](design.md)
3. Read [sprint-plan.md](sprint-plan.md)
4. Confirm the docs consistently describe:
   - local file + YouTube ingest
   - `transcript.json`
   - `frame_manifest.json`
   - `tutorial_asset_bundle.json`

---

## 2026-03-04 — Sprint 4 Reliability Hardening Completed

Completed a focused hardening sprint based on external review findings.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Python contract | Runtime support aligned to Python 3.11+ in `pyproject.toml` |
| yt-dlp safety | Added subprocess timeout + retry handling with explicit timeout error tags |
| LLM safety | Added request timeout + bounded retries + structured timeout/failure messages |
| Test reproducibility | Added pytest path config (`pythonpath = ["src"]`) |
| CI gates | Added GitHub Actions workflow for ruff, black --check, and pytest |
| Docs portability | Replaced absolute local file links with relative links in project docs |
| Regression coverage | Added tests for yt-dlp timeout behavior, LLM retry/timeout behavior, and project contract |

### Why It Matters

- Reduces scheduler stall risk from hanging external calls.
- Makes runtime support expectations explicit and enforceable.
- Improves contributor and CI reproducibility.
- Strengthens maintainability by preventing portability/documentation regressions.

### How to Verify

1. `source .venv/bin/activate`
2. `ruff check src tests`
3. `black --check src tests`
4. `pytest -q`
5. Inspect CI workflow at `.github/workflows/ci.yml`

---

## 2026-03-04 — MVP Pipeline Delivered (Sprints 1-3)

Implemented and validated the full transcript workflow from product/design docs.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Core package | Normalized package path to `src/lunduke_transcripts/` and rebuilt CLI app |
| Run modes | `run` command with `--config`, `--from`, `--to`, `--reprocess` |
| Discovery/fetch | `yt-dlp` adapter for channel discovery, metadata fetch, transcript acquisition |
| State | SQLite tables: `videos`, `transcripts`, `runs`, `run_items` |
| Artifacts | `metadata.json`, `transcript_exact.vtt`, `transcript_exact.md`, `transcript_exact.txt`, optional `transcript_clean.md` |
| Cleanup pass | OpenAI adapter + deterministic cleanup prompt + hash-based cache |
| Scheduling | `scripts/run_pipeline.sh` + `scripts/com.lunduke.transcripts.plist.example` + README scheduler docs |
| Tests | Unit/integration tests for VTT parsing, date-range filtering, idempotency/reprocess behavior |

### Why It Matters

- Ships an end-to-end MVP that can run now or on schedule.
- Preserves exact transcript fidelity while enabling optional cleaned output.
- Adds durable state and run reporting so reruns are safe and auditable.

### How to Verify

1. Activate environment and run checks:
   - `source .venv/bin/activate`
   - `ruff check src tests`
   - `pytest -q`
2. Run the app:
   - `python -m lunduke_transcripts.main run --config config/channels.toml`
3. Verify outputs:
   - `data/db/lunduke_transcripts.sqlite3`
   - `data/runs/<run_id>.json`
   - `data/videos/<video_id>/metadata.json`
   - transcript files under each video directory
4. Verify idempotency:
   - run same command twice
   - second run should report `videos_new = 0` unless `--reprocess` is used

### Test As Lee Results

- Live run against `https://www.youtube.com/@Lunduke/videos` succeeded.
- Rerun confirmed idempotency (`videos_new = 0`).
- `--reprocess` rerun successfully processed the same range again.

---

## 2026-02-17 — Project Scaffolded

**Project initialized** with init-agent.

### Created

| File | Purpose |
|------|---------|
| `AGENTS.md` | AI agent guide and conventions |
| `WHERE_AM_I.md` | Quick orientation for agents |
| `feedback.md` | Human feedback capture |
| `README.md` | Project documentation |
| `context.md` | Session working memory |
| `result-review.md` | This file - running log |
| `sprint-plan.md` | Sprint tracking |

### How to Verify

1. Check all files exist: `ls *.md`
2. Read AGENTS.md to understand project conventions
3. Check context.md for current state

---

*Add new entries above this line. Keep the newest work at the top.*
