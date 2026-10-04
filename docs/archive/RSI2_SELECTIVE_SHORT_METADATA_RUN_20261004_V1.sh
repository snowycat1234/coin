#!/usr/bin/env bash
set -euo pipefail
# Invoke only inside the accepted progress/bounded wrapper; no Python or payload IO.
: "${COIN_TASK_ID:?Actual bounded metadata task identity required}"
exec /mnt/c/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe \
  -NoProfile -NonInteractive -File D:/codex/coin/.cache/d059_metadata.ps1 \
  "$@" -MetadataTaskId "$COIN_TASK_ID"
