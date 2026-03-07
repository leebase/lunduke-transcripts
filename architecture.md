# Architecture Decisions

> Technical decisions that are stable enough to warrant a record.

---

## 2026-03-06 — Stable local source identifiers use content fingerprints

**Decision:** Local media source IDs are derived from a content hash of the file bytes rather than path, size, or modified time metadata.

**Rationale:** Local tutorial assets need idempotent storage keys that survive harmless file operations like rename, move, or `touch`. Path- or mtime-based identifiers create duplicate artifact trees for the same logical source.

**Alternatives rejected:** Path + size + mtime fingerprints were simpler to compute, but they treated metadata churn as a new source and broke local rerun stability.

**Consequences:** Local media probing reads the full file once to compute the source ID. In return, artifact directories and rerun behavior stay stable across common file-management operations.

## 2026-03-06 — Frame extraction replaces artifacts only after a successful extraction

**Decision:** Frame extraction writes into a temporary sibling directory and only swaps it into `frames/` after `ffmpeg` succeeds.

**Rationale:** Reprocessing must not destroy a previously good frame set when a later extraction fails. The old frames remain the last known-good asset package until a replacement is ready.

**Alternatives rejected:** Writing directly into `frames/` was simpler, but it deleted existing screenshots before success was known and turned transient extractor failures into artifact loss.

**Consequences:** Extraction uses a temporary directory and a replace step. Failed runs leave prior frame artifacts intact, which is the safer default for downstream generators.

## 2026-03-06 — Bundle manifests are always written once transcript JSON exists

**Decision:** `tutorial_asset_bundle.json` is written whenever `transcript.json` is produced, even if frame capture is disabled or fails. The bundle records `frame_capture.status`, optional `frame_manifest_path`, and any frame error message.

**Rationale:** Downstream renderers need one canonical file to inspect. Missing the bundle entirely on a partially successful extraction makes failure handling harder than carrying explicit state inside the manifest.

**Alternatives rejected:** Omitting the bundle on frame failure hid the degraded state behind a missing file. Treating frame failures as warnings also failed the product contract because the canonical bundle could disappear on a nominally successful run.

**Consequences:** Successful transcript extraction can still produce a degraded bundle, but the run is marked `failed` or `partial` when frame capture was required and did not succeed. Downstream code can inspect one manifest instead of guessing from missing files.

## 2026-03-06 — Tutorial behavior lives in repo-local agent and skill files

**Decision:** The downstream tutorial pipeline loads agent role files from `agents/` and reusable tutorial skills from `skills/`.

**Rationale:** Tutorial generation needs fast prompt iteration without rewriting orchestration code. Repo-local files keep prompt evolution versioned with the code and artifacts they influence.

**Alternatives rejected:** Hardcoding prompts in Python would make iteration slower and hide behavioral changes from git history. An external prompt store would weaken reproducibility for this local-first workflow.

**Consequences:** Tutorial manifests record digests for agent and skill files. Prompt changes invalidate the cache and are visible in generated artifacts.

## 2026-03-06 — Tutorial generation uses an approval and editorial review loop

**Decision:** The tutorial command stops after outline generation until the human reruns with `--approve-outline`, then it runs validation, technical review, adversarial review, and review response as co-editors before writing the latest `tutorial_final.md`.

**Rationale:** The tutorial flow should mirror how the project writes code: define done, plan, draft, test, review, respond to review. That cooperation model is more reliable than letting one prompt write straight to a publishable tutorial, but the reviewers are meant to improve the draft rather than veto it.

**Alternatives rejected:** A single-pass writer would be simpler but too prone to smooth factual drift. Hard publish gates for every editorial disagreement made the pipeline overweight objections and left stale public artifacts behind. Fully manual gating at every stage would be slower than needed for v1.

**Consequences:** Tutorial generation produces more intermediate artifacts, and review warnings remain machine-readable with reroute targets, but editorial findings do not suppress later reviewer stages or prevent the latest approved tutorial artifact from being written.

