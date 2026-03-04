# lunduke-transcripts Session Context

> **Purpose**: Working memory for session continuity.

---

## Snapshot

| Attribute | Value |
|-----------|-------|
| **Phase** | MVP Implemented |
| **Mode** | 2 (Implementation with approval) |
| **Last Updated** | 2026-03-04 |

### Sprint Status
| Sprint | Status | Completion |
|--------|--------|------------|
| Sprint 1 — Foundation | ✅ Completed | 100% |
| Sprint 2 — LLM Cleanup | ✅ Completed | 100% |
| Sprint 3 — Scheduling and Hardening | ✅ Completed | 100% |

---

## What's Happening Now

### Current Work Stream
Hardening and next-iteration planning after MVP completion.

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

### In Progress
- ⏳ Post-MVP polish and optional enhancements

---

## Decisions Locked

| Decision | Rationale | Date |
|----------|-----------|------|
| Python remains primary stack | Best fit for local pipeline + LLM workflow velocity | 2026-03-04 |
| `yt-dlp` adapter boundary | Handles YouTube extraction volatility behind one interface | 2026-03-04 |
| SQLite as state source of truth | Strong idempotency and run history with low ops cost | 2026-03-04 |
| Date filters are inclusive | Matches user expectation and product definition | 2026-03-04 |
| Exact transcript is canonical | Protects fidelity when cleanup output changes wording | 2026-03-04 |

---

## Document Inventory

### Planning (Stable)
| File | Purpose | Status |
|------|---------|--------|
| `product-definition.md` | Product vision and constraints | ✅ Active |
| `design.md` | Architecture and implementation design | ✅ Active |
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

1. Which default cleanup model should be used in production runs?
2. How strict should cleanup be for filler-word removal?
3. Should we add `.txt` clean output in addition to `transcript_clean.md`?

---

## Next Actions Queue (ranked)

| Rank | Action | Owner | Done When |
|------|--------|-------|----------|
| 1 | Add integration test with mocked yt-dlp subprocess output | AI | Deterministic adapter behavior covered |
| 2 | Add optional backfill limit (`--max-backfill-days`) | Human+AI | Large first run safety control available |
| 3 | Decide and document default LLM model policy | Human | Cleanup defaults locked |

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

- **Working Directory**: `/Users/leeharrington/projects/lunduke-transcripts`
- **Runtime**: Python 3.13 + project `.venv`
- **Key tools**: `yt-dlp`, `pytest`, `ruff`, `black`

---

## Done Checklist
- [x] Mode acknowledged: worked within autonomy boundaries
- [x] Tests pass clean (run profile-specific tests)
- [x] Tested As Lee: ran app as a user, fixed issues found
- [x] Updated: context.md, WHERE_AM_I.md, result-review.md, sprint-plan.md
- [ ] Committed and pushed with descriptive message
