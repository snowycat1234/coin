import importlib.util
from datetime import date

import pytest

from quant.paths import ROOT

spec = importlib.util.spec_from_file_location(
    "hf_history_tests", ROOT / "scripts/hf_fetch_history.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact180days_and_locked_boundary():
    assert len(module.dates(date(2025, 7, 1), date(2025, 12, 28))) == 180
    with pytest.raises(ValueError, match="Locked"):
        module.dates(date(2025, 7, 1), date(2026, 3, 2))


def test_absent_returns_none_but_partial_refuses(tmp_path):
    assert str(tmp_path).startswith("/home/xflops/coin-state/")
    day = date(2025, 7, 1)
    assert module.resume_day("spot", "BTCUSDT", day, None, store=tmp_path) is None
    folder = tmp_path / "spot/BTCUSDT"
    folder.mkdir(parents=True)
    (folder / "2025-07-01.parquet").write_bytes(b"partial")
    with pytest.raises(ValueError, match="Partial"):
        module.resume_day("spot", "BTCUSDT", day, None, store=tmp_path)


def test_progress_only_replaces_its_owned_receipt(tmp_path):
    path = tmp_path / "progress.json"
    module.publish(path, {"status": "RUNNING", "completed": 1})
    module.publish(path, {"status": "RUNNING", "completed": 2})
    assert '"completed": 2' in path.read_text()
    assert not path.with_suffix(".json.task-tmp").exists()
