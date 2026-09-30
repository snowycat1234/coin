#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
[[ "${WSL_DISTRO_NAME:-}" == hpc_linux ]] || { echo 'Use D-hosted hpc_linux' >&2; exit 1; }
[[ "$(systemctl --user show coin-quant.slice -p MemoryMax --value)" == 5000000000 ]] || {
  echo 'Shared 5 GB memory limit is not installed' >&2; exit 1;
}
[[ "$(systemctl --user show coin-quant.slice -p MemorySwapMax --value)" == 0 ]] || {
  echo 'Project swap must be disabled' >&2; exit 1;
}
exec systemd-run --user --scope --quiet --slice=coin-quant.slice \
  -p MemorySwapMax=0 "$@"
