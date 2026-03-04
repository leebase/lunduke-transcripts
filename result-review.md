# lunduke-transcripts Result Review

> **Running log of completed work.** Newest entries at the top.
>
> Each entry documents what was built, why it matters, and how to verify it works.

---

## 2026-03-04 — Sprint 4 Reliability Hardening Completed

Completed a focused hardening sprint based on external review findings.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Python contract | Runtime support aligned to Python 3.11+ in `pyproject.toml` |
| yt-dlp safety | Added subprocess timeout + retry handling with explicit timeout error tags |
| LLM safety | Added request timeout + bounded retries + structured timeout/failure messages |
| Test reproducibility | Added pytest path config (`pythonpath = ["src"]`) |
| CI gates | Added GitHub Actions workflow for ruff, black --check, and pytest |
| Docs portability | Replaced absolute local file links with relative links in project docs |
| Regression coverage | Added tests for yt-dlp timeout behavior, LLM retry/timeout behavior, and project contract |

### Why It Matters

- Reduces scheduler stall risk from hanging external calls.
- Makes runtime support expectations explicit and enforceable.
- Improves contributor and CI reproducibility.
- Strengthens maintainability by preventing portability/documentation regressions.

### How to Verify

1. `source .venv/bin/activate`
2. `ruff check src tests`
3. `black --check src tests`
4. `pytest -q`
5. Inspect CI workflow at `.github/workflows/ci.yml`

---

## 2026-03-04 — MVP Pipeline Delivered (Sprints 1-3)

Implemented and validated the full transcript workflow from product/design docs.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Core package | Normalized package path to `src/lunduke_transcripts/` and rebuilt CLI app |
| Run modes | `run` command with `--config`, `--from`, `--to`, `--reprocess` |
| Discovery/fetch | `yt-dlp` adapter for channel discovery, metadata fetch, transcript acquisition |
| State | SQLite tables: `videos`, `transcripts`, `runs`, `run_items` |
| Artifacts | `metadata.json`, `transcript_exact.vtt`, `transcript_exact.md`, `transcript_exact.txt`, optional `transcript_clean.md` |
| Cleanup pass | OpenAI adapter + deterministic cleanup prompt + hash-based cache |
| Scheduling | `scripts/run_pipeline.sh` + `scripts/com.lunduke.transcripts.plist.example` + README scheduler docs |
| Tests | Unit/integration tests for VTT parsing, date-range filtering, idempotency/reprocess behavior |

### Why It Matters

- Ships an end-to-end MVP that can run now or on schedule.
- Preserves exact transcript fidelity while enabling optional cleaned output.
- Adds durable state and run reporting so reruns are safe and auditable.

### How to Verify

1. Activate environment and run checks:
   - `source .venv/bin/activate`
   - `ruff check src tests`
   - `pytest -q`
2. Run the app:
   - `python -m lunduke_transcripts.main run --config config/channels.toml`
3. Verify outputs:
   - `data/db/lunduke_transcripts.sqlite3`
   - `data/runs/<run_id>.json`
   - `data/videos/<video_id>/metadata.json`
   - transcript files under each video directory
4. Verify idempotency:
   - run same command twice
   - second run should report `videos_new = 0` unless `--reprocess` is used

### Test As Lee Results

- Live run against `https://www.youtube.com/@Lunduke/videos` succeeded.
- Rerun confirmed idempotency (`videos_new = 0`).
- `--reprocess` rerun successfully processed the same range again.

---

## 2026-02-17 — Project Scaffolded

**Project initialized** with init-agent.

### Created

| File | Purpose |
|------|---------|
| `AGENTS.md` | AI agent guide and conventions |
| `WHERE_AM_I.md` | Quick orientation for agents |
| `feedback.md` | Human feedback capture |
| `README.md` | Project documentation |
| `context.md` | Session working memory |
| `result-review.md` | This file - running log |
| `sprint-plan.md` | Sprint tracking |

### How to Verify

1. Check all files exist: `ls *.md`
2. Read AGENTS.md to understand project conventions
3. Check context.md for current state

---

*Add new entries above this line. Keep the newest work at the top.*
