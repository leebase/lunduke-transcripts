# Sprint Plan: lunduke-transcripts

> Tactical execution plan for AgentFlow delivery. This is the source of truth for sprint scope and status.

---

## Planning Baseline

- **Date created**: 2026-03-04
- **Current mode**: 2 (Collaborative)
- **Method**: TinyClaw (small, validated increments)
- **MVP source**: `product-definition.md` + `design.md`

Assumptions:
- Sprint length: 1 week (adjustable)
- Priority: source-agnostic transcript extraction and reusable frame asset generation

---

## Sprint 10 — Tutorial Quality Refinement

**Status**: ✅ Completed (2026-03-07)  
**Goal**: Improve public tutorial quality so outputs read like real tutorials instead of transcript-shaped artifacts, while routing the expensive tutorial stages through a stronger model and converting the reviewer stages into advisory co-editors that always produce a fresh latest artifact.

### Scope

- [x] Add tutorial-specific skills for:
  - narrative structure
  - public-artifact hygiene
  - tutorial navigation
  - tutorial step selection
  - tutorial-quality review
- [x] Update writer/planner/reviewer agents to use the new tutorial skills
- [x] Make adversarial review advisory-only rather than a publish veto
- [x] Require public tutorial structure in final Markdown:
  - context section
  - table of contents
  - back-to-top navigation
  - no leaked `Evidence:` callouts
- [x] Route tutorial writing/review/red-team stages through `lee-llm-router` and ChatGPT Plus `gpt-5.4`
- [x] Fix the ChatGPT subscription provider so the real screencast tutorial flow no longer hangs in the review loop
- [x] Add validator/test coverage for:
  - evidence leakage
  - missing navigation
  - definition-controlled structural requirements
  - per-section back-to-top validation
- [x] Run formal code review and remediate findings
- [x] Fix the live LLM review-stage stall exposed by real screencast reruns
- [x] Remove tutorial hard-block semantics from validation and technical review
- [x] Always run technical and adversarial review, even when validation finds defects
- [x] Always write a fresh latest tutorial artifact after outline approval, with review warnings in the manifest instead of `blocked` tutorial status
- [x] Fix tutorial reroute handling so `script-writer` and `visual-editor` reroutes continue cleanly
- [x] Update CLI/docs/status semantics so editorial issues no longer return an error exit code
- [x] Retune planning/writing so incidental environment setup is explicitly discouraged and called out in review prompts
- [x] Republish the `AgentFlowComplete_compressed.mp4` tutorial as fresh Markdown + PDF under the new advisory co-editor flow

### Delivery Notes

- The public Markdown contract is now stricter: internal grounding artifacts stay in JSON sidecars, not the final tutorial.
- The draft for `AgentFlowComplete_compressed.mp4` now includes context, a table of contents, and back-to-top navigation, and no longer leaks evidence blocks.
- Expensive tutorial stages now run through `lee-llm-router`, with cheap planning/evidence stages staying on cheaper OpenRouter roles and the default ChatGPT Plus routing narrowed to writer + technical reviewer for reliability.
- Validation, technical review, and adversarial review now act as co-editors. They always run, produce machine-readable findings, and surface warnings without blocking fresh final artifacts.
- Test As Lee republished `AgentFlowComplete_compressed.mp4` as fresh Markdown and PDF and verified the updated timestamps.
- Real-user reliability fixes in this sprint included config-relative router path fallback, wall-clock timeout hardening in `lee-llm-router`, and default router-role tuning to avoid a slow adversarial stage on the subscription path.

### Acceptance Criteria

1. Published tutorials read like public tutorials rather than organized transcript notes.
2. Final Markdown never leaks `Evidence:` blocks or internal review language.
3. Navigation requirements are enforced consistently and can be relaxed only through the tutorial definition flags.
4. Real screencast reruns complete the full draft → review loop without hanging and always produce a fresh latest Markdown artifact after outline approval.
5. Editorial findings are preserved as machine-readable warnings and reroute hints, not as tutorial-quality vetoes.
6. The real `AgentFlowComplete_compressed.mp4` flow republishes fresh Markdown and PDF artifacts under the advisory co-editor model.

