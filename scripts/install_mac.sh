#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3.12 >/dev/null || { echo 'Install python@3.12 with Homebrew'; exit 1; }
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -e '.[dev,dashboard]'
echo 'Installed. Set SEC_USER_AGENT for future SEC connectivity; run scripts/smoke_test.sh'
