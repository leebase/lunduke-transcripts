# lunduke-transcripts Session Context

> **Purpose**: Working memory for session continuity.

---

## Snapshot

| Attribute | Value |
|-----------|-------|
| **Phase** | Tutorial Quality Refinement + Selective GPT-5.4 Routing |
| **Mode** | 2 (Implementation with approval) |
| **Last Updated** | 2026-03-07 |

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
Sprint 10 is tightening tutorial quality so the public Markdown reads like a
real tutorial, while selectively routing the expensive tutorial-writing stages
through `lee-llm-router` and the ChatGPT Plus `gpt-5.4` model.

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
- ✅ Added tutorial-quality skills for narrative, navigation, public-artifact hygiene, step selection, and tutorial-quality review
- ✅ Tightened writer/planner/reviewer prompts around context, TOC, back-to-top navigation, and banning leaked `Evidence:` blocks
- ✅ Changed adversarial tutorial review to advisory-only while keeping it mandatory before publish
- ✅ Ran formal code review, found validator contract/navigation gaps, and fixed both with regression coverage
- ✅ Added tests for definition-controlled structure requirements and per-section back-to-top enforcement
- ✅ Added optional `lee-llm-router` task routing for selected tutorial stages
- ✅ Added router config/env support plus task-to-role mappings for tutorial stages
- ✅ Fixed the ChatGPT subscription provider to send required `instructions`, `stream = true`, and SSE parsing without unsupported `temperature`
- ✅ Fixed the live screencast tutorial rerun so it now completes the full review loop and returns `blocked` cleanly instead of hanging
- ✅ Verified that `tutorial.writer`, `tutorial.technical-review`, and `tutorial.adversarial-review` run on ChatGPT Plus `gpt-5.4`
- ✅ Fixed router config/repo/trace paths to resolve relative to the config file, not the current working directory

### In Progress
- ⏳ Tuning frame selection quality and tutorial voice/ghostwriting behavior
- ⏳ Improving tutorial evidence selection so the `AgentFlowComplete_compressed.mp4` tutorial can clear review instead of blocking

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
| Adversarial review is advisory-only | It should inject counter-pressure and reroute ideas without outweighing validator/technical review | 2026-03-07 |
| Public tutorial Markdown must enforce context, TOC, navigation, and no leaked evidence notes | Final output should read like a tutorial, not a transcript with internal scaffolding | 2026-03-07 |
| Expensive tutorial stages route through `lee-llm-router` and ChatGPT Plus `gpt-5.4` | Writing/review quality benefits from a stronger model while cheap planning/evidence stages stay on cheaper models | 2026-03-07 |
| Router paths resolve relative to the chosen config file | Tutorial routing should not depend on launching the CLI from the repo root | 2026-03-07 |

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
4. Should blocked tutorial runs optionally render a `tutorial_draft.pdf` for human review?

---

## Next Actions Queue (ranked)

| Rank | Action | Owner | Done When |
|------|--------|-------|----------|
| 1 | Improve tutorial step selection so incidental setup does not dominate the lesson | Human+AI | Screencast tutorials skip or demote environment setup that is not core to the workflow |
| 2 | Keep strengthening tutorial voice and ghostwriting quality | Human+AI | Tutorials read like the speaker coached by a top educator, not prettified transcripts |
| 3 | Decide whether blocked tutorials should render a draft PDF for review | Human+AI | A blocked rerun can still produce a human-reviewable PDF without pretending the tutorial is publishable |
| 4 | Add the next renderer target after PDF | Human+AI | DOCX or PPTX export works from the published tutorial artifacts |

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
- [x] Committed and pushed with descriptive message
