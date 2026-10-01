"""IPv4 wheel download, verified against official PyPI hashes in the existing uv lock."""

import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

root = Path("/mnt/d/codex/coin")
lock = tomllib.loads((root / "uv.lock").read_text())
folder = root / ".cache/wheels"
folder.mkdir(parents=True, exist_ok=True)
paths, receipts = [], []
for name in ("lightgbm", "xgboost-cpu", "narwhals"):
    package = next(item for item in lock["package"] if item["name"] == name)
    wheel = next(item for item in package["wheels"]
                 if "manylinux" in item["url"] and "x86_64" in item["url"]
                 or item["url"].endswith("py3-none-any.whl"))
    if not wheel["url"].startswith("https://files.pythonhosted.org/"):
        raise RuntimeError("Only official PyPI CDN wheel sources allowed")
    path = folder / wheel["url"].rsplit("/", 1)[-1]
    download_url = wheel["url"].replace("https://files.pythonhosted.org/",
                                        "https://pypi.tuna.tsinghua.edu.cn/")
    subprocess.run(["curl", "-4", "--fail", "--location", "--silent", "--show-error",
                    "--max-time", "60", "-o", str(path), download_url], check=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if f"sha256:{digest}" != wheel["hash"] or path.stat().st_size != wheel["size"]:
        raise RuntimeError(f"Official wheel integrity mismatch: {name}")
    paths.append(str(path))
    receipts.append({"name": name, "version": package["version"], "sha256": digest,
                     "size": path.stat().st_size, "source": wheel["url"],
                     "download_mirror": download_url})
    print(json.dumps(receipts[-1]), flush=True)
subprocess.run([str(root / ".tools/bin/uv"), "pip", "install", "--no-deps", *paths], check=True)
(root / "reports/CPU_RESEARCH_DEPENDENCIES.json").write_text(
    json.dumps({"status": "PASS", "cpu_only": True, "gpu_used": False,
                "lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
                "wheels": receipts}, indent=2) + "\n")
