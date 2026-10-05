#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
[[ "${WSL_DISTRO_NAME:-}" == hpc_linux ]] || { echo 'Use D-hosted hpc_linux' >&2; exit 1; }
for resource_slice in coin.slice coin-research.slice; do
  [[ "$(systemctl --user show "$resource_slice" -p MemoryMax --value)" == 8000000000 ]] || {
    echo 'Shared 8 GB memory limit is not installed' >&2; exit 1;
  }
  [[ "$(systemctl --user show "$resource_slice" -p MemorySwapMax --value)" == 0 ]] || {
    echo 'Project swap must be disabled' >&2; exit 1;
  }
done
exec systemd-run --user --scope --quiet --slice=coin-research.slice \
  -p MemorySwapMax=0 "$@"
