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
- Priority: harden compatibility, reliability, and reproducibility for production use

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

Last updated: 2026-03-04
