#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
[[ "${WSL_DISTRO_NAME:-}" == hpc_linux ]] || exit 1
mkdir -p /home/xflops/.config/systemd/user
install -m 644 scripts/coin-quant.slice /home/xflops/.config/systemd/user/coin-quant.slice
install -m 644 scripts/coin.slice /home/xflops/.config/systemd/user/coin.slice
install -m 644 scripts/coin-research.slice /home/xflops/.config/systemd/user/coin-research.slice
systemctl --user daemon-reload
systemctl --user start coin.slice coin-quant.slice coin-research.slice
systemctl --user set-property --runtime coin.slice MemoryMax=8000000000 MemorySwapMax=0
systemctl --user set-property --runtime coin-research.slice MemoryMax=8000000000 MemorySwapMax=0
systemctl --user show coin.slice coin-quant.slice coin-research.slice -p MemoryMax -p MemorySwapMax -p ControlGroup
