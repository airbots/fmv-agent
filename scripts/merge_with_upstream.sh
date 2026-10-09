#!/bin/zsh
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/projects/fmv-agent}"
if [[ ! -f "$TARGET/app.py" || ! -f "$TARGET/sec_fetcher.py" ]]; then
  echo "Expected original fmv-agent files at $TARGET. Clone upstream first." >&2
  exit 1
fi
if [[ "$TARGET" == "$SRC" ]]; then echo 'Target cannot be source'; exit 1; fi
cp -R "$SRC/fmv" "$TARGET/"
cp -R "$SRC/config" "$SRC/launchd" "$SRC/scripts" "$SRC/tasks" "$SRC/tests" "$TARGET/"
cp "$SRC/pyproject.toml" "$SRC/.gitignore.autonomous" "$TARGET/"
echo 'Overlay installed. Original app.py and sec_fetcher.py preserved.'
