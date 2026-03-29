# lunduke-transcripts Result Review

> **Running log of completed work.** Newest entries at the top.
>
> Each entry documents what was built, why it matters, and how to verify it works.

---

## 2026-03-29 — Sprint 11 Downstream Vendored Router Migration Follow-Up

Implemented the follow-up to close out remaining `lee-llm-router` migration friction.
`[llm].router_repo_path` is now optional in the runtime config parser, empty
path values are normalized to `None`, and the sample router configs no longer
hard-code a developer-specific absolute path. The repo now includes a vendored
`src/lee_llm_router/` snapshot from this project for stable local use with
`router_repo_path` unset.

### Built

- Removed hard-coded `/Users/.../lee-llm-router` defaults from `config/channels.toml` and
  `config/channels.toml.example` and documented the vendored-snapshot recommendation
- Updated `src/lunduke_transcripts/config.py` to coalesce optional router paths
  from env and TOML into either a real path or `None`
- Added regression coverage for empty-string router paths in
  `tests/test_config_env.py`
- Exported and committed a vendored `src/lee_llm_router/` snapshot for this repo
- Updated `README.md` to call out when `router_repo_path` should remain unset

### Why It Matters

Downstream users can now run with an in-repo router snapshot instead of
environment-specific absolute path assumptions, reducing setup fragility while
preserving router migration momentum.

### How to Verify

1. Run focused checks with a temp `openai` stub:
   - `tmpdir=$(mktemp -d) && echo 'class APITimeoutError(Exception): pass\\nclass OpenAI: ...' > \"$tmpdir/openai.py"`
   - `PYTHONPATH=\"$tmpdir:src\" python3 -m pytest tests/test_config_env.py tests/test_main_cli.py -q`
2. Confirm template configs and docs omit host-specific `router_repo_path` and that README documents vendored mode
3. Confirm `src/lee_llm_router/.lee_llm_router_export.json` exists and reflects the latest export source

## 2026-03-07 — Sprint 11 Editorial Cleanup and Post-Draft Screenshot Refit

Implemented the next concrete Sprint 11 quality pass by removing unsupported
public prompt-template inserts, softening unsupported assumptions in the
tutorial contract, and refitting screenshot choices after the draft exists so
the final visuals better match the rewritten tutorial steps.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Editorial pass | Replaced the old post-writer copy-edit hook with a fuller editorial pass that removes scaffolding sections, strengthens the intro framing, softens repeated source-limit caveats, and strips image blocks from text-only steps |
| Contract normalization | Softened definition and outline assumptions that were drifting into unsupported claims such as step-by-step copy-paste expectations, hard Mac-only requirements, ChatGPT Plus requirements, or assumed architecture fluency |
| Action/outline matching | Taught outline validation and reference matching to ignore pure orientation steps when checking the first actionable move, and made the matcher more tolerant of co-thinker paraphrase variants |
| Screenshot relevance | Added a deterministic post-draft visual-fit pass that re-evaluates `frame_selection_plan.json` against the written tutorial, remaps reused screenshots to more specific later frames when possible, and rewrites the draft image blocks to match the updated plan |
| Regression coverage | Added tests for definition normalization, outline-assumption softening, earlier weak-frame downgrade, action-title matching variants, post-draft frame refit, draft image-block rewriting, and intro-only step handling |
| Live validation | Re-ran the real `AgentFlowComplete_compressed.mp4` tutorial flow and confirmed fresh Markdown/PDF finals plus materially better frame-to-step alignment without creating new visuals |

### Why It Matters

- The public draft is less likely to overclaim unsupported setup details or
  invent reusable prompt templates that the screencast never actually teaches.
- Screenshot selection is now based on the rewritten tutorial step intent, not
  only the nearest transcript-aligned frame candidate, which directly addresses
  the biggest Lee complaint about visual relevance.
- The remaining Sprint 11 gap is narrower and clearer: writing quality,
  sequencing, and tutorial voice are now the main blockers instead of runtime
  reliability or stale visual evidence.

### How to Verify

