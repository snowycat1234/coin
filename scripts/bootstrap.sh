#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
mkdir -p .cache/{tmp,uv,xdg,config,pycache} .tools/bin state logs reports/generated models
bash scripts/install_resource_limits.sh
bash scripts/bounded.sh python3 -m quant.disk --reserve 3000000000
if ! test -x .tools/bin/uv; then
  curl --fail --location --silent --show-error https://astral.sh/uv/0.12.21/install.sh -o .cache/tmp/uv-install.sh
  UV_INSTALL_DIR="$QUANT_ROOT/.tools/bin" UV_NO_MODIFY_PATH=1 sh .cache/tmp/uv-install.sh
fi
bash scripts/bounded.sh uv lock --python /usr/bin/python3
bash scripts/bounded.sh uv sync --locked --python /usr/bin/python3
git init -q
git config core.autocrlf false
uv --version
bash scripts/bounded.sh .venv/bin/python -m quant.disk

