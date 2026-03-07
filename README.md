# lunduke-transcripts

Local-first Python pipeline that ingests YouTube videos or local media files, captures transcripts and frame candidates, and stores:

1. exact transcript artifacts (timestamped + plain text)
2. canonical JSON artifacts for downstream tutorial generation
3. multi-agent tutorial artifacts with review gates
4. metadata + run reports

## Install

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install faster-whisper
brew install pandoc chromium
```

ASR clip transcription also requires `ffmpeg` available on your `PATH` (or set `[app].ffmpeg_binary`).
PDF rendering uses `pandoc` plus a Chrome-family browser binary. On macOS, the
renderer will prefer Google Chrome if it is installed, then fall back to
`chromium`.

## Configure

1. Start with [config/channels.toml.example](config/channels.toml.example)
2. Copy to `config/channels.toml`
3. Add one or more `[[channels]]`, `[[videos]]`, and/or `[[files]]` targets
4. Copy `.env.example` to `.env` and set provider/model/API key:
   - `LLM_PROVIDER=openrouter`
   - `LLM_MODEL=openai/gpt-4.1-mini` (or your preferred OpenRouter model)
   - `OPENROUTER_API_KEY=...`

## CLI

```bash
lunduke-transcripts run --config config/channels.toml
lunduke-transcripts run --config config/channels.toml --article
lunduke-transcripts run --url "https://www.youtube.com/watch?v=VIDEO_ID"
lunduke-transcripts run --channel-url "https://www.youtube.com/@Lunduke/videos"
lunduke-transcripts run --video-url "https://www.youtube.com/watch?v=VIDEO_ID"
lunduke-transcripts run --video-file "/absolute/path/to/demo.mp4"
lunduke-transcripts run --video-url "https://www.youtube.com/watch?v=VIDEO_ID" --asr-fallback
lunduke-transcripts run --video-url "https://www.youtube.com/watch?v=VIDEO_ID" --force-asr --clip-start 00:30:40 --clip-end 01:12:35
lunduke-transcripts tutorial --bundle data/videos/.../tutorial_asset_bundle.json
lunduke-transcripts tutorial --bundle data/videos/.../tutorial_asset_bundle.json --approve-outline
lunduke-transcripts render --manifest data/videos/.../tutorial/tutorial_manifest.json --target pdf
```

You can pass one or more `--url` values (auto-detect channel vs video), or use
`--channel-url` / `--video-url` / `--video-file` explicitly.
When any URL flag is provided, the run works even if `--config` does not exist.

### Date range options

```bash
lunduke-transcripts run --config config/channels.toml --from 2026-02-01 --to 2026-02-29
lunduke-transcripts run --config config/channels.toml --from 2026-02-01
lunduke-transcripts run --config config/channels.toml --to 2026-02-29
lunduke-transcripts run --config config/channels.toml --from 2026-02-01 --to 2026-02-29 --reprocess
lunduke-transcripts run --config config/channels.toml --from 2026-02-01 --to 2026-02-29 --article
lunduke-transcripts run --url "https://www.youtube.com/watch?v=VIDEO_ID" --from 2026-02-01 --to 2026-02-29
lunduke-transcripts run --video-url "https://www.youtube.com/watch?v=VIDEO_ID" --from 2026-02-01 --to 2026-02-29
```

### Environment file override

```bash
lunduke-transcripts run --config config/channels.toml --env-file .env
lunduke-transcripts tutorial --bundle data/videos/.../tutorial_asset_bundle.json --env-file .env
lunduke-transcripts render --manifest data/videos/.../tutorial/tutorial_manifest.json --env-file .env
```

### Tutorial generation

The `tutorial` command is a downstream pipeline that consumes an existing
`tutorial_asset_bundle.json`.

- First run without `--approve-outline`:
  - generates `tutorial_definition.json`, `lesson_outline.json`,
    `evidence_map.json`, and `frame_selection_plan.json`
  - stops with `status: "awaiting_outline_approval"`
- Re-run with `--approve-outline`:
  - drafts the tutorial
  - validates structure and evidence coverage
  - runs technical review plus adversarial review
  - writes `tutorial_final.md` only if the tutorial clears the review gate

Optional flags:
- `--reprocess`
- `--max-review-cycles`
- `--agents-dir`
- `--skills-dir`

### Tutorial rendering

The `render` command is a downstream format-only pipeline that consumes an
existing `tutorial_manifest.json`.

- It validates that all Markdown image references resolve before rendering.
- It writes:
  - `tutorial_final.html`
  - `tutorial_final.pdf`
  - `render_manifest.json`
- It does not rerun tutorial generation or call the LLM.

Example:

```bash
lunduke-transcripts render \
  --manifest data/videos/.../tutorial/tutorial_manifest.json \
  --target pdf