1. Run targeted checks:
   - `./.venv/bin/pytest -q tests/test_tutorial_pipeline.py`
   - `./.venv/bin/ruff check src/lunduke_transcripts/app/tutorial_pipeline.py src/lunduke_transcripts/transforms/tutorial_prompts.py tests/test_tutorial_pipeline.py`
   - `./.venv/bin/black --check src/lunduke_transcripts/app/tutorial_pipeline.py src/lunduke_transcripts/transforms/tutorial_prompts.py tests/test_tutorial_pipeline.py`
2. Re-run the real tutorial flow:
   - `PYTHONPATH=src ./.venv/bin/python -m lunduke_transcripts.main tutorial --bundle data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial_asset_bundle.json --approve-outline --reprocess --config config/channels.toml --env-file .env`
3. Inspect the refreshed visual plan and final artifacts:
   - `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/frame_selection_plan.json`
   - `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_final.md`
   - `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_final.pdf`
4. Confirm the current live result:
   - the publish/render path completes and refreshes fresh finals
   - screenshot reuse is reduced and later steps get more specific existing
     frames when possible
   - the tutorial is still not fully Lee-approved because the prose remains too
     workflow-summary-like in places

---

## 2026-03-07 — Sprint 11 Prompt and Validator Pedagogy Pass

Implemented the first concrete Sprint 11 pass by tightening planner/writer/reviewer
guidance around learner-first sequencing, adding validator heuristics for
incidental setup-first outlines, and reducing duplicated low-signal warning
noise in tutorial reruns.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Planner prompts | Strengthened the planner instructions so the first actionable section should start with the core workflow and demote scaffolding such as remote access, recording context, and setup chores |
| Writer/reviewer prompts | Tightened writer, technical reviewer, and adversarial reviewer prompts around payoff, public-tutorial voice, and calling out setup-first lesson structure |
| Validator heuristics | Added an outline-level `incidental_setup_priority` finding when the first actionable step foregrounds setup while later steps contain the actual workflow |
| Warning quality | Reduced low-signal warning churn by making step-title representation checks accept slug/keyword matches and deduplicating repeated failure/advisory messages |
| Outline copy edits | Normalized obvious `Codex`/`codecs` confusion inside normalized lesson outlines so planner output no longer feeds known homophone mistakes downstream in tests |
| Regression coverage | Added tests for incidental-setup detection, outline terminology normalization, more forgiving step-title representation, and failure-message deduplication |

### Why It Matters

- Moves Sprint 11 beyond prompt aspirations by making pedagogy problems visible
  in machine-readable validation output.
- Cuts repeated structural noise so remaining warning sets better reflect real
  teaching and sequencing problems.
- Improves upstream planner artifacts, not just the final Markdown, which gives
  the writer a cleaner lesson structure to work from.

### How to Verify

1. Run targeted checks:
   - `./.venv/bin/pytest -q tests/test_tutorial_pipeline.py`
   - `./.venv/bin/ruff check src/lunduke_transcripts/app/tutorial_pipeline.py src/lunduke_transcripts/transforms/tutorial_prompts.py tests/test_tutorial_pipeline.py`
   - `./.venv/bin/black --check src/lunduke_transcripts/app/tutorial_pipeline.py src/lunduke_transcripts/transforms/tutorial_prompts.py tests/test_tutorial_pipeline.py`
2. Confirm the new validator behavior in tests:
   - incidental setup first is reported as `incidental_setup_priority`
   - outline JSON normalizes obvious `codecs` references to `Codex`
   - repeated identical review messages collapse to one failure message
3. Run the live screencast tutorial flow:
   - `./.venv/bin/python -m lunduke_transcripts.main tutorial --bundle data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial_asset_bundle.json --approve-outline --reprocess --max-review-cycles 0 --config config/channels.toml --env-file .env`
4. Note the current live result:
   - the router-backed screencast run still lingered and had to be killed manually after refreshing only part of the artifact set, so Sprint 11 content work is progressing but the live-run reliability issue remains open

### Follow-on Validation

