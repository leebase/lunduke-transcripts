# lunduke-transcripts Session Context

> **Purpose**: Working memory for session continuity.

---

## Snapshot

| Attribute | Value |
|-----------|-------|
| **Phase** | Sprint 10 Closeout + Sprint 11 Tutorial Pedagogy Planning |
| **Mode** | 2 (Implementation with approval) |
| **Last Updated** | 2026-03-07 |

### Sprint Status
| Sprint | Status | Completion |
|--------|--------|------------|
| Sprint 10 — Tutorial Quality Refinement | ✅ Completed | 100% |
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
Sprint 10 is closed. The tutorial pipeline now uses advisory co-editors instead
of tutorial-quality hard gates, publishes a fresh latest artifact after outline
approval, auto-renders fresh HTML/PDF artifacts by default when a run reaches
`published`, and still supports explicit Markdown-only publishes via
`--skip-render`. Render failures now report a partial overall CLI result while
keeping the tutorial's published status explicit in the payload. Sprint 11 is
focused on making the tutorial itself read like a stronger piece of
ghostwritten instructional writing while tightening public artifact polish.

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
- ✅ Fixed the live screencast tutorial rerun so it now completes the full review loop without tutorial-quality `blocked` status
- ✅ Verified that `tutorial.writer` and `tutorial.technical-review` run on ChatGPT Plus `gpt-5.4`
- ✅ Fixed router config/repo/trace paths to resolve relative to the config file, not the current working directory
- ✅ Removed tutorial-quality hard gates so validation/technical/adversarial stages now act as co-editors
- ✅ Always run technical and adversarial review, even when validation finds defects
- ✅ Always write a fresh `tutorial_final.md` after outline approval and record unresolved issues as warnings in `tutorial_manifest.json`
- ✅ Fixed reroute control flow so `script-writer` and `visual-editor` reroutes continue cleanly
- ✅ Changed tutorial CLI exit behavior so editorial warnings do not return a failing exit code
- ✅ Added repo-root fallback for `config/...` router paths when config-relative resolution points at a missing path
- ✅ Added a wall-clock timeout guard to the ChatGPT subscription streaming provider in `lee-llm-router`
- ✅ Narrowed the default ChatGPT Plus routing to writer + technical reviewer for better real-run reliability
- ✅ Test As Lee republished `AgentFlowComplete_compressed.mp4` as fresh Markdown and PDF under the advisory co-editor model
- ✅ Added a deterministic public copy-edit pass plus regression coverage for obvious `Codex`/`codecs` name confusion
- ✅ Test As Lee regenerated the live screencast draft and confirmed the fresh public Markdown now uses `Codex` consistently with no terminology validation findings
- ✅ Fixed the stale-final-artifact gap by making published `tutorial` CLI runs auto-invoke downstream HTML/PDF rendering
- ✅ Added tutorial CLI regression coverage for auto-render success and render-failure exit behavior
- ✅ Added `--skip-render` so Markdown-only publishes do not depend on the renderer toolchain
- ✅ Changed tutorial CLI payload/status semantics so render failures report `status = "partial"` while preserving `tutorial_status = "published"`
- ✅ Re-ran the real screencast `render` CLI and refreshed `tutorial_final.html`, `tutorial_final.pdf`, and `render_manifest.json`

### In Progress
- ⏳ Sprint 11 planning: tutorial pedagogy, ghostwriting quality, and step selection
- ⏳ Evaluating how much stronger the writer/planner prompts should get before adding a source-interpretation stage
- ⏳ Investigating why some router-backed live `tutorial` CLI runs still linger after artifact refresh, including cached publish paths that should now only need the render handoff

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
| Tutorial generation uses outline approval plus advisory co-editor review | The workflow still mirrors code review, but tutorial stages improve the draft instead of vetoing publication | 2026-03-07 |
| Markdown remains canonical and PDF render is downstream-only | Content generation and document formatting should stay independent | 2026-03-06 |
| Tutorial render validates images before running Pandoc/PDF | Screenshot-heavy tutorials must fail fast on broken image references | 2026-03-06 |
| Chrome-family browser backend is preferred for HTML-to-PDF | Browser rendering handles screenshot-heavy layouts better than a direct PDF path | 2026-03-06 |
| Adversarial review is advisory-only | It should inject counter-pressure and reroute ideas without outweighing validator/technical review | 2026-03-07 |
| Public tutorial Markdown must enforce context, TOC, navigation, and no leaked evidence notes | Final output should read like a tutorial, not a transcript with internal scaffolding | 2026-03-07 |
| ChatGPT Plus routing is reserved by default for writer + technical reviewer | The heavy editorial stages benefit most from `gpt-5.4`; keeping red-team cheaper improves real-run reliability | 2026-03-07 |
| Router paths resolve relative to the chosen config file | Tutorial routing should not depend on launching the CLI from the repo root | 2026-03-07 |
| Repo-root fallback is allowed for `config/...` router assets | Real configs commonly point at repo-root config files even when the main TOML file lives under `config/` | 2026-03-07 |
| Editorial warnings no longer suppress fresh final artifacts | The latest approved tutorial should always be inspectable and renderable, even when reviewers still have objections | 2026-03-07 |
| Public tutorial drafts get deterministic copy-edits for known tool-name confusions before validation | Reader-facing output should not leak obvious ASR homophone mistakes like `codecs` when `Codex` is clearly intended | 2026-03-07 |
| Published tutorial CLI runs auto-trigger downstream PDF rendering by default, but Markdown-only publishes remain available | A fresh approved tutorial should not leave a stale older PDF pretending to be the latest final artifact, but the renderer must not become mandatory for every publish workflow | 2026-03-07 |

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
4. Should Sprint 11 add a dedicated source-interpretation stage before planning?
5. Why do some router-backed live `tutorial` runs linger in an SSL read after refreshing draft artifacts?

---

## Next Actions Queue (ranked)

| Rank | Action | Owner | Done When |
|------|--------|-------|----------|
| 1 | Improve tutorial step selection so incidental setup does not dominate the lesson | Human+AI | Screencast tutorials skip or demote environment setup that is not core to the workflow |
| 2 | Keep strengthening tutorial voice and ghostwriting quality | Human+AI | Tutorials read like the speaker coached by a top educator, not prettified transcripts |
| 3 | Decide whether to add a source-interpretation stage before planning | Human+AI | Planner/writer get a stronger “what is this video really about?” artifact |
| 4 | Investigate the lingering router-backed live tutorial processes seen during Test As Lee | Human+AI | The real `tutorial` CLI exits cleanly after refreshing artifacts instead of hanging in an SSL read |
| 5 | Add the next renderer target after PDF | Human+AI | DOCX or PPTX export works from the published tutorial artifacts |

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