---

## Sprint 11 — Tutorial Pedagogy and Ghostwriting Quality

**Status**: ⏳ In Progress  
**Goal**: Improve the published tutorial itself so it teaches the underlying workflow cleanly, sounds like the speaker coached by a top-notch educator, and demotes incidental environment/setup details.

### Scope

- [ ] Improve planner step selection so remote-access and recording context do not become core steps unless required
- [x] Add a source-interpretation stage so planning gets an explicit core-workflow vs scaffolding artifact
- [x] Strengthen writer prompts and skills around context, payoff, and learner-oriented sequencing
- [x] Tighten technical/adversarial review prompts around “is this actually a good public tutorial?”
- [x] Reduce repeated “step title not represented” and similar low-signal findings in the final warning set
- [x] Add a terminology spellcheck/copy-edit guard for obvious product-name mistakes such as `Codex`/`codecs`
- [x] Re-run `AgentFlowComplete_compressed.mp4` and compare quality against the current refreshed Markdown/PDF

### Acceptance Criteria

1. The first actionable section starts with the real workflow instead of environmental setup.
2. The opening context explains what the tutorial is for and why it matters in a tighter, more public-facing way.
3. The final Markdown reads less like project notes and more like an authored tutorial in the speaker’s voice.

### Delivery Notes

- Planner guidance now explicitly prefers the first irreversible workflow action
  over setup scaffolding like remote access, recording context, and project-folder
  choreography.
- The pipeline now writes `source_interpretation.json` before planning and feeds
  it into planning, evidence mapping, visual selection, writing, and review so
  every downstream stage can see the intended core workflow and demoted setup.
- Source interpretation now normalizes setup-first `best_first_action` values
  toward the first substantive emphasized action, and outline normalization
  deterministically reorders the first actionable step when the planner still
  leaves a demoted setup step first.
- Technical and adversarial review prompts now explicitly attack weak payoff,
  setup-first sequencing, and project-note voice rather than only structural
  hygiene.
- Validation now reports `incidental_setup_priority` when the outline leads with
  setup while later steps contain the real workflow, and repeated identical
  warning messages are deduplicated before they flow back into revision/failure
  summaries.
- Outline normalization now applies the narrow `Codex` terminology copy edit as
  well, so planner artifacts stop feeding obvious homophone mistakes into later
  stages.
- Router config now maps `tutorial.source-interpretation` to a dedicated
  `tutorial_interpreter` role in both live and example configs.
- Public tutorial drafts now get a narrow deterministic copy-edit pass for
  obvious tool-name confusions before validation runs.
- Regression coverage now checks that a draft containing `GPT 5.3 codecs` or
  similar public-facing wording is normalized to `Codex` in the final Markdown.
- Published tutorial runs now auto-trigger the downstream render step by
  default so a fresh `tutorial_final.md` no longer leaves a stale older PDF on
  disk, while `--skip-render` preserves the explicit Markdown-only workflow.
- Test As Lee now surfaces wrapped routed-task timeouts as
  `llm_router_timeout[...]` instead of blank router failures, and the default
  routed tutorial timeout budget in `config/channels.toml` plus the live/example
  router YAMLs is now 120 seconds so the real `tutorial.evidence` stage can
  finish without false failures.
- Outline normalization and validation now treat the first actionable step as
  the thing that must align with `best_first_action`, and can move the
  interpreted first action ahead of a leading text-only setup step within the
  first actionable section.
- The latest full default `AgentFlowComplete_compressed.mp4` rerun completes
  end-to-end again with fresh `tutorial_final.md`, `tutorial_final.html`,
  `tutorial_final.pdf`, and `render_manifest.json`, and the first actionable
  section now starts with AI planning instead of folder setup.
