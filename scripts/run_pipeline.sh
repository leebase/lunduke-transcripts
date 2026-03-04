#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv in $ROOT_DIR" >&2
  exit 1
fi

source ".venv/bin/activate"
python -m lunduke_transcripts.main run --config config/channels.toml "$@"
