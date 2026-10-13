"""Invoke the unchanged read-only holding CLI in its own import namespace."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOLDING_SCRIPT = ROOT / 'research/rejected-break-follow-native-20261012/holding.py'

def diagnose_holding(window, account, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    subprocess.run([
        sys.executable, str(HOLDING_SCRIPT), '--window', window,
        '--account', str(account), '--destination', str(destination),
    ], cwd=ROOT, check=True)