- The remaining Sprint 11 gap is content quality, not runtime completion:
  the live tutorial is still too summary-like, too disclaimer-heavy, and still
  lacks minimally actionable prompt/artifact examples for key workflow steps.

### Next Execution Slice

- [ ] Collapse intro/context pseudo-steps into one compact opening block
  - done when the live outline no longer creates separate weak steps for
    `what you will have by the end`, `why this matters`, or similar generic
    orientation copy unless the source explicitly teaches them
- [ ] Add minimally actionable prompt and artifact examples for the core phases
  - done when planning, sprinting, review, and run sections each include at
    least one reusable prompt or artifact pattern without inventing unsupported
    shell commands
- [ ] Remove public-artifact scaffolding sections from the live draft
  - done when the final Markdown no longer creates sections like
    `Text-Only and Visual Notes` and instead folds necessary caveats into the
    relevant context or step
- [ ] Improve weak-visual handling
  - done when non-text-only steps either have materially stronger captions /
    image explanation or are downgraded to justified text-only
- [ ] Re-run full Test As Lee acceptance on `AgentFlowComplete_compressed.mp4`
  - done when the default live `tutorial` flow completes end-to-end and the
    remaining warning set is materially smaller and higher-signal than the
    March 7, 2026 13:52 local run

---

## Sprint 9 — Tutorial PDF Rendering

**Status**: ✅ Completed (2026-03-06)  
**Goal**: Render published Markdown tutorials into HTML/PDF with explicit screenshot validation and render provenance.

### Scope

- [x] Add a downstream `render` CLI command that consumes `tutorial_manifest.json`
- [x] Add image validation for Markdown screenshot references before render
- [x] Add Pandoc-driven HTML rendering from `tutorial_final.md`
- [x] Add Chrome-family PDF rendering from generated HTML
- [x] Add `render_manifest.json` with toolchain, image validation, and output status
- [x] Add tests for:
  - successful HTML/PDF render
  - missing-image failure
  - missing tutorial markdown failure
  - repeatable reruns
  - render CLI behavior
- [x] Update README and sample config for renderer settings

### Delivery Notes

- Markdown remains the canonical authored tutorial artifact.
- PDF rendering is a separate downstream step and never reruns tutorial generation.
- Screenshot preservation is a hard requirement: missing image references fail the render before Pandoc/PDF generation runs.
- The renderer clears stale HTML/PDF outputs before each attempt so failed renders do not look successful.
- On macOS, the PDF backend prefers Google Chrome when available because Chromium may not exit cleanly after printing headless PDFs.

### Acceptance Criteria

1. User can render a published tutorial manifest into HTML/PDF with one CLI command.
2. Missing tutorial images fail the render with a clear machine-readable manifest.
3. Render outputs live under the tutorial directory beside `tutorial_final.md`.
4. Lint/format/tests pass and Test As Lee passes on a real tutorial directory.

---

## Sprint 8 — Multi-Agent Tutorial Generation

**Status**: ✅ Completed (2026-03-06)  
**Goal**: Turn `tutorial_asset_bundle.json` into an approval-gated written tutorial workflow with role-based agents, reusable skills, validation, review, and revision artifacts.

### Scope

- [x] Add a downstream `tutorial` CLI command that consumes `tutorial_asset_bundle.json`
- [x] Add repo-local tutorial agent role files under `agents/`
- [x] Add repo-local tutorial skills under `skills/`
- [x] Add tutorial pipeline stages for:
  - definition of done
  - planning
  - evidence mapping
  - visual selection
  - drafting
  - validation
  - technical review
  - adversarial review
  - review response
- [x] Add outline approval gate before drafting continues
- [x] Add `tutorial_definition.json`, `lesson_outline.json`, `evidence_map.json`, `frame_selection_plan.json`
- [x] Add `tutorial_validation_report.json`, `technical_review_report.json`, `adversarial_review_report.json`, `tutorial_revision_plan.json`
- [x] Add `tutorial_manifest.json` with agent/skill digests and review outcomes
- [x] Add `tutorial_final.md` when the tutorial clears the gate
- [x] Add cache reuse keyed by bundle contents plus agent/skill versions
- [x] Add tests for approval gating, blocking review paths, reroute behavior, text-only validation, CLI behavior, and cache invalidation

