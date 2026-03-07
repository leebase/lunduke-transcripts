# lunduke-transcripts Session Context

> **Purpose**: Working memory for session continuity.

---

## Snapshot

| Attribute | Value |
|-----------|-------|
| **Phase** | Sprint 11 Tutorial Pedagogy Implementation |
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
now in implementation: planner/writer/reviewer prompts have been tightened
around learner payoff and setup demotion, outline normalization now applies the
narrow `Codex` terminology fix, validator heuristics now flag setup-first
lesson structure, repeated identical warning text is deduplicated before it
feeds revision/failure summaries, and a new `source_interpretation.json`
artifact now exists upstream of planning to distinguish the core workflow from
scaffolding. Test As Lee has now also pushed the live path harder: routed task
timeouts are surfaced cleanly instead of hanging or failing with blank router
errors, the default routed tutorial timeout budget is now 120 seconds, and the
real screencast flow completes end-to-end again with fresh Markdown/HTML/PDF.
The remaining blocker is tutorial quality, not runtime completion.

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
- ✅ Tightened Sprint 11 planner/writer/reviewer prompts around learner payoff, public-tutorial voice, and setup-first sequencing defects
- ✅ Added outline-level `incidental_setup_priority` validation for setup-first lesson plans
- ✅ Reduced low-signal tutorial warning churn by relaxing title-representation matching and deduplicating repeated failure/advisory messages
- ✅ Extended the narrow `Codex` terminology copy edit into normalized lesson outlines
- ✅ Added Sprint 11 regression coverage for incidental setup detection, outline terminology normalization, and warning deduplication
- ✅ Added a new `source-interpreter` stage plus `source_interpretation.json` and threaded that artifact into planning, evidence, visual selection, writing, and review
- ✅ Added live/example router-role mappings for `tutorial.source-interpretation`
- ✅ Test As Lee confirmed the new interpretation artifact and refreshed live outline are generated for `AgentFlowComplete_compressed.mp4`
- ✅ Tightened source interpretation so setup-first `best_first_action` values normalize toward the first substantive emphasized action
- ✅ Added deterministic outline realignment so the first actionable step follows the interpreted first action when the planner still leaves setup first
- ✅ Test As Lee confirmed a workspace-codepath live rerun now starts the refreshed outline with `Engage AI as a Co-Thinker...` instead of project-folder creation
- ✅ Added CLI-side stale-artifact cleanup for `tutorial --reprocess` so interrupted reruns cannot leave an old PDF/render manifest masquerading as fresh output
- ✅ Added routed-task timeout handling in `src/lunduke_transcripts/infra/llm_adapter.py` so wrapped `lee-llm-router` timeouts surface as `llm_router_timeout[...]` instead of blank request failures
- ✅ Raised the default routed tutorial timeout budget to 120 seconds in `config/channels.toml` and both tutorial router YAMLs so the real `tutorial.evidence` stage can finish
- ✅ Tightened planner/writer prompt contracts so unsupported payoff/extension sections and top-level scaffolding sections are discouraged explicitly
- ✅ Hardened outline normalization so the interpreted first real action can move ahead of leading text-only setup within the first actionable section
- ✅ Test As Lee reran the default live screencast flow end-to-end and refreshed `tutorial_final.md`, `tutorial_final.html`, `tutorial_final.pdf`, and `render_manifest.json` without lingering
- ✅ Test As Lee confirmed the first actionable section now starts with AI planning instead of folder setup in the live final tutorial

### In Progress
- ⏳ Finishing Sprint 11 ghostwriting work so the live screencast stops reading like a workflow summary and starts teaching with minimally actionable prompts/artifacts
- ⏳ Tightening planner/evidence/writer behavior so unsupported intro payoff steps, speculative extension steps, and disclaimer-heavy scaffold sections stop appearing in the live tutorial
- ⏳ Improving visual support quality so non-text steps are not backed only by weak screenshots

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
| Sprint 11 pedagogy checks should be machine-visible when possible | Prompt-only coaching is too weak; setup-first lesson structure and noisy duplicate warnings need validator/report support | 2026-03-07 |
| Planning should consume an explicit source-interpretation artifact | The live screencast needed a separate "what is this really teaching?" summary before planning, not just stronger planner instructions | 2026-03-07 |
| Routed tutorial tasks need an explicit wall-clock budget larger than the old 60s default | The real `tutorial.evidence` stage can legitimately run past 60 seconds; a 120-second budget plus clear timeout surfacing keeps Lee's path bounded without silent hangs or blank errors | 2026-03-07 |

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
5. How should Sprint 11 supply minimally actionable prompt/artifact examples when the source is a workflow demo rather than a command-by-command tutorial?

---

## Next Actions Queue (ranked)

| Rank | Action | Owner | Done When |
|------|--------|-------|----------|
| 1 | Keep strengthening tutorial voice and ghostwriting quality | Human+AI | Tutorials read like the speaker coached by a top educator, not a cautious workflow summary |
| 2 | Add minimally actionable prompt/artifact examples without overstating what the screencast proves | Human+AI | Core planning, sprinting, review, and run sections teach concrete takeaways instead of caveat-heavy abstraction |
| 3 | Improve screenshot usefulness or justify more text-only steps | Human+AI | Non-text steps stop failing on weak visual support |
| 4 | Keep pushing live step selection from AI planning into transcript-processing execution | Human+AI | The tutorial moves from project planning into fetching/processing transcripts earlier in the lesson |
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
- [x] Tested As Lee: ran app as a user, recorded the remaining live-run hang and quality gap
- [x] Updated: context.md, WHERE_AM_I.md, result-review.md, sprint-plan.md
- [ ] Committed and pushed with descriptive message
