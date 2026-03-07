# WHERE_AM_I — lunduke-transcripts

> Product-level orientation for milestone progress.

---

## Project Health

| Attribute | Value |
|-----------|-------|
| **Project** | lunduke-transcripts |
| **Profile** | Python Package |
| **Current Phase** | Phase 5 — Tutorial Rendering Delivered |
| **Overall Status** | 🟢 Extraction, reviewed Markdown tutorials, and downstream PDF rendering shipped |
| **Last Updated** | 2026-03-06 |

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
| Define transcript + frame asset architecture | ✅ Done | `product-definition.md`, `design.md` updated on 2026-03-06 |
| Plan next implementation sprint | ✅ Done | Sprint 7 added for transcript JSON + frame manifests |
| Ship source-agnostic tutorial asset extraction | ✅ Done | Local file ingest, frame extraction, degraded bundle handling, and bundle artifacts implemented |
| Ship downstream multi-agent written tutorial generation | ✅ Done | `tutorial` CLI, approval gate, validation, review, revision, and final Markdown output are implemented |
| Ship downstream tutorial rendering | ✅ Done | `render` CLI, image validation, HTML staging, PDF output, and render manifests are implemented |

---

## Sprint Position

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 9 — Tutorial PDF Rendering | Downstream HTML/PDF renderer with image validation | ✅ Complete |
| Sprint 8 — Multi-Agent Tutorial Generation | Approval-gated tutorial drafting, validation, and review | ✅ Complete |
| Sprint 7 — Tutorial Asset Extraction Foundation | Transcript JSON + frame manifest + bundle | ✅ Complete with remediation |
| Sprint 6 — ASR Plugin Architecture | Caption fallback via pluggable ASR | ✅ Complete |
| Sprint 1 — Foundation | Exact transcript pipeline | ✅ Complete |
| Sprint 2 — LLM Cleanup | Cleanup generation + caching | ✅ Complete |
| Sprint 3 — Scheduling and Hardening | Scheduler assets + retries + reports | ✅ Complete |
| Sprint 4 — Reliability Hardening | Python contract, timeouts, CI, docs portability | ✅ Complete |

---

## Product Risks & Blockers

| Risk/Blocker | Impact | Status |
|-------------|--------|--------|
| Upstream YouTube format changes | Discovery/fetch instability | 🟡 Managed with timeout/retry controls |
| Frame extraction thresholds may be noisy | Too many or weak screenshots | 🟡 Next tuning target |
| Candidate frames are not yet semantically ranked | Renderers may get too many screenshots | 🟡 Deferred to next phase |
| Missing captions for some videos | Partial transcript coverage | 🟢 Handled with ASR fallback path |

---

## Key Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| Keep Python stack | Best speed/maintainability for text + orchestration | 2026-03-04 |
| Runtime contract set to Python 3.11+ | Matches implementation and avoids 3.10 UTC mismatch | 2026-03-04 |
| Use `yt-dlp` adapter boundary | Simplifies resilience to YouTube changes | 2026-03-04 |
| Use SQLite for durable state | Reliable idempotency and run history | 2026-03-04 |
| Keep exact transcript canonical | Preserves source-fidelity for auditability | 2026-03-04 |
| Store frame images on disk and reference them from JSON | Keeps manifests small and downstream-friendly | 2026-03-06 |
| Use scene detection for frame candidates before semantic selection | Deterministic extraction now, smarter selection later | 2026-03-06 |
| Local file fingerprints use content hashes | Stable across rename, move, and touch operations | 2026-03-06 |
| Missing explicit local file inputs fail the run | Invalid user inputs must not present as clean success | 2026-03-06 |
| Bundle manifest persists even when frame capture fails | Downstream tools should read one canonical manifest and inspect explicit frame status | 2026-03-06 |
| Frame directories are replaced only after successful extraction | Prevents reruns from deleting last known-good screenshots | 2026-03-06 |
| Tutorial behavior is defined by repo-local agent and skill files | Keeps editorial iteration versioned and decoupled from orchestration code | 2026-03-06 |
| Tutorial publishing requires outline approval and review gates | Matches the project's code-review discipline before a tutorial becomes publish-eligible | 2026-03-06 |
| Tutorial rendering is a downstream format step | Keeps content generation independent from document formatting and rerendering | 2026-03-06 |
| Tutorial image validation happens before render | Prevents screenshot-heavy PDFs from silently dropping broken image references | 2026-03-06 |
| Chrome-family HTML-to-PDF rendering is the first PDF backend | Browser layout handles screenshot-heavy tutorials better than a direct PDF path | 2026-03-06 |

---

## What "Done" Looks Like

- [x] MVP criteria met
- [x] User can run manually or on schedule
- [x] New-video detection and date-range filtering work
- [x] Exact + cleaned transcript outputs available
- [x] Canonical transcript/frame bundle available for downstream generators

---

## Next Milestone

Phase 6 tutorial quality and format expansion:

1. improve frame selection quality
2. improve tutorial voice and ghostwriting quality
3. add the next renderer target after PDF