### Delivery Notes

- The tutorial pipeline is downstream-only and never reruns transcript or frame extraction.
- A first tutorial run stops at `awaiting_outline_approval` until the human reruns with `--approve-outline`.
- Adversarial review is mandatory before `tutorial_final.md` becomes publish-eligible.
- Prompt behavior now lives in repo-local `agents/` and tutorial-specific `skills/`, while orchestration stays in Python.

### Acceptance Criteria

1. User can generate an outline package from `tutorial_asset_bundle.json` with one CLI command.
2. Drafting does not continue until the outline is explicitly approved.
3. Review artifacts are written in machine-readable form before publish.
4. Prompt/skill changes are visible in `tutorial_manifest.json`.
5. Re-running with unchanged bundle and unchanged agent/skill files reuses cached outputs.
6. Lint/format/tests pass and Test As Lee passes.

---

## Sprint 7 — Tutorial Asset Extraction Foundation

**Status**: ✅ Completed with Closeout Remediation (2026-03-06)  
**Goal**: Produce a stable, source-agnostic data package for later tutorial generation by adding transcript JSON, frame candidate extraction, and bundle manifests.

### Scope

- [x] Add source-agnostic ingest support for local video files alongside YouTube video targets
- [x] Generalize source/video models and storage keys to support `youtube_video` and `local_file`
- [x] Add canonical `transcript.json` artifact with normalized segment timing and provenance
- [x] Add frame candidate extraction using `ffmpeg` scene detection
- [x] Write frame files under per-video `frames/` directories
- [x] Add `frame_manifest.json` referencing frame files and extraction metadata
- [x] Add `tutorial_asset_bundle.json` referencing transcript, frame, and metadata artifacts
- [x] Add config/CLI support for local files:
  - `[[files]]` targets
  - `--video-file`
- [x] Add tests for:
  - local file config parsing
  - transcript JSON generation
  - frame manifest generation
  - idempotent reruns with transcript + frame artifacts
- [x] Update README and sample config for the canonical asset bundle workflow

### Delivery Notes

- Local media files can now be processed through `--video-file` and `[[files]]`.
- Successful runs write `transcript.json`, `frame_manifest.json`, and `tutorial_asset_bundle.json`.
- Missing local file inputs are surfaced as failed runs instead of silent no-op success.
- Manual validation passed using a real local `.mp4` plus sidecar `.vtt`, followed by an idempotent rerun.
- `tutorial_asset_bundle.json` now records `frame_capture.status` and any extraction error whenever `transcript.json` exists.
- Frame extraction now stages into a temporary directory before replacing `frames/`.
- Local media IDs are locked to content fingerprints and covered by regression tests.

### Closeout Remediation

- [x] Make frame extraction failures visible in canonical bundle output and run status
- [x] Make frame extraction replace `frames/` atomically so failed reruns do not destroy prior assets
- [x] Lock local file IDs to stable content fingerprints with regression coverage
- [x] Record the extraction design decisions in `architecture.md`

### Acceptance Criteria

1. User can process either a YouTube video URL or a local `.mp4` file with one CLI.
2. Successful runs write exact transcript artifacts plus `transcript.json`.
3. Successful runs write frame image files to disk plus `frame_manifest.json`.
4. `tutorial_asset_bundle.json` references artifact files rather than embedding image data.
5. Existing run reporting and idempotency semantics remain intact.
6. Lint/format/tests pass.

---

## Sprint 6 — ASR Plugin Architecture (Productionizing Caption Fallback)

**Status**: ✅ Completed (2026-03-05)  
**Goal**: Add production-ready transcript fallback using pluggable ASR providers, with `fast-whisper` as the first implementation.

### Scope

