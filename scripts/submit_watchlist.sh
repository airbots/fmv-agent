#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
for ticker in "${@:-MU}"; do
  python -m fmv.platform.cli submit-ticker "$ticker"
done
