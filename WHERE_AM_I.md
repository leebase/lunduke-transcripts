# WHERE_AM_I — lunduke-transcripts

> Product-level orientation for milestone progress.

---

## Project Health

| Attribute | Value |
|-----------|-------|
| **Project** | lunduke-transcripts |
| **Profile** | Python Package |
| **Current Phase** | Phase 6 — Sprint 11 Pedagogy Implementation |
| **Overall Status** | 🟡 Extraction, reviewed Markdown tutorials, downstream PDF rendering, default publish-to-PDF handoff with an explicit Markdown-only escape hatch, and selective ChatGPT Plus `gpt-5.4` routing are shipped; Test As Lee now completes the full live screencast publish/render path again, but Sprint 11 quality is still open because the tutorial reads too much like a workflow summary instead of a Lee-approvable public tutorial |
| **Last Updated** | 2026-03-07 |

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
| Improve public tutorial quality and hygiene | 🟡 In progress | New tutorial skills, navigation checks, advisory co-editor semantics, a source-interpretation stage, stronger planner/writer/reviewer prompts, setup-first validation, `Codex` copy edits, deterministic outline realignment, and intro/context validation fixes are in; the remaining gap is converting the live screencast from a cautious workflow summary into a more actionable tutorial |
| Make real screencast tutorial reruns finish reliably | 🟡 In progress | Published tutorial runs now auto-render fresh HTML/PDF, routed timeout failures now surface clearly, and the default live screencast flow completes again with a 120-second routed-task budget; the remaining issue is content quality, not stale-artifact/runtime ambiguity |
| Route expensive tutorial stages through ChatGPT Plus `gpt-5.4` | ✅ Done | `lee-llm-router` now handles tutorial writing + technical review while cheap stages stay on cheaper OpenRouter models by default |

---

## Sprint Position

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 10 — Tutorial Quality Refinement | Public tutorial quality + selective strong-model routing + advisory co-editor semantics | ✅ Complete |
| Sprint 11 — Tutorial Pedagogy and Ghostwriting Quality | Stronger teaching voice, better step selection, less project-note feel | ⏳ In Progress |
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
| Live screencast tutorial still reads like a workflow summary rather than a Lee-approvable tutorial | The first actionable section is fixed and the runtime is stable again, but the output still lacks minimally actionable examples and still carries too much caveat-heavy voice | 🟡 Active product-quality constraint |

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
| Tutorial generation uses outline approval and advisory co-editor review | Matches the project's code-review discipline without letting reviewers act as go/no-go deciders | 2026-03-07 |
| Tutorial rendering is a downstream format step | Keeps content generation independent from document formatting and rerendering | 2026-03-06 |
| Tutorial image validation happens before render | Prevents screenshot-heavy PDFs from silently dropping broken image references | 2026-03-06 |
| Chrome-family HTML-to-PDF rendering is the first PDF backend | Browser layout handles screenshot-heavy tutorials better than a direct PDF path | 2026-03-06 |
| Adversarial tutorial review is advisory-only | Red-team pressure should trigger reconsideration, not become an automatic veto | 2026-03-07 |
| Final tutorial Markdown enforces public-artifact hygiene and navigation | Reader-facing tutorials must keep evidence/provenance in sidecars and include basic navigation | 2026-03-07 |
| Strong-model tutorial stages run through `lee-llm-router` | ChatGPT Plus `gpt-5.4` is reserved by default for tutorial writing + technical review while cheap stages remain inexpensive | 2026-03-07 |
| Router paths are resolved relative to the chosen config file | Running the CLI from another working directory must not break router configs or traces | 2026-03-07 |
| Fresh final artifacts are written even when editorial warnings remain | Human review should see the newest Markdown/PDF rather than stale successful artifacts | 2026-03-07 |
| Public tutorial drafts receive deterministic copy-edits for known tool-name confusions | Reader-facing artifacts should not leak obvious transcript homophone mistakes like `codecs` when `Codex` is clearly intended | 2026-03-07 |
| Published tutorial runs auto-trigger downstream render refresh by default, with `--skip-render` for Markdown-only publishes | A fresh approved tutorial should refresh HTML/PDF artifacts in the same user flow instead of leaving stale finals on disk, without making the renderer mandatory for every publish workflow | 2026-03-07 |
| Sprint 11 quality rules should become validator-visible when practical | Prompt-only coaching is not enough to keep setup-first lesson structure and repetitive low-signal warning noise under control | 2026-03-07 |
| Tutorial planning should consume an explicit source-interpretation artifact | The live screencast needed a separate core-workflow summary before planning, not just stronger planner instructions | 2026-03-07 |

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

1. improve tutorial voice and ghostwriting quality so the output becomes a public tutorial instead of a caveat-heavy walkthrough
2. add minimally actionable prompt/artifact examples without inventing unsupported commands
3. improve screenshot usefulness or justify more text-only steps
4. keep pushing transcript-processing execution earlier in the lesson
5. add the next renderer target after PDF
