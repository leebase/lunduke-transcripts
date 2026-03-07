# lunduke-transcripts Session Context

> **Purpose**: Working memory for session continuity.

---

## Snapshot

| Attribute | Value |
|-----------|-------|
| **Phase** | Markdown + PDF Tutorial Pipeline Delivered |
| **Mode** | 2 (Implementation with approval) |
| **Last Updated** | 2026-03-06 |

### Sprint Status
| Sprint | Status | Completion |
|--------|--------|------------|
| Sprint 9 — Tutorial PDF Rendering | ✅ Completed | 100% |
| Sprint 8 — Multi-Agent Tutorial Generation | ✅ Completed | 100% |
| Sprint 7 — Tutorial Asset Extraction Foundation | ✅ Completed with Closeout Remediation | 100% |
| Sprint 6 — ASR Plugin Architecture | ✅ Completed | 100% |
| Sprint 4 — Reliability Hardening | ✅ Completed | 100% |
| Sprint 1 — Foundation | ✅ Completed | 100% |
| Sprint 2 — LLM Cleanup | ✅ Completed | 100% |
| Sprint 3 — Scheduling and Hardening | ✅ Completed | 100% |

---

## What's Happening Now

### Current Work Stream
Sprint 9 PDF rendering is complete; next work is improving frame selection
quality, tutorial voice, and additional renderer targets.

### Recently Completed
- ✅ Created `product-definition.md` and `design.md`
- ✅ Implemented full Python package pipeline in `src/lunduke_transcripts/`
- ✅ Added `run` CLI with `--from`, `--to`, and `--reprocess`
- ✅ Added `yt-dlp` discovery/transcript acquisition adapter
- ✅ Added SQLite storage (`videos`, `transcripts`, `runs`, `run_items`)
- ✅ Added exact transcript artifacts and metadata outputs
- ✅ Added LLM cleanup adapter + prompt guardrails + hash-based cleanup cache
- ✅ Added scheduler assets (`scripts/run_pipeline.sh`, launchd example)
- ✅ Added tests for VTT parsing and date-range/idempotency behavior
- ✅ Test As Lee completed via live CLI runs against a real channel
- ✅ Added article generation with paragraph-end timestamp normalization
- ✅ Added OpenRouter-focused `.env` configuration flow
- ✅ Fixed undated artifact folder migration to dated names when publish time exists
- ✅ Completed Sprint 4 hardening: Python contract, timeouts/retries, portable docs links, CI workflow
- ✅ Completed Sprint 6 ASR plugin architecture with `fast-whisper` fallback
- ✅ Reframed product/design docs around transcript JSON + frame manifest outputs
- ✅ Added local file ingest via `[[files]]` and `--video-file`
- ✅ Added `transcript.json`, `frame_manifest.json`, and `tutorial_asset_bundle.json`
- ✅ Added scene-change frame extraction via `ffmpeg`
- ✅ Added explicit failure reporting for missing local file inputs
- ✅ Test As Lee passed for local `.mp4` + sidecar captions and rerun idempotency
- ✅ Added degraded bundle output with explicit frame capture status/error metadata
- ✅ Made frame extraction replace `frames/` only after successful extraction
- ✅ Added regression coverage for stable local IDs and frame failure handling
- ✅ Added `architecture.md` for extraction design decisions and review protocol alignment
- ✅ Added repo-local `agents/` role files and tutorial-specific `skills/`
- ✅ Added downstream `tutorial` CLI command for multi-agent tutorial generation
- ✅ Added outline approval gate plus tutorial validation/review/revision artifacts
- ✅ Added agent/skill digest tracking and manifest-based tutorial cache reuse
- ✅ Test As Lee passed for `tutorial` approval gate, publish flow, cache reuse, and missing-bundle failure
- ✅ Added downstream `render` CLI command for tutorial HTML/PDF generation
- ✅ Added Pandoc + Chrome-family PDF rendering with screenshot validation
- ✅ Added `render_manifest.json` plus stale-output cleanup on rerender/failure
- ✅ Test As Lee passed for real screencast HTML/PDF rendering and broken-image failure handling

### In Progress
- ⏳ Tuning frame selection quality and tutorial voice/ghostwriting behavior

---

## Decisions Locked

