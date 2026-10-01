import asyncio
import tempfile
from decimal import Decimal
from pathlib import Path

from quant.acceptance import run_execution_acceptance
from quant.paths import STATE


def test_real_signed_adapter_timeout_lookup_fill_recovery():
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="execution-integration-", dir=STATE) as folder:
        result = asyncio.run(run_execution_acceptance(
            Path(folder) / "execution.sqlite3", disk_check=lambda **kwargs: {"status": "OK"},
        ))
        assert result["status"] == "OFFLINE_ENGINEERING_PASS"
        assert result["real_testnet_days"] == 0 and result["exchange_orders"] == 0
        assert result["http_mock_mutations"] == 1
        assert result["network_enabled"] is False
        assert Decimal(result["final"]["balances"]["USDT"]) == Decimal("9949.95")