- [x] Add ASR plugin contract + provider registry
- [x] Implement `fast-whisper` provider plugin
- [x] Add ASR app config options (`enable_asr_fallback`, provider/model/device, ffmpeg)
- [x] Add single-video clip options (`clip_start`, `clip_end`, `force_asr`) in config
- [x] Integrate fallback path in `SingleVideoTranscriber`:
  - captions first, ASR fallback when unavailable
  - optional force-ASR mode
  - optional clip transcription
- [x] Persist ASR metadata/artifacts and run-item statuses
- [x] Add CLI runtime overrides (`--asr-fallback`, `--force-asr`, `--clip-start`, `--clip-end`)
- [x] Add tests for plugin registry, config parsing, and fallback behavior
- [x] Update README and config examples

### Acceptance Criteria

1. If captions are unavailable and ASR fallback is enabled, exact transcript artifacts are still produced via ASR.
2. `fast-whisper` is an implementation behind a swap-friendly plugin interface (no orchestrator changes needed for future providers).
3. Single-video targets can define clip bounds and force-ASR behavior.
4. Pipeline remains idempotent and existing run/report behavior remains intact.
5. Lint/format/tests pass.

---

## Sprint 5 — Core Refactor (Single Video + Wrapper)

**Status**: ✅ Completed (2026-03-04)  
**Goal**: Separate per-video transcription into a dedicated service and keep channel processing as a wrapper orchestration layer with unified channel/video target config.

### Scope

- [x] Add `SingleVideoTranscriber` service for one-video end-to-end processing
- [x] Refactor `Orchestrator` to use wrapper + single-video service split
- [x] Add config support for explicit single-video targets (`[[videos]]`) in addition to `[[channels]]`
- [x] Add CLI target options:
  - `--channel-url` (repeatable)
  - `--video-url` (repeatable)
  - keep `--url` for backward compatibility
- [x] Keep existing date-range and idempotency semantics for all target types
- [x] Add tests for:
  - config parsing with `[[videos]]`
  - CLI target flag merging behavior
  - orchestrator wrapper invoking single-video processor correctly
- [x] Update docs with new target configuration examples

### Acceptance Criteria

1. User can run single-video mode and channel mode through one CLI.
2. Config file can define both channel and single-video targets.
3. Channel runs still respect `--from/--to` and `--reprocess`.
4. Existing output schema/artifact naming remains stable.
5. Test suite passes after refactor.

---

## Sprint 4 — Reliability Hardening (Current)

**Status**: ✅ Completed (2026-03-04)  
**Goal**: Close high-priority review gaps: Python version contract, timeout safety, docs portability, and one-command reproducible checks.

### Scope

- [x] Resolve Python compatibility contract:
  - Option A: bump runtime support to `>=3.11`
  - Option B: refactor `datetime.UTC` usage to `timezone.utc` for 3.10 support
- [x] Add `yt-dlp` subprocess timeout and timeout-aware retry/error reporting
- [x] Add LLM request timeout and bounded retries with clear failure reason tags
- [x] Convert absolute local markdown links to relative project links
- [x] Make tests reproducible from a clean clone:
  - add pytest config/path behavior in `pyproject.toml` or
  - codify editable install requirement and enforce in CI
- [x] Add CI workflow gates for:
  - `ruff check src tests`
  - `black --check src tests`
  - `pytest -q`
- [x] Add targeted tests for:
  - yt-dlp timeout path
  - LLM timeout/retry path
  - Python version contract expectations

### Acceptance Criteria

1. No runtime contract mismatch remains between `requires-python` and code usage.
2. External calls (yt-dlp + LLM) fail fast with bounded retries and explicit run-item error messages.
3. `README.md` and design docs are portable (no machine-specific absolute file links).
4. A fresh environment can run the documented verification commands successfully.
5. CI enforces lint/format/test checks on every push/PR.

---

## Sprint 1 — Foundation

**Status**: ✅ Completed (2026-03-04)  
**Goal**: Deliver Slice 1 MVP: exact transcript pipeline with idempotent new-video detection and optional date-range filtering.