## 2026-03-06 — PDF rendering is downstream from tutorial generation and image-aware

**Decision:** Published tutorials render from `tutorial_final.md` via a separate
`render` CLI command that consumes `tutorial_manifest.json`, validates Markdown
image references, uses `pandoc` to create standalone HTML, and then uses a
Chrome-family browser binary to print PDF.

**Rationale:** Rendering is a format concern, not an LLM concern. Keeping it
downstream avoids rerunning tutorial generation when only layout changes, and
image validation must happen before render so screenshot-heavy tutorials never
claim success with broken references.

**Alternatives rejected:** Embedding image bytes into JSON would bloat canonical
artifacts and blur the separation between extraction and rendering. Generating
PDF directly from Markdown without an HTML stage would make screenshot layout
and page-break control harder. Reusing stale HTML/PDF outputs on failed renders
was rejected because it hides real image-validation failures.

**Consequences:** The renderer writes `tutorial_final.html`,
`tutorial_final.pdf`, and `render_manifest.json` inside the tutorial directory.
The pipeline removes stale render outputs before each attempt, and it prefers
Google Chrome on macOS when available because Chromium may not exit cleanly
after writing headless PDFs.

## 2026-03-07 — Adversarial tutorial review is mandatory but advisory-only

**Decision:** The tutorial pipeline always runs the adversarial reviewer before a
tutorial is publish-eligible, but adversarial findings cannot block publication
on their own.

**Rationale:** The adversarial pass is there to inject counter-narrative pressure
and catch overreach, not to overpower the validator and technical reviewer. That
keeps the red-team role useful without turning every objection into a veto.

**Alternatives rejected:** Treating adversarial review as a hard gate made the
pipeline overweight objections and pushed it toward overly defensive output.
Skipping adversarial review entirely would remove an important source of
pressure-testing before publish.

**Consequences:** Adversarial findings can trigger reroute cycles and remain
visible as warnings in the manifest when unresolved, but they do not veto the
latest tutorial artifact.

## 2026-03-07 — Public tutorial Markdown enforces navigation and internal-note hygiene

**Decision:** Published tutorial Markdown is a public artifact with required
reader-facing structure: context, table of contents, back-to-top navigation, and
no leaked evidence/provenance callouts.

**Rationale:** Grounding artifacts are useful for the pipeline, but they do not
belong in reader-facing tutorials. The final Markdown has to read like a real
tutorial, not a transcript with internal scaffolding attached.

**Alternatives rejected:** Relying on prompts alone let internal review language
and weak navigation leak into outputs. Leaving these checks entirely to later
review agents made the contract too soft.

**Consequences:** The validator now enforces public-artifact structure, and the
writer/reviewer prompts explicitly separate sidecar evidence artifacts from the
final tutorial. Tutorial definition flags can relax these requirements when a
future format legitimately needs a different structure.

## 2026-03-07 — Expensive tutorial stages route through `lee-llm-router`

**Decision:** Tutorial planning/evidence stages may stay on cheaper API models,
while the default ChatGPT Plus routing is reserved for the heaviest editorial
stages (`tutorial.writer` and `tutorial.technical-review`).

**Rationale:** The strongest model quality is most valuable when the pipeline is
writing or judging public tutorial prose. Using it for the easy extraction or
planning stages adds cost and latency without a matching benefit.

**Alternatives rejected:** A full global switch to the strongest model would
increase cost and latency across the whole app. Keeping everything on the
smaller API model left the tutorial pipeline too weak editorially. Calling the
raw ChatGPT backend directly from the app would duplicate provider logic that
already belongs in `lee-llm-router`.

**Consequences:** The lunduke CLI now accepts router config/env settings and
task-role mappings. Router paths are resolved relative to the selected config
file, with a repo-root fallback for `config/...` assets that exist there. The
subscription provider in `lee-llm-router` now sends `instructions`, uses SSE,
stops on the completion signal, omits unsupported `temperature`, and enforces a
wall-clock timeout guard for streaming responses.
