# lunduke-transcripts

Local-first Python pipeline that discovers new YouTube videos, captures transcripts, and stores:

1. exact transcript artifacts (timestamped + plain text)
2. cleaned transcript artifacts (optional LLM pass)
3. metadata + run reports

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configure

1. Start with [config/channels.toml.example](/Users/leeharrington/projects/lunduke-transcripts/config/channels.toml.example)
2. Copy to `config/channels.toml`
3. Add one or more channels
4. Copy `.env.example` to `.env` and set provider/model/API key:
   - `LLM_PROVIDER=openrouter`
   - `LLM_MODEL=openai/gpt-4.1-mini` (or your preferred OpenRouter model)
   - `OPENROUTER_API_KEY=...`

## CLI

```bash
lunduke-transcripts run --config config/channels.toml
lunduke-transcripts run --config config/channels.toml --article
```

### Date range options

```bash
lunduke-transcripts run --config config/channels.toml --from 2026-02-01 --to 2026-02-29
lunduke-transcripts run --config config/channels.toml --from 2026-02-01
lunduke-transcripts run --config config/channels.toml --to 2026-02-29
lunduke-transcripts run --config config/channels.toml --from 2026-02-01 --to 2026-02-29 --reprocess
lunduke-transcripts run --config config/channels.toml --from 2026-02-01 --to 2026-02-29 --article
```

### Environment file override

```bash
lunduke-transcripts run --config config/channels.toml --env-file .env
```

## Outputs

```text
data/
  db/lunduke_transcripts.sqlite3
  videos/<YYYY-MM-DD_slugified-title__video_id>/
    metadata.json
    transcript_exact.vtt
    transcript_exact.md
    transcript_exact.txt
    transcript_clean.md            # when cleanup succeeds/enabled
    news_article.md               # when article generation succeeds/enabled
    news_article_metadata.json
  runs/<run_id>.json
```

## Scheduling

Use the same run command via scheduler.

### Cron (hourly example)

```bash
15 * * * * cd /Users/REPLACE_ME/projects/lunduke-transcripts && /Users/REPLACE_ME/projects/lunduke-transcripts/scripts/run_pipeline.sh
```

### launchd (macOS)

Use [scripts/com.lunduke.transcripts.plist.example](/Users/leeharrington/projects/lunduke-transcripts/scripts/com.lunduke.transcripts.plist.example), replace `REPLACE_ME`, then:

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
- No transcript files produced: video may not expose captions; check run report status.
- Cleanup/article skipped: set `OPENROUTER_API_KEY` (or `OPENAI_API_KEY`) and provider/model.
- Duplicate processing unexpectedly:
  - default mode skips already processed videos
  - use `--reprocess` only when intentional
