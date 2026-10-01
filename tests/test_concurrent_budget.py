from types import SimpleNamespace

import pytest

from quant import concurrent_budget as budget
from quant.collector import CollectorStopped


@pytest.mark.parametrize("kind", ["paper", "collector"])
def test_other_job_growth_uses_global_limit_and_not_local_writer_quota(monkeypatch, kind):
    monkeypatch.setattr(budget, "VHD", SimpleNamespace(
        stat=lambda: SimpleNamespace(st_size=1_200_000_000)))
    if kind == "paper":
        obj = object.__new__(budget.ConcurrentShadowEngine)
        obj.ledger = {"total_bytes": 6_000_000_000}
    else:
        obj = object.__new__(budget.ConcurrentCollector)
        obj._custom_guard = False
        obj._fatal = None
        obj._last_guard = 0
        obj._disk_ledger = {"total_bytes": 6_000_000_000}
        obj.event = lambda *args: None
        def stop(error):
            obj._fatal = str(error)
        obj._disk_stop = stop
    obj._budget_vhd = 1_000_000_000
    obj._budget_db = 0
    obj._database_bytes = lambda: 1024
    check = obj._guard if kind == "paper" else lambda: obj.guard(force=True)
    check()
    if kind == "collector":
        assert obj._disk_snapshot["growth_bytes"] == 200_000_000
        assert obj._disk_snapshot["own_growth_bytes"] == 1024
    # The same independent job growth must still enforce the shared intake cap.
    if kind == "paper":
        obj.ledger["total_bytes"] = 35_800_000_000
    else:
        obj._disk_ledger["total_bytes"] = 35_800_000_000
        obj._last_guard = 0
    with pytest.raises((RuntimeError, CollectorStopped), match="36 GB"):
        check()


def test_own_paper_write_quota_remains_enforced(monkeypatch):
    monkeypatch.setattr(budget, "VHD", SimpleNamespace(
        stat=lambda: SimpleNamespace(st_size=1_000_000_000)))
    obj = object.__new__(budget.ConcurrentShadowEngine)
    obj.ledger = {"total_bytes": 6_000_000_000}
    obj._budget_db, obj._budget_vhd = 0, 1_000_000_000
    obj._database_bytes = lambda: 100_000_000
    with pytest.raises(RuntimeError, match="local 100 MB"):
        obj._guard()