### Scope

- [x] Normalize Python package path to `src/lunduke_transcripts/` and update entrypoint wiring
- [x] Implement config loading (`config/channels.toml`) and runtime defaults
- [x] Implement CLI command: `run --config --from --to --reprocess`
- [x] Implement YouTube adapter using `yt-dlp` (video discovery + caption acquisition)
- [x] Implement SQLite schema for `videos`, `transcripts`, `runs`, `run_items`
- [x] Implement orchestrator for discovery → filtering → fetch → write → report
- [x] Implement idempotent new-video behavior keyed by `video_id`
- [x] Implement date-range filtering on `published_at` (inclusive bounds)
- [x] Write artifacts:
  - `metadata.json`
  - `transcript_exact.vtt`
  - `transcript_exact.md`
  - run summary JSON in `data/runs/`
- [x] Add unit + integration tests for idempotency and date-range behavior
- [x] Test As Lee: run CLI twice (second run zero duplicates)

### Acceptance Criteria

1. `lunduke-transcripts run --config ...` processes new videos and writes exact transcript + metadata artifacts.
2. `--from/--to` limits candidates to matching `published_at` range (inclusive).
3. Second run without new videos reports zero new processed items.
4. One video failure does not abort entire run.
5. Tests pass and manual Test As Lee passes.

---

## Sprint 2 — LLM Cleanup

**Status**: ✅ Completed (2026-03-04)  
**Goal**: Deliver Slice 2 MVP: cleaned transcript generation without changing meaning.

### Scope

- [x] Implement LLM adapter interface (provider-agnostic; OpenAI first)
- [x] Implement cleanup prompt and guardrails (no summarize/invent)
- [x] Generate `transcript_clean.md` from exact transcript input
- [x] Persist cleanup metadata (model, timestamp, prompt/version)
- [x] Cache cleanup by exact transcript hash to avoid repeat cost
- [x] Add tests for cleanup contract and failure handling
- [x] Test As Lee: exact + cleaned outputs side-by-side validation

### Acceptance Criteria

1. Cleaned transcript is produced when cleanup is enabled.
2. Exact transcript remains unchanged and always retained.
3. Cleanup failures do not block exact transcript pipeline completion.
4. Cleanup output provenance is saved in metadata.

---

## Sprint 3 — Scheduling and Hardening

**Status**: ✅ Completed (2026-03-04)  
**Goal**: Deliver Slice 3 MVP: reliable unattended operation and operational clarity.

### Scope

- [x] Provide scheduler recipes (`cron` and `launchd`) using same run command
- [x] Add retry/backoff for transient extraction failures
- [x] Improve run reports (counts, failure reasons, filter metadata)
- [x] Add multi-channel config ergonomics and validation
- [x] Add operational docs and troubleshooting section in README
- [x] Test As Lee: unattended-style scheduled invocation simulation

### Acceptance Criteria

1. User can schedule one command and run unattended.
2. Run reports clearly show successes/failures with actionable reasons.
3. Multi-channel configuration works in one run.

---

## Cross-Sprint Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| YouTube extraction format changes | Discovery/fetch failures | Keep adapter boundary, add retries, pin + update `yt-dlp` |
| Missing captions on videos | Partial coverage | Explicit unavailable status; continue processing |
| Cleanup may alter intent | Trust risk | Keep exact transcript canonical; strict cleanup contract |
| Scope creep in early sprints | Delivery delay | Enforce sprint acceptance criteria before adding extras |

---

## Execution Rules (AgentFlow)

Every sprint item follows:

1. Code
2. Test
3. Test As Lee
4. Fix
5. Loop until green
6. Document updates (`context.md`, `WHERE_AM_I.md`, `result-review.md`, this file)
7. Commit and push

Done checklist for each completed work unit:

- [x] Mode acknowledged and respected
- [x] Tests pass clean
- [x] Test As Lee completed
- [x] Required docs updated
- [x] Committed and pushed with descriptive message

---

Last updated: 2026-03-06
