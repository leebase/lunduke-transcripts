# Product Definition: lunduke-transcripts

> Product-level definition for what this tool must do, how we measure success, and what is out of scope.

---

## Product Summary

`lunduke-transcripts` is a local-first Python app that ingests video from YouTube
and local media files, extracts transcripts, captures important visual frames, and
stores both:

1. an **exact transcript** (faithful to source captions or ASR timing), and
2. a **canonical tutorial asset package** (JSON + referenced files) for downstream
   publishing workflows.

When captions are unavailable, the app can optionally run local ASR transcription
as a fallback using a pluggable provider architecture (fast-whisper first).

The app must run:
- on demand (manual/CLI), and
- on a recurring schedule (via system scheduler).

---

## Primary User

Lee (or similar user) who wants a durable, searchable local archive of video
transcripts, frame grabs, and metadata for future tutorial, article, and training
workflows.

---

## Core Jobs To Be Done

1. Run the app at will and extract tutorial-ready assets from video sources.
2. Run automatically on a schedule without manual babysitting.
3. Avoid duplicate work by identifying videos already processed.
4. Preserve source-faithful transcript output for auditing.
5. Capture useful screenshots without embedding binary image data in JSON artifacts.
6. Store useful metadata (publish date/time, channel info, IDs, fetch time, language, etc.).
7. Produce a canonical JSON package that later efforts can use to generate Markdown,
   HTML, PDF, PPTX, and other training outputs.
8. Optionally run processing for a specific video publish-date range.
9. Turn a canonical tutorial asset bundle into a reviewed written tutorial without
   re-running transcript or frame extraction.

---

## Functional Requirements

### FR-1: Source Ingest
- Input one or more media sources:
  - YouTube channel sources (channel URL/handle/playlist form)
  - direct YouTube video URLs
  - local video file paths (for example `.mp4`)
- Enumerate recent videos for channel sources.
- Identify videos not yet processed using persistent state keyed by a stable source
  identifier.

### FR-2: New Video Detection
- A run must be idempotent.
- Re-running immediately should not create duplicate outputs for already processed videos.
- State must survive process restarts.

### FR-3: Exact Transcript Acquisition
- For each new video, attempt to fetch caption/transcript data.
- For local files, support transcript acquisition from sidecar captions when present
  and ASR when captions are not available.
- Support optional ASR fallback when captions are unavailable.
- Preserve timestamps in at least one canonical output format.
- Preserve source fidelity as much as available from provider data.
- Record when no transcript is available.

### FR-3a: Pluggable ASR Provider Architecture
- ASR must use a provider plugin interface so implementations can be swapped later.
- MVP ASR provider implementation is `fast-whisper`.
- Provider identity and model metadata must be captured in output metadata.
- If configured ASR provider is unavailable, run should log clear status and continue.

### FR-4: Transcript Normalization
- Generate normalized transcript JSON from the exact transcript.
- Keep segment timing, text, and provenance metadata.
- Preserve meaning and factual content; do not summarize or invent.
- Keep the exact transcript as the canonical audit artifact.

### FR-5: Metadata Capture
For each video, store metadata at minimum:
- `source_id`
- `source_kind` (`youtube_channel`, `youtube_video`, `local_file`)
- `video_id` (nullable for non-YouTube sources)
- `video_url` (nullable for local files)
- `local_path` (when source is local)
- `channel_id`
- `channel_name`
- `title`
- `description` (if available)
- `published_at` (original video publish datetime when available)
- `captured_at` (when our app processed it)
- `transcript_language`
- `transcript_source` (manual captions, auto captions, ASR provider, unavailable, unknown)
- `duration_seconds` (if available)
- `asr_provider` and `asr_model` (when ASR path is used)
- `clip_start` / `clip_end` bounds (when clip transcription is used)

### FR-6: Output Artifacts
Per processed video, persist:
1. Exact transcript with timestamps.
2. Exact transcript without timestamps (optional but preferred).
3. Transcript JSON with normalized segments and metadata.
4. Metadata file (JSON).
5. Run-level processing status (success/failure reason).
6. Optional ASR segment artifact for debugging/audit (preferred).
7. Screen-grab image files stored on disk.
8. Frame manifest JSON referencing those image files.
9. Tutorial asset bundle JSON referencing transcript JSON, frame manifest, and other artifacts.

