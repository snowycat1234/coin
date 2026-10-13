"""Import isolation and failure propagation, no financial simulator or account."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_holding as reporting

def test_child_uses_own_driver_despite_conflicting_pythonpath(tmp_path, monkeypatch):
    legacy = tmp_path / 'legacy'; legacy.mkdir()
    conflict = tmp_path / 'conflict'; conflict.mkdir()
    (legacy / 'driver.py').write_text("MARKER = 'correct_legacy_driver'\n")
    (conflict / 'driver.py').write_text("raise RuntimeError('wrong_driver_import')\n")
    script = legacy / 'holding.py'
    script.write_text("import argparse,json\nfrom pathlib import Path\nfrom driver import MARKER\np=argparse.ArgumentParser()\np.add_argument('--window');p.add_argument('--account');p.add_argument('--destination')\na=p.parse_args()\nPath(a.destination).write_text(json.dumps(dict(marker=MARKER,window=a.window,account=a.account)))\n")
    monkeypatch.setattr(reporting, 'HOLDING_SCRIPT', script)
    monkeypatch.setenv('PYTHONPATH', str(conflict))
    account = tmp_path / 'account with spaces'
    destination = tmp_path / 'report with spaces.json'
    reporting.diagnose_holding('Y2023', account, destination)
    assert json.loads(destination.read_text()) == dict(marker='correct_legacy_driver', window='Y2023', account=str(account))

def test_child_failure_propagates_and_existing_report_is_preserved(tmp_path, monkeypatch):
    script = tmp_path / 'failed_holding.py'; script.write_text('raise SystemExit(7)\n')
    monkeypatch.setattr(reporting, 'HOLDING_SCRIPT', script)
    destination = tmp_path / 'report.json'
    with pytest.raises(subprocess.CalledProcessError) as error:
        reporting.diagnose_holding('Y2023', tmp_path / 'account', destination)
    assert error.value.returncode == 7 and not destination.exists()
    destination.write_text('existing evidence')
    with pytest.raises(FileExistsError):
        reporting.diagnose_holding('Y2023', tmp_path / 'account', destination)
    assert destination.read_text() == 'existing evidence'
