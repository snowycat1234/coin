#!/usr/bin/env bash
set -euo pipefail
set -o noclobber
test -f /home/xflops/coin-state/v8-l1-clock-preservation-20261002-v2/PRESERVATION.json
test "$(sha256sum src/quant/microstructure.py | cut -d ' ' -f 1)" = 649a69c924cdcfc4e85dca37a2a6c4958993f3f3365e04b3f10372f8875ddbb4
exec .venv/bin/python -u -m quant.microstructure --run > /home/xflops/coin-state/v8-l1-clock-preservation-20261002-v2/microstructure-recovery.stdout.log 2> /home/xflops/coin-state/v8-l1-clock-preservation-20261002-v2/microstructure-recovery.stderr.log