### FR-7: Significant Frame Capture
- The pipeline must support extracting visual frame candidates from the source video.
- Frame image binaries must be written to files on disk; JSON artifacts must only
  reference file paths and metadata.
- The system must support scene-change-driven frame candidate extraction.
- The system should support a later content-selection pass that chooses the most
  instructionally useful frames from candidates.

### FR-8: Canonical Tutorial Asset Package
- For each processed video, generate a canonical JSON package for downstream
  rendering workflows.
- The package must reference:
  - transcript segments
  - frame candidates or selected frames
  - source metadata
  - artifact paths
- The package must be stable enough for later Markdown, HTML, PDF, and PPTX
  generators to consume without re-running transcription or frame extraction.

### FR-12: Multi-Agent Tutorial Generation
- The system must support a downstream tutorial-generation pipeline that consumes
  `tutorial_asset_bundle.json`.
- The tutorial pipeline must use specialized repo-local agent definitions and
  reusable repo-local skill files.
- The pipeline must support these roles:
  - educator
  - tutorial planner
  - evidence mapper
  - script writer
  - visual editor
  - validator
  - technical reviewer
  - adversarial reviewer
  - review responder
- Agent and skill definitions must be editable without changing orchestration code.

### FR-13: Tutorial Workflow Cooperation
- Tutorial generation must follow this workflow:
  - define done
  - plan
  - draft
  - validate
  - review
- respond to review
  - publish
- The outline package must require explicit human approval before drafting
  continues.
- Validation, technical review, and adversarial review must all run before the
  tutorial is considered complete.
- Review stages are co-editors, not go/no-go gates.
- Editorial findings must be captured as machine-readable review and revision
  artifacts, but they must not suppress later editorial stages or prevent a
  fresh latest tutorial artifact from being written after outline approval.

### FR-14: Tutorial Outputs
- The first downstream tutorial target is written Markdown.
- The pipeline must write these artifacts under a per-video tutorial directory:
  - `tutorial_definition.json`
  - `lesson_outline.json`
  - `evidence_map.json`
  - `frame_selection_plan.json`
  - `tutorial_draft.md`
  - `tutorial_validation_report.json`
  - `technical_review_report.json`
  - `adversarial_review_report.json`
  - `tutorial_revision_plan.json`
  - `tutorial_manifest.json`
  - `tutorial_final.md`
- The tutorial manifest must record prompt/skill versions, review outcomes, human
  approval state, and review warnings/outcomes for the latest run.

### FR-9: Execution Modes
- Manual mode: run once now.
- Scheduled mode: compatible with system scheduler (cron/launchd/task scheduler).
- Scheduled run uses the same idempotent behavior and state.

### FR-10: Date Range Option
- Manual runs must support optional date-range filters on `published_at`.
- Supported filters:
  - start + end date (`from` and `to`)
  - open-ended start-only (`from`)
  - open-ended end-only (`to`)
- Date range matching is inclusive of boundary dates.
- Date-only inputs are interpreted in a configured timezone and stored internally in UTC.
- When date filters are provided, only videos with `published_at` in range are candidates for processing.
- Idempotency still applies by default; already processed videos in range are skipped unless explicitly reprocess mode is requested.

### FR-11: Single-Video Clip Transcription
- Single-video targets may optionally define clip bounds (`clip_start`, `clip_end`).
- When clip bounds are provided, transcription should run on that subrange only.
- Clip transcription supports both caption path and ASR fallback path.

---

## Suggested Output Structure (Current Direction)

```text
data/
  db/lunduke_transcripts.sqlite3
  runs/
    <run_id>.json
  videos/
    <artifact_dir>/
      metadata.json
      transcript_exact.vtt
      transcript_exact.md
      transcript_exact.txt
      transcript.json
      frame_manifest.json
      tutorial_asset_bundle.json
      frames/
        000123.jpg
        000456.jpg
```