- Added a new `source-interpreter` tutorial stage plus `source_interpretation.json`
  so planning gets an explicit "what is this video really teaching?" artifact.
- Updated router config so the new stage resolves to an explicit
  `tutorial_interpreter` role during live runs.
- Re-ran the real `AgentFlowComplete_compressed.mp4` flow and confirmed:
  - `source_interpretation.json` refreshed successfully
  - `lesson_outline.json` refreshed again through the planner
  - planner output no longer leaked `codecs` terminology
  - the outline still begins with project-folder/setup work rather than the
    core transcript-processing workflow
  - the CLI process still lingered and needed to be killed manually
- Tightened the source-interpretation contract again so setup-first
  `best_first_action` values are normalized toward the first substantive
  emphasized action, and outline normalization now deterministically realigns
  the first actionable step to the interpreted first action when the planner
  still leaves setup first.
- Re-ran the live screencast flow through the workspace codepath
  (`PYTHONPATH=src`) and confirmed the refreshed outline now starts with
  `Engage AI as a Co-Thinker to Define Project Goals` instead of project-folder
  creation.
- The router-backed CLI process still lingered after artifact refresh and had
  to be killed manually, so the pedagogy fix is improved but the runtime
  reliability bug remains open.
- Added a CLI-side stale-artifact cleanup for `tutorial --reprocess` so old
  `tutorial_manifest.json`, `tutorial_final.md`, `tutorial_final.html`,
  `tutorial_final.pdf`, and `render_manifest.json` are removed before a fresh
  rerun begins.
- Added regression coverage proving a reprocess tutorial run clears stale final
  tutorial/render outputs before invoking the pipeline, preventing an
  interrupted rerun from looking like a fresh publish with an older PDF.
- Test As Lee then pushed the live reliability path further:
  - added a wall-clock timeout wrapper around routed tutorial tasks in
    `src/lunduke_transcripts/infra/llm_adapter.py`
  - taught the adapter to surface wrapped `lee-llm-router` timeouts as
    `llm_router_timeout[...]` instead of an empty
    `llm_router_request_failed[...]` message
  - widened the default routed tutorial timeout budget in
    `config/channels.toml` and both router YAMLs from 60s to 120s so the real
    `tutorial.evidence` stage has enough headroom to finish consistently
  - added regression coverage for wrapped router timeout detection and blank
    router-error cause reporting
- Tightened planner/writer skills and prompt contracts again so:
  - generic `why this matters` / `by the end` copy should stay compact instead
    of becoming standalone outline steps unless the source clearly teaches it
  - speculative extension / future-work steps should not be planned unless the
    transcript actually demonstrates them
  - public drafts should not add top-level scaffolding sections like
    `Text-Only and Visual Notes`
- Hardened outline normalization and validation so:
  - the interpreted `best_first_action` can move ahead of leading text-only
    setup inside the first actionable section
  - intro/context-only opening copy no longer triggers a false
    `outline_misaligned_with_interpretation` finding
- Re-ran the full default Lee path on the real screencast multiple times using
  `PYTHONPATH=src ./.venv/bin/python -m lunduke_transcripts.main tutorial ...`
  and confirmed:
  - the end-to-end CLI now exits cleanly instead of lingering
  - fresh `tutorial_final.md`, `tutorial_final.html`, `tutorial_final.pdf`, and
    `render_manifest.json` are regenerated together
  - the first actionable section now starts with AI planning instead of folder
    setup
  - the tutorial is still **not** Lee-approved: it remains too summary-like,
    too disclaimer-heavy, and still lacks minimally actionable prompt/artifact
    examples for core workflow steps

---

## 2026-03-07 — Published Tutorial Runs Now Refresh Final PDF Artifacts

Fixed the stale-final-artifact gap by making the `tutorial` CLI invoke the
downstream renderer automatically after a successful publish, instead of
stopping at fresh Markdown and leaving an older PDF on disk.

### Built

