#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
[[ "${WSL_DISTRO_NAME:-}" == hpc_linux ]] || exit 1
mkdir -p /home/xflops/.config/systemd/user
install -m 644 scripts/coin-quant.slice /home/xflops/.config/systemd/user/coin-quant.slice
systemctl --user daemon-reload
systemctl --user start coin-quant.slice
systemctl --user show coin-quant.slice -p MemoryMax -p MemorySwapMax -p ControlGroup
