#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.aurorain.fmv-worker.plist"
mkdir -p "$(dirname "$DEST")"
/usr/bin/python3 - "$ROOT" "$DEST" <<'PY2'
import sys
from pathlib import Path
root,dest=map(Path,sys.argv[1:])
content=(root/'launchd/com.aurorain.fmv-worker.plist.template').read_text().replace('__PROJECT_ROOT__',str(root))
dest.write_text(content)
PY2
plutil -lint "$DEST"
launchctl bootstrap "gui/$(id -u)" "$DEST" || echo 'Already loaded? Use launchctl bootout first.'
echo "Scheduled 22:00 local: $DEST"