| Area | What Was Delivered |
|------|--------------------|
| CLI publish flow | `lunduke-transcripts tutorial --approve-outline` now calls the downstream PDF renderer by default whenever the tutorial run finishes with `status = "published"` |
| Markdown-only escape hatch | Added `--skip-render` so a user can still publish only `tutorial_final.md` without depending on Pandoc/Chrome |
| Failure visibility | The tutorial CLI JSON output now distinguishes `status`, `tutorial_status`, and `render_status`, and reports `status = "partial"` with a non-zero exit code if the downstream render fails after publish |
| Regression coverage | Added CLI tests covering published-tutorial auto-render success, `--skip-render`, and published-tutorial render failure handling |
| Live validation | Re-ran the real `render` CLI for `AgentFlowComplete_compressed.mp4` and refreshed `tutorial_final.html`, `tutorial_final.pdf`, and `render_manifest.json` with March 7, 2026 timestamps |

### Why It Matters

- Prevents a fresh `tutorial_final.md` from masquerading as a fully refreshed
  final artifact when the PDF on disk is still from an older run.
- Keeps rendering downstream and independently rerunnable while preserving a
  clean Markdown-only path for users who explicitly do not want to render.

### How to Verify

1. Run targeted checks:
   - `./.venv/bin/pytest -q tests/test_main_cli.py tests/test_tutorial_render_pipeline.py`
   - `./.venv/bin/ruff check src/lunduke_transcripts/main.py tests/test_main_cli.py`
   - `./.venv/bin/black --check src/lunduke_transcripts/main.py tests/test_main_cli.py`
2. Verify the Markdown-only publish path remains available:
   - `./.venv/bin/python -m lunduke_transcripts.main tutorial --bundle data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial_asset_bundle.json --approve-outline --skip-render --config config/channels.toml --env-file .env`
3. Verify the real renderer path refreshes the screencast final artifacts:
   - `./.venv/bin/python -m lunduke_transcripts.main render --manifest data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_manifest.json --target pdf --config config/channels.toml --env-file .env`
4. Confirm fresh timestamps on:
   - `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_final.html`
   - `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_final.pdf`
   - `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/render_manifest.json`
5. Note the remaining separate gap:
   - some live router-backed `tutorial` CLI runs can still linger after artifact refresh, so the PDF handoff fix does not by itself close the lingering-process bug

---

## 2026-03-07 — Codex Terminology Guard Added to Public Tutorial Output

Added a narrow public-facing copy-edit and validation backstop so tutorial
drafts stop leaking the `Codex`/`codecs` transcript homophone into reader-facing
Markdown.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Public copy edit | Added a deterministic post-writer pass that normalizes obvious `Codex`/`codecs` confusion before tutorial validation runs |
| Prompt guidance | Tightened writer/reviewer prompt guidance and the tutorial-writing skill so obvious tool-name homophone mistakes are corrected rather than preserved |
| Regression coverage | Added a pipeline regression proving that public tutorial Markdown no longer ships `GPT 5.3 codecs`-style wording |
| Live validation | Re-ran the real `AgentFlowComplete_compressed.mp4` tutorial flow and confirmed the fresh draft now uses `Codex` consistently with no terminology findings in `tutorial_validation_report.json` |

### Why It Matters

- Fixes a visible public-artifact quality bug that would undermine trust in the
  tutorial output.
- Treats the terminology issue like copy editing, not a blocking review veto,
  which fits the current co-editor model better.

### How to Verify

1. Run targeted checks:
   - `./.venv/bin/pytest -q tests/test_tutorial_pipeline.py`
   - `./.venv/bin/ruff check src/lunduke_transcripts/app/tutorial_pipeline.py src/lunduke_transcripts/transforms/tutorial_prompts.py tests/test_tutorial_pipeline.py`
   - `./.venv/bin/black --check src/lunduke_transcripts/app/tutorial_pipeline.py src/lunduke_transcripts/transforms/tutorial_prompts.py tests/test_tutorial_pipeline.py`
