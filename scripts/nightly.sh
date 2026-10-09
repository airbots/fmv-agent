#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
export FMV_RUNTIME="$PWD/runtime"
export FMV_MODEL="${FMV_MODEL:-deepseek-r1:32b}"
mkdir -p "$FMV_RUNTIME"
# macOS single runner lock using mkdir, remove on exit
if ! mkdir "$FMV_RUNTIME/.worker-lock" 2>/dev/null; then
  echo 'Another worker is active (or stale lock). Exit.'
  exit 0
fi
trap 'rmdir "$FMV_RUNTIME/.worker-lock"' EXIT
./.venv/bin/python -m fmv.platform.cli run-once
