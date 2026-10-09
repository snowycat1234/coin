"""Import the unchanged native scheduler for synthetic contract tests only."""

from pathlib import Path

from modules.temporal_two_expert.exact import sha

NATIVE_SHA256 = "36c74d0bca4a3d556cf87aae223a8df06340f322652edcca192b363788875f6d"


def native_methods():
    source = Path(__file__).resolve().parents[2] / "scripts/investment/resumable_perpetual.py"
    if sha(source) != NATIVE_SHA256:
        raise ValueError("Frozen native scheduler source changed")
    from scripts.investment.resumable_perpetual import NativeDailySimulator

    if sha(source) != NATIVE_SHA256:
        raise ValueError("Frozen native scheduler source changed during import")
    return NativeDailySimulator