2. Regenerate the screencast tutorial draft:
   - `./.venv/bin/python -m lunduke_transcripts.main tutorial --bundle data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial_asset_bundle.json --approve-outline --reprocess --max-review-cycles 0 --config config/channels.toml --env-file .env`
3. Inspect the fresh draft:
   - `rg -n '\\bCodecs\\b|\\bcodecs\\b|\\bCodex\\b' data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_draft.md`
4. Confirm the validation report no longer includes a terminology finding:
   - inspect `data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_validation_report.json`

## 2026-03-07 — Advisory Co-Editor Tutorial Flow Closed Out

Closed Sprint 10 by converting tutorial validation/review into advisory
co-editors, republishing the real screencast tutorial, and hardening the
router-backed live path that Test As Lee exposed.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Tutorial semantics | Removed tutorial-quality `blocked` outcomes; validation, technical review, and adversarial review now always run and record warnings instead of vetoing fresh final artifacts |
| Pipeline control flow | Fixed reroute handling so `script-writer` and `visual-editor` reroutes continue cleanly instead of risking a fall-through return |
| CLI/user contract | Tutorial runs now exit successfully for editorial-warning outcomes and always write a fresh `tutorial_final.md` after outline approval |
| Manifesting | `tutorial_manifest.json` now records editorial attention/warning counts instead of hard-block semantics |
| Router reliability | Added repo-root fallback for `config/...` router assets, added a wall-clock timeout guard in `lee-llm-router`, and narrowed the default ChatGPT Plus routing to writer + technical reviewer |
| Live artifacts | Re-ran `AgentFlowComplete_compressed.mp4` and refreshed `tutorial_final.md`, `tutorial_final.html`, `tutorial_final.pdf`, and `render_manifest.json` |

### Why It Matters

- Matches the product direction: tutorial stages are now co-editors, not
  go/no-go deciders.
- Prevents the stale-artifact confusion where a new run could finish without
  producing a fresh public tutorial file.
- Keeps the stronger model on the highest-value editorial work while improving
  reliability of the real screencast workflow.

### How to Verify

1. Run checks:
   - `./.venv/bin/pytest -q`
   - `./.venv/bin/ruff check src tests`
   - `./.venv/bin/black --check src tests`
   - `./.venv/bin/pytest -q tests/test_providers.py` in `~/projects/lee-llm-router`
2. Regenerate the real screencast tutorial:
   - `./.venv/bin/python -m lunduke_transcripts.main tutorial --bundle data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial_asset_bundle.json --approve-outline --reprocess --max-review-cycles 0 --config config/channels.toml --env-file .env`
3. Render the refreshed final tutorial:
   - `./.venv/bin/python -m lunduke_transcripts.main render --manifest data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial/tutorial_manifest.json --target pdf --config config/channels.toml --env-file .env`
4. Verify fresh timestamps on:
   - `tutorial_final.md`
   - `tutorial_final.pdf`
   - `tutorial_manifest.json`
   - `render_manifest.json`
5. Inspect `tutorial_manifest.json` and confirm:
   - `status = "published"`
   - `publish_eligible = true`
   - `review_outcomes.editorial_attention_required = true`
   - blocked flags are all `false`

## 2026-03-07 — Selective ChatGPT Plus GPT-5.4 Tutorial Routing

Integrated `lee-llm-router` into the tutorial pipeline so the expensive
editorial stages can use ChatGPT Plus `gpt-5.4` while the cheaper planning and
evidence stages remain on cheaper OpenRouter roles.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Router integration | Added optional router config/env support and task-to-role routing in the lunduke LLM adapter and CLI wiring |
| Provider fixes | Fixed the `lee-llm-router` ChatGPT subscription provider to send `instructions`, use SSE streaming, stop cleanly on completion, and avoid unsupported `temperature` |
| Path handling | Resolved router repo/config/trace paths relative to the selected config file instead of the current working directory |
| Validation | Added provider tests for streamed SSE responses plus CLI regression coverage for config-relative router paths |
| Live verification | Re-ran `AgentFlowComplete_compressed.mp4` through the real tutorial flow and confirmed it now exits `blocked` cleanly instead of hanging in the review loop |