Frame images are stored as files on disk. JSON artifacts reference those files by
path and metadata; image bytes are not embedded in JSON.

---

## Non-Functional Requirements

1. **Reliability**: One failed video should not abort the entire run.
2. **Traceability**: Every run produces a machine-readable run report.
3. **Reproducibility**: Outputs are deterministic for identical inputs and model settings.
4. **Local-first**: All outputs are stored locally under the project directory.
5. **Performance (MVP)**: Handle at least 1-3 channels and recent video history without manual intervention.
6. **Portable downstream use**: JSON artifacts must reference files with relative or
   resolvable local paths; no binary image payloads are embedded in JSON.

---

## Out of Scope (Current Phase)

- Auto-posting transcripts to forums or websites.
- Full analytics dashboard/UI.
- Speaker diarization and advanced transcript enrichment.
- Editing/re-uploading YouTube captions.
- Final polished PDF/PPTX/web export generation remains out of scope.

---

## Success Criteria (Current Phase)

The current phase is successful when all are true:

1. User can run one command against a YouTube video or local media file.
2. Exact transcript artifacts are saved with timestamps.
3. `transcript.json` is generated with normalized segment timing and provenance.
4. Frame image files plus a frame manifest are produced without embedding image data into JSON.
5. `tutorial_asset_bundle.json` references transcript JSON, frame manifest, and metadata artifacts.
6. Second run with no new videos completes cleanly and reports zero new items unless reprocess is requested.
7. User can run with a date range and process only videos published in that range where publish metadata exists.
8. User can run a downstream tutorial command against `tutorial_asset_bundle.json`.
9. The tutorial pipeline stops at outline approval until explicitly approved.
10. A passing tutorial writes reviewed Markdown plus machine-readable validation and review artifacts.

---

## Risks and Mitigations

1. **Caption availability varies by video**
   - Mitigation: ASR fallback path + clear source status and continue run.
2. **YouTube extraction behavior may change**
   - Mitigation: Isolate acquisition layer behind adapter interface.
3. **LLM cost/latency variability**
   - Mitigation: Keep JSON extraction independent from later tutorial-generation passes.
4. **Transcript cleanup could alter meaning**
   - Mitigation: Keep exact transcript as source of truth; enforce non-summarization prompt rules.
5. **Visual scene detection may select noisy frames**
   - Mitigation: Extract candidates via scene detection, then allow later selection or scoring passes to choose tutorial-worthy frames.
6. **Tutorial agents may drift from the source**
   - Mitigation: use evidence mapping, mandatory validation, technical review, and adversarial review before publish.

---

## Open Product Decisions

1. Whether local files should prefer sidecar subtitle files before ASR.
2. How aggressive frame candidate extraction should be by default.
3. Whether the first JSON package should include all frame candidates or only selected instructional frames.
4. Exact CLI/config contract for local file inputs.
5. Default ASR provider/model/device settings for low-cost local usage.
6. When to add vision-aware frame review instead of metadata-only frame selection.

---

## Initial Delivery Slices (TinyClaw)

### Slice 1: Source-Agnostic Transcript Extraction
- Add local file input support alongside YouTube video targets
- Normalize transcript output into exact transcript artifacts plus `transcript.json`
- Preserve existing idempotent run/report behavior

### Slice 2: Frame Candidate Extraction
- Download or access video media needed for frame extraction
- Run scene-change-based frame candidate extraction
- Write frame files to disk plus `frame_manifest.json`

### Slice 3: Canonical Tutorial Asset Bundle
- Write `tutorial_asset_bundle.json`
- Reference transcript JSON, frame manifest, metadata, and source info
- Keep the bundle stable for later Markdown/HTML/PDF/PPTX generators

### Slice 4: Multi-Agent Written Tutorial Generation
- Add repo-local agent and skill definitions
- Add tutorial workflow artifacts and approval gate
- Add validation, review, and review-response stages
- Write `tutorial_final.md` plus `tutorial_manifest.json`

---

Last updated: 2026-03-06
