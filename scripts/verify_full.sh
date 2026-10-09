#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python -m compileall -q fmv
python -m pytest -q
python -m fmv.platform.cli --help >/dev/null
python - <<'CHECK'
from fmv.platform.worker import process
from fmv.reports.schema import normalize_report
from fmv.agents.assumptions import model_assumptions
print('Imports OK / CLI OK / tests OK')
CHECK