### Why It Matters

- Uses a stronger model where it matters most without paying for it in the easy
  transcript/planning stages.
- Removes the runtime failure mode that previously left the real screencast
  tutorial flow hanging after draft/review generation.
- Makes router-backed configs more portable because they no longer depend on
  launching the CLI from the repo root.

### How to Verify

1. Run targeted checks:
   - `./.venv/bin/pytest -q tests/test_main_cli.py tests/test_llm_adapter.py tests/test_config_env.py`
   - `./.venv/bin/ruff check src/lunduke_transcripts/main.py tests/test_main_cli.py`
   - `./.venv/bin/black --check src/lunduke_transcripts/main.py tests/test_main_cli.py`
   - `./.venv/bin/pytest -q tests/test_providers.py` in `~/projects/lee-llm-router`
2. Confirm router config points expensive roles at ChatGPT Plus `gpt-5.4` in [config/tutorial-llm-router.yaml](config/tutorial-llm-router.yaml).
3. Run the real screencast tutorial flow:
   - `.venv/bin/python -m lunduke_transcripts.main tutorial --bundle data/videos/undated_agentflowcomplete-compressed__local-07a44a6c708888f9/tutorial_asset_bundle.json --approve-outline --reprocess --max-review-cycles 1 --config config/channels.toml --env-file .env`
4. Verify the result is a clean `blocked` JSON payload rather than a hang.
5. Inspect the fresh traces under `.agentleeops/traces/20260307/` and confirm:
   - `tutorial_writer` used `gpt-5.4`
   - `tutorial_reviewer` used `gpt-5.4`
   - `tutorial_redteam` used `gpt-5.4`
6. Note the current product-quality outcome: the screencast still fails review, so the latest fresh artifact is `tutorial_draft.md`, not a republished `tutorial_final.pdf`.

## 2026-03-07 — Tutorial Quality Refinement and Review Hardening

Implemented a tutorial-quality refinement pass focused on making the published
Markdown behave like a real public tutorial rather than a transcript-shaped
artifact.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Tutorial skills | Added `tutorial-narrative`, `public-artifact-hygiene`, `tutorial-navigation`, `tutorial-step-selection`, and `tutorial-quality-review` |
| Agent updates | Updated planner, writer, technical reviewer, and adversarial reviewer role files to use the new tutorial-specific skills |
| Public artifact rules | Writer prompts and validation now require context, a table of contents, per-section back-to-top links, and no leaked `Evidence:` callouts in final Markdown |
| Review semantics | Changed adversarial review to advisory-only while keeping it mandatory before publish |
| Review remediation | Ran a formal code review, found validator contract/navigation gaps, and fixed both with regression coverage |
| Validation | Added tests for evidence leakage, definition-controlled structure requirements, and per-section navigation enforcement |

### Why It Matters

- Moves the system closer to producing something publishable as the speaker's
  tutorial instead of a cleaned-up transcript.
- Separates public tutorial prose from internal grounding artifacts more
  cleanly.
- Makes the tutorial contract more honest by enforcing the same navigation and
  hygiene rules the prompts now ask for.

### How to Verify

1. Run checks:
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
   - `.venv/bin/pytest -q`
2. Regenerate a tutorial bundle through the `tutorial` CLI with `--approve-outline --reprocess`.
3. Inspect `tutorial_draft.md` and confirm:
   - it starts with context
   - it has a table of contents
   - each major section includes `[Back to top](#top)`
   - it does not contain `Evidence:`
4. Review `code-reviews/review-2026-03-06.md` for the formal review artifact.
5. Note the current gap: on the real `AgentFlowComplete_compressed.mp4` screencast, the live rerun stalled after `tutorial_draft.md` and `tutorial_validation_report.json`, so the end-to-end LLM review stage still needs reliability work.

## 2026-03-06 — Downstream PDF Renderer Delivered

