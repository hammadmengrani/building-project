#!/usr/bin/env bash
set -euo pipefail
STUDIO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$STUDIO_ROOT"
if [[ -x "$STUDIO_ROOT/../venv/bin/python" ]]; then
  exec "$STUDIO_ROOT/../venv/bin/python" server.py "$@"
fi
exec python3 server.py "$@"
