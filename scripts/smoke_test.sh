#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
./.venv/bin/python -m pytest -q
TMP_RUNTIME="$(mktemp -d)"
FMV_RUNTIME="$TMP_RUNTIME" FMV_SKIP_LLM=1 ./.venv/bin/python -m fmv.platform.cli submit tasks/example.json
FMV_RUNTIME="$TMP_RUNTIME" FMV_SKIP_LLM=1 ./.venv/bin/python -m fmv.platform.cli run-once
FMV_RUNTIME="$TMP_RUNTIME" ./.venv/bin/python -m fmv.platform.cli status
rm -rf "$TMP_RUNTIME"
echo 'Smoke tests passed.'