Implemented a downstream renderer that converts a published tutorial manifest
into HTML and PDF while validating screenshot references before render.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Render CLI | Added `lunduke-transcripts render --manifest ... --target pdf` |
| Render pipeline | Added a separate renderer that reads `tutorial_manifest.json`, validates Markdown image references, renders `tutorial_final.html` with Pandoc, and prints `tutorial_final.pdf` with a Chrome-family browser engine |
| Render artifacts | Added `render_manifest.json` with toolchain, output paths, and image validation status |
| Image safety | Added pre-render image validation and stale-output cleanup so failed renders do not pretend to have fresh HTML/PDF |
| Validation | Added tests for HTML/PDF creation, missing-image failures, repeatable renders, and render CLI behavior |

### Why It Matters

- Turns the reviewed Markdown tutorial into a format a reader can actually consume without leaving the project folder.
- Keeps rendering separate from LLM generation so document styling iterations are cheap and deterministic.
- Makes screenshot preservation a hard contract instead of a best-effort side effect.

### How to Verify

1. Install renderer tools:
   - `brew install pandoc chromium`
2. Generate or reuse a published tutorial directory containing `tutorial_manifest.json`.
3. Render the tutorial:
   - `.venv/bin/python -m lunduke_transcripts.main render --manifest /path/to/tutorial/tutorial_manifest.json --target pdf`
4. Verify outputs:
   - `tutorial_final.html`
   - `tutorial_final.pdf`
   - `render_manifest.json`
5. Confirm screenshots are visible in HTML/PDF and that missing images cause a clean failure before render.

## 2026-03-06 — Sprint 8 Multi-Agent Tutorial Generation Delivered

Implemented a downstream tutorial pipeline that consumes `tutorial_asset_bundle.json`
and produces reviewed written tutorials using repo-local agent and skill files.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Tutorial CLI | Added `lunduke-transcripts tutorial --bundle ...` with outline approval, cache reuse, and review-cycle controls |
| Agent system | Added repo-local `agents/` role files and tutorial-specific `skills/` loaded at runtime |
| Tutorial artifacts | Added `tutorial_definition.json`, `lesson_outline.json`, `evidence_map.json`, `frame_selection_plan.json`, review artifacts, `tutorial_manifest.json`, and `tutorial_final.md` |
| Review loop | Added validator, technical review, adversarial review, and review-response rerouting before publish |
| Caching/provenance | Added manifest-based cache reuse keyed by bundle contents plus agent/skill digests |
| Validation | Added tests for approval gating, adversarial blocking, writer-only reroute recovery, text-only validation, skill-version invalidation, and CLI failure handling |

### Why It Matters

- Turns the extracted transcript/frame bundle into an actual reviewed tutorial workflow instead of leaving rendering entirely hypothetical.
- Makes prompt behavior editable through versioned repo files while preserving reproducibility through manifest digests.
- Mirrors the project's code discipline by forcing validation and review before a tutorial is publish-eligible.

### How to Verify

1. Run checks:
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
2. Create or reuse a video directory containing `tutorial_asset_bundle.json`.
3. Generate the outline package:
   - `.venv/bin/python -m lunduke_transcripts.main tutorial --bundle /path/to/tutorial_asset_bundle.json`
4. Approve and continue:
   - `.venv/bin/python -m lunduke_transcripts.main tutorial --bundle /path/to/tutorial_asset_bundle.json --approve-outline`
5. Verify tutorial outputs under `tutorial/`:
   - `tutorial_definition.json`
   - `lesson_outline.json`
   - `evidence_map.json`
   - `frame_selection_plan.json`
   - `tutorial_validation_report.json`
   - `technical_review_report.json`
   - `adversarial_review_report.json`
   - `tutorial_revision_plan.json`
   - `tutorial_manifest.json`
   - `tutorial_final.md` when publish-eligible

## 2026-03-06 — Sprint 7 Closeout Remediation Completed

