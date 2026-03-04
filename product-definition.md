# Product Definition: lunduke-transcripts

> Product-level definition for what this tool must do, how we measure success, and what is out of scope.

---

## Product Summary

`lunduke-transcripts` is a local-first Python app that monitors one or more YouTube channels, detects newly published videos, downloads available transcripts, and stores both:

1. an **exact transcript** (faithful to the source captions), and
2. an **LLM-cleaned transcript** (readability pass for downstream use).

The app must run:
- on demand (manual/CLI), and
- on a recurring schedule (via system scheduler).

---

## Primary User

Lee (or similar user) who wants a durable, searchable local archive of a journalist's video transcripts and metadata for analysis and future publishing workflows.

---

## Core Jobs To Be Done

1. Run the app at will and fetch transcripts for new videos.
2. Run automatically on a schedule without manual babysitting.
3. Avoid duplicate work by identifying videos already processed.
4. Preserve source-faithful transcript output for auditing.
5. Generate a cleaned transcript for easier reading and LLM/analysis use.
6. Store useful metadata (publish date/time, channel info, IDs, fetch time, language, etc.).
7. Optionally run processing for a specific video publish-date range.

---

## Functional Requirements

### FR-1: Channel Monitoring
- Input one or more YouTube channel sources (channel URL/handle/playlist form).
- Enumerate recent videos for each source.
- Identify videos not yet processed using persistent state keyed by `video_id`.

### FR-2: New Video Detection
- A run must be idempotent.
- Re-running immediately should not create duplicate outputs for already processed videos.
- State must survive process restarts.

### FR-3: Exact Transcript Acquisition
- For each new video, attempt to fetch caption/transcript data.
- Preserve timestamps in at least one canonical output format.
- Preserve source fidelity as much as available from provider data.
- Record when no transcript is available.

### FR-4: LLM Cleanup Pass
- Generate a cleaned transcript from the exact transcript.
- Cleanup goals: punctuation, sentence boundaries, filler cleanup, typo normalization.
- Preserve meaning and factual content; do not summarize or invent.
- Keep optional timestamp anchors or paragraph-level timestamp mapping.

### FR-5: Metadata Capture
For each video, store metadata at minimum:
- `video_id`
- `video_url`
- `channel_id`
- `channel_name`
- `title`
- `description` (if available)
- `published_at` (original video publish datetime)
- `captured_at` (when our app processed it)
- `transcript_language`
- `transcript_source` (manual captions, auto captions, unavailable, unknown)
- `duration_seconds` (if available)

### FR-6: Output Artifacts
Per processed video, persist:
1. Exact transcript with timestamps.
2. Exact transcript without timestamps (optional but preferred).
3. Cleaned transcript (readable format).
4. Metadata file (JSON).
5. Run-level processing status (success/failure reason).

### FR-7: Execution Modes
- Manual mode: run once now.
- Scheduled mode: compatible with system scheduler (cron/launchd/task scheduler).
- Scheduled run uses the same idempotent behavior and state.

### FR-8: Date Range Option
- Manual runs must support optional date-range filters on `published_at`.
- Supported filters:
  - start + end date (`from` and `to`)
  - open-ended start-only (`from`)
  - open-ended end-only (`to`)
- Date range matching is inclusive of boundary dates.
- Date-only inputs are interpreted in a configured timezone and stored internally in UTC.
- When date filters are provided, only videos with `published_at` in range are candidates for processing.
- Idempotency still applies by default; already processed videos in range are skipped unless explicitly reprocess mode is requested.

---

## Suggested Output Structure (MVP)

```text
data/
  state/
    processed_videos.json
  runs/
    2026-03-04T21-00-00Z_run.json
  videos/
    <video_id>/
      metadata.json
      transcript_exact.vtt
      transcript_exact.md
      transcript_clean.md
```

This structure is a default and may be revised during implementation if it improves reliability.

---

## Non-Functional Requirements

1. **Reliability**: One failed video should not abort the entire run.
2. **Traceability**: Every run produces a machine-readable run report.
3. **Reproducibility**: Outputs are deterministic for identical inputs and model settings.
4. **Local-first**: All outputs are stored locally under the project directory.
5. **Performance (MVP)**: Handle at least 1-3 channels and recent video history without manual intervention.

---

## Out of Scope (MVP)

- Auto-posting transcripts to forums or websites.
- Full analytics dashboard/UI.
- Speaker diarization and advanced transcript enrichment.
- Editing/re-uploading YouTube captions.

---

## Success Criteria (MVP)

The MVP is successful when all are true:

1. User can run one command and process new videos from configured channels.
2. User can schedule that same command and it runs unattended.
3. For videos with captions, exact transcript artifacts are saved with timestamps.
4. Cleaned transcript artifacts are generated from exact transcripts.
5. Metadata files include publish datetime and processing datetime.
6. Second run with no new videos completes cleanly and reports zero new items.
7. User can run with a date range and process only videos published in that range.

---

## Risks and Mitigations

1. **Caption availability varies by video**
   - Mitigation: Mark status clearly as unavailable and continue run.
2. **YouTube extraction behavior may change**
   - Mitigation: Isolate acquisition layer behind adapter interface.
3. **LLM cost/latency variability**
   - Mitigation: Optional cleanup pass; cache cleaned outputs by transcript hash.
4. **Transcript cleanup could alter meaning**
   - Mitigation: Keep exact transcript as source of truth; enforce non-summarization prompt rules.

---

## Open Product Decisions

1. Preferred LLM provider/model for cleanup pass.
2. Required output formats (`.md`, `.txt`, `.json`) beyond MVP defaults.
3. Whether cleaned transcript must retain full line-level timestamps or only section anchors.
4. Channel configuration source (CLI args vs config file vs both).
5. Exact CLI contract for reprocessing behavior inside a date range.

---

## Initial Delivery Slices (TinyClaw)

### Slice 1: Exact Transcript Pipeline
- Single channel input
- New video detection
- Date-range filtered discovery (published date)
- Exact transcript + metadata output
- No cleanup pass yet

### Slice 2: LLM Cleanup Pipeline
- Cleaned transcript generation
- Prompt + guardrails for fidelity
- Cache by transcript hash

### Slice 3: Scheduling + Hardening
- Scheduler docs/scripts
- Run reports and retry behavior
- Multi-channel support

---

Last updated: 2026-03-04