```

### ASR fallback settings

`[app]` supports:
- `enable_asr_fallback`
- `force_asr`
- `asr_provider` (`fast-whisper`)
- `asr_model`
- `asr_device`
- `asr_compute_type`
- `ffmpeg_binary`
- `ffmpeg_timeout_seconds`
- `keep_audio_files`

`[[videos]]` supports:
- `clip_start`
- `clip_end`
- `force_asr`

`[[files]]` supports:
- `path`
- `clip_start`
- `clip_end`
- `force_asr`

`[app]` also supports renderer settings:
- `pandoc_binary`
- `pdf_engine` (`chromium`)
- `pdf_engine_binary`

## Outputs

```text
data/
  db/lunduke_transcripts.sqlite3
  videos/<YYYY-MM-DD_slugified-title__video_id>/
    metadata.json
    transcript_exact.vtt
    transcript_exact.md
    transcript_exact.txt
    transcript.json
    frame_manifest.json            # when frame capture succeeds
    tutorial_asset_bundle.json     # always written when transcript.json exists
    frames/*.jpg                   # scene-change frame candidates when capture succeeds
    transcript_segments.tsv        # when ASR path is used
    transcript_clean.md            # when cleanup succeeds/enabled
    news_article.md               # when article generation succeeds/enabled
    news_article_metadata.json
    tutorial/
      tutorial_definition.json
      lesson_outline.json
      evidence_map.json
      frame_selection_plan.json
      tutorial_draft.md
      tutorial_validation_report.json
      technical_review_report.json
      adversarial_review_report.json
      tutorial_revision_plan.json
      tutorial_final.md           # when publish-eligible
      tutorial_manifest.json
      tutorial_final.html         # when render succeeds
      tutorial_final.pdf          # when render succeeds
      render_manifest.json
  runs/<run_id>.json
```

## Scheduling

Use the same run command via scheduler.

### Cron (hourly example)

```bash
15 * * * * cd /path/to/lunduke-transcripts && /path/to/lunduke-transcripts/scripts/run_pipeline.sh
```

### launchd (macOS)

Use [scripts/com.lunduke.transcripts.plist.example](scripts/com.lunduke.transcripts.plist.example), replace `REPLACE_ME`, then:

```bash
launchctl load ~/Library/LaunchAgents/com.lunduke.transcripts.plist
```

## Development

Run tests:

```bash
pytest
```

Lint/format:

```bash
ruff check src tests
black src tests
```

## Troubleshooting

- `yt-dlp not found`: set `[app].yt_dlp_binary` in config or install in active environment.
- `yt-dlp` hangs/slow responses:
  - tune `[app].yt_dlp_timeout_seconds`
  - tune `[app].fetch_retries` and `[app].retry_backoff_seconds`
- No transcript files produced: video may not expose captions; check run report status.
- Local file transcript missing: add a sidecar `.vtt`/`.srt` next to the media file or enable ASR fallback.
- Frame capture failed:
  - inspect `tutorial_asset_bundle.json` for `frame_capture.status` and `frame_capture.error`
  - check the run report for the `frames` step error
- ASR fallback not running: set `enable_asr_fallback = true` (or pass `--asr-fallback`) and install `faster-whisper`.
- ASR clipping errors:
  - verify `ffmpeg` is installed
  - verify clip formats like `HH:MM:SS` or `MM:SS`
- Missing local file input:
  - verify the `--video-file` path exists
  - verify the path points to a file, not a directory
- Cleanup/article skipped: set `OPENROUTER_API_KEY` (or `OPENAI_API_KEY`) and provider/model.
- Tutorial generation failed immediately:
  - verify `OPENROUTER_API_KEY` or `OPENAI_API_KEY` is available for the configured provider
  - verify the agent and skill directories exist and contain the expected files
- Tutorial stuck at approval gate:
  - first run is expected to stop at `status: "awaiting_outline_approval"`
  - rerun with `--approve-outline` after reviewing the outline artifacts
- Render failed immediately:
  - verify `pandoc` is installed
  - verify a Chrome-family browser binary is installed and reachable
  - inspect `render_manifest.json` for `image_validation` and toolchain details
- Missing images in PDF render:
  - verify `tutorial_final.md` still references valid `../frames/...` paths
  - rerun render only after restoring the missing frame files
- LLM timeout/retry behavior:
  - set `LLM_TIMEOUT_SECONDS`, `LLM_RETRIES`, `LLM_RETRY_BACKOFF_SECONDS` in `.env`
- Duplicate processing unexpectedly:
  - default mode skips already processed videos
  - use `--reprocess` only when intentional