Closed the Sprint 7 review findings by hardening frame extraction, bundle
generation, and local source identity behavior.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Bundle contract | `tutorial_asset_bundle.json` is now written whenever `transcript.json` exists and records `frame_capture.status` plus any extraction error |
| Frame safety | Frame extraction now stages into a temporary directory and only replaces `frames/` after success |
| Local IDs | Added regression coverage to keep local source IDs stable across `touch` and rename operations |
| Architecture docs | Added `architecture.md` and aligned the review process with an actual technical decision log |
| Validation | Added regression tests for frame capture failure handling and frame preservation on failed reruns |

### Why It Matters

- Prevents a nominally successful run from hiding a missing canonical bundle.
- Preserves the last known-good screenshots when a reprocess fails.
- Keeps local artifact trees stable for the same media file even when its filesystem metadata changes.

### How to Verify

1. Run automated checks:
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
2. Run a local-file flow with a sidecar caption file:
   - `.venv/bin/python -m lunduke_transcripts.main run --config /tmp/test-config.toml --video-file /path/to/demo.mp4`
3. Verify the bundle output:
   - `tutorial_asset_bundle.json` exists whenever `transcript.json` exists
   - `frame_capture.status` is `captured` on success or `error` on extractor failure
4. Re-run the same command and confirm `videos_new = 0`.
5. Run with a missing local file path and confirm the CLI exits with status `failed`.

## 2026-03-06 — Sprint 7 Tutorial Asset Extraction Delivered

Implemented the extraction phase that turns a YouTube video or local media file
into reusable transcript and frame artifacts for later tutorial generation.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Local ingest | Added local file targets via `[[files]]` config and `--video-file` CLI support |
| Transcript package | Added canonical `transcript.json` with normalized segment timing and provenance |
| Frame extraction | Added `ffmpeg` scene-change frame capture into per-video `frames/` directories |
| Frame manifest | Added `frame_manifest.json` referencing image files and timestamps |
| Bundle manifest | Added `tutorial_asset_bundle.json` as the top-level downstream package |
| Validation | Added tests for local file config parsing, bundle artifacts, rerun idempotency, and missing-file failure handling |

### Why It Matters

- Separates extraction from later rendering so Markdown, HTML, PDF, and PPTX work can build on stable inputs.
- Supports both YouTube and local `.mp4` workflows in one pipeline.
- Keeps image binaries out of JSON while preserving the metadata needed for later generators.

### How to Verify

1. Activate the venv and run checks:
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/black --check src tests`
2. Run a local file flow with sidecar captions:
   - `.venv/bin/python -m lunduke_transcripts.main run --config /tmp/test-config.toml --video-file /path/to/demo.mp4`
3. Verify outputs under the configured data dir:
   - `transcript_exact.vtt`
   - `transcript.json`
   - `frame_manifest.json`
   - `tutorial_asset_bundle.json`
   - `frames/*.jpg`
4. Re-run the same command and confirm `videos_new = 0`.

---

## 2026-03-06 — Planned Transcript + Frame Asset Extraction Phase

Updated the planning docs to define the next implementation phase around canonical
transcript and screen-grab artifacts for downstream tutorial generation.

### Built

| Area | What Was Delivered |
|------|--------------------|
| Product scope | Expanded product definition to include local video ingest, transcript JSON, frame manifests, and tutorial asset bundles |
| Technical design | Reworked design around source-agnostic ingest, scene-detection-based frame extraction, and JSON contracts |
| Sprint plan | Added Sprint 7 focused on transcript extraction, frame capture, and canonical asset packaging |
| Session memory | Updated `context.md` and `WHERE_AM_I.md` to reflect the new phase and locked decisions |

### Why It Matters

- Clarifies that screenshots are stored as files on disk, not embedded in JSON.
- Establishes one canonical intermediate package for future Markdown, HTML, PDF, and PPTX generators.
- Narrows the next build phase to extraction and packaging, which reduces scope risk.

### How to Verify

1. Read [product-definition.md](product-definition.md)
2. Read [design.md](design.md)
3. Read [sprint-plan.md](sprint-plan.md)
4. Confirm the docs consistently describe:
   - local file + YouTube ingest
   - `transcript.json`
   - `frame_manifest.json`
   - `tutorial_asset_bundle.json`

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