| Decision | Rationale | Date |
|----------|-----------|------|
| Python remains primary stack | Best fit for local pipeline + LLM workflow velocity | 2026-03-04 |
| `yt-dlp` adapter boundary | Handles YouTube extraction volatility behind one interface | 2026-03-04 |
| SQLite as state source of truth | Strong idempotency and run history with low ops cost | 2026-03-04 |
| Date filters are inclusive | Matches user expectation and product definition | 2026-03-04 |
| Exact transcript is canonical | Protects fidelity when cleanup output changes wording | 2026-03-04 |
| Frame image bytes stay out of JSON | Keep manifests portable, inspectable, and small | 2026-03-06 |
| Scene detection chooses frame candidates first | Deterministic extraction now, semantic selection later | 2026-03-06 |
| Local file IDs use content fingerprints | Keeps local reruns stable across touch/rename/move operations | 2026-03-06 |
| Missing explicit local file inputs fail the run | User input errors must not look like success | 2026-03-06 |
| Frame extraction failures still write the bundle but fail the run | Downstream tools get one canonical manifest without masking a bad extraction | 2026-03-06 |
| Frame replacements are staged before swap | Reprocessing must not destroy the last known-good frame set | 2026-03-06 |
| Tutorial prompts live in repo-local agent and skill files | Prompt evolution should be versioned and decoupled from orchestration code | 2026-03-06 |
| Tutorial publishing requires outline approval plus validation and review gates | The tutorial workflow should mirror the project's code-review discipline | 2026-03-06 |
| Markdown remains canonical and PDF render is downstream-only | Content generation and document formatting should stay independent | 2026-03-06 |
| Tutorial render validates images before running Pandoc/PDF | Screenshot-heavy tutorials must fail fast on broken image references | 2026-03-06 |
| Chrome-family browser backend is preferred for HTML-to-PDF | Browser rendering handles screenshot-heavy layouts better than a direct PDF path | 2026-03-06 |

---

## Document Inventory

### Planning (Stable)
| File | Purpose | Status |
|------|---------|--------|
| `product-definition.md` | Product vision and constraints | ✅ Active |
| `design.md` | Architecture and implementation design | ✅ Active |
| `architecture.md` | Technical decision log | ✅ Active |
| `project-plan.md` | Strategic roadmap | 🟡 Template, needs refresh |
| `sprint-plan.md` | Tactical execution and status | ✅ Updated |
| `AGENTS.md` | AI operational protocol | ✅ Active |

### Session Memory (Dynamic)
| File | Purpose | Status |
|------|---------|--------|
| `context.md` | Working state, current focus, next actions | 🔄 Active |
| `result-review.md` | Running log of completed work | 🔄 Active |
| `WHERE_AM_I.md` | Product-level milestone compass | 🔄 Active |

---

## Open Questions (keep short)

1. Should semantic frame selection use transcript heuristics first, LLM first, or a hybrid?
2. Should the visual editor move from metadata-only frame selection to a vision-aware review pass?
3. Is DOCX or PPTX the next renderer target after PDF?
4. How much pedagogical uplift should tutorial generation allow while still sounding like the speaker?

---

## Next Actions Queue (ranked)

| Rank | Action | Owner | Done When |
|------|--------|-------|----------|
| 1 | Upgrade frame selection from raw candidate metadata to stronger instructional selection | Human+AI | Visual editor chooses more tutorial-worthy frames with fewer weak screenshots |
| 2 | Rework tutorial prompts toward stronger ghostwritten educational output | Human+AI | Tutorials read like the speaker coached by a top educator, not prettified transcripts |
| 3 | Add the next renderer target after PDF | Human+AI | DOCX or PPTX export works from the published tutorial artifacts |
| 4 | Revisit cleanup/article defaults for tutorial workflows | Human+AI | Transcript post-processing policy fits training-output generation |

---

## Working Conventions

### Start of session
1. Read `AGENTS.md`
2. Read `context.md`
3. Read `WHERE_AM_I.md`
4. Execute highest-ranked next action

### End of work unit
1. Move completed items to "Recently Completed"
2. Update "Next Actions Queue"
3. Add new "Decisions Locked"
4. Keep "Open Questions" ≤ 5

---

## Environment Notes

- **Working Directory**: `./lunduke-transcripts`
- **Runtime**: Python 3.13 + project `.venv`
- **Key tools**: `yt-dlp`, `pytest`, `ruff`, `black`

---

## Done Checklist
- [x] Mode acknowledged: worked within autonomy boundaries
- [x] Tests pass clean (run profile-specific tests)
- [x] Tested As Lee: ran app as a user, fixed issues found
- [x] Updated: context.md, WHERE_AM_I.md, result-review.md, sprint-plan.md
- [ ] Committed and pushed with descriptive message
