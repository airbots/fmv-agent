#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export FMV_RUNTIME="${FMV_RUNTIME:-$ROOT/runtime}"
exec python -m streamlit run fmv/reports/dashboard.py --server.address 127.0.0.1 --server.port 8501
