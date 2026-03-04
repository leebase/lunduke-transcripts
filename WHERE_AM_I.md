# WHERE_AM_I — lunduke-transcripts

> Product-level orientation for milestone progress.

---

## Project Health

| Attribute | Value |
|-----------|-------|
| **Project** | lunduke-transcripts |
| **Profile** | Python Package |
| **Current Phase** | Phase 2 — Reliability Hardening Complete |
| **Overall Status** | 🟢 MVP + hardening baseline |
| **Last Updated** | 2026-03-04 |

---

## Progress Against Product Goals

> Reference: `product-definition.md`

### MVP Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| Run on demand | ✅ Done | `lunduke-transcripts run --config ...` |
| Run with schedule compatibility | ✅ Done | cron/launchd scripts/docs added |
| Detect/process only new videos | ✅ Done | SQLite idempotency + `--reprocess` override |
| Exact transcript artifacts with timestamps | ✅ Done | `.vtt` + `.md` + `.txt` outputs |
| Cleaned transcript pass | ✅ Done | LLM adapter + cache + provenance fields |
| Metadata capture (publish/capture times etc.) | ✅ Done | `metadata.json` per video |
| Date-range execution option | ✅ Done | `--from` / `--to` inclusive filtering |

### Current Phase Goals

| Goal | Status | Notes |
|------|--------|-------|
| Define product and design docs | ✅ Done | `product-definition.md`, `design.md` |
| Build first working feature | ✅ Done | Complete transcript pipeline shipped |
| Validate in real run | ✅ Done | Live channel run + idempotency rerun |

---

## Sprint Position

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 — Foundation | Exact transcript pipeline | ✅ Complete |
| Sprint 2 — LLM Cleanup | Cleanup generation + caching | ✅ Complete |
| Sprint 3 — Scheduling and Hardening | Scheduler assets + retries + reports | ✅ Complete |
| Sprint 4 — Reliability Hardening | Python contract, timeouts, CI, docs portability | ✅ Complete |

---

## Product Risks & Blockers

| Risk/Blocker | Impact | Status |
|-------------|--------|--------|
| Upstream YouTube format changes | Discovery/fetch instability | 🟡 Managed with timeout/retry controls |
| LLM cleanup may vary by model/provider | Output consistency | 🟡 Needs policy lock |
| Missing captions for some videos | Partial transcript coverage | 🟢 Handled (explicit unavailable state) |

---

## Key Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| Keep Python stack | Best speed/maintainability for text + orchestration | 2026-03-04 |
| Runtime contract set to Python 3.11+ | Matches implementation and avoids 3.10 UTC mismatch | 2026-03-04 |
| Use `yt-dlp` adapter boundary | Simplifies resilience to YouTube changes | 2026-03-04 |
| Use SQLite for durable state | Reliable idempotency and run history | 2026-03-04 |
| Keep exact transcript canonical | Preserves source-fidelity for auditability | 2026-03-04 |

---

## What "Done" Looks Like

- [x] MVP criteria met
- [x] User can run manually or on schedule
- [x] New-video detection and date-range filtering work
- [x] Exact + cleaned transcript outputs available
- [x] Core documentation complete

---

## Next Milestone

Phase 3 refinement:

1. finalize provider fallback model policy
2. improve first-run backfill ergonomics
3. add security audit automation in CI
