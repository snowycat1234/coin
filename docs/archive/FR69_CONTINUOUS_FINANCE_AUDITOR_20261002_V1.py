"""Reuse accepted financial arithmetic on nine actual continuous-replay ledgers."""
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
import resource
import time

import polars as pl

ROOT = Path('/mnt/d/codex/coin')
RUN = Path('/home/xflops/coin-state/fr69-continuous-30d-diagnostic-20261002-v2')
original = ROOT / 'docs/archive/FR_ROLLING00_FINANCE_AUDITOR_20261002_V1.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(original) == '12356a6b1e522edb02417b7f1d19c984079dc36cf0339de1dadd69f44a8657f8'
# Reuse the exact accepted imports/constants/functions; its CLI tail is not executed.
prefix = original.read_text().split('parser = argparse.ArgumentParser()', 1)[0]
ns = {'__name__': 'accepted_closed_ledger_arithmetic', '__file__': str(original)}
exec(compile(prefix, str(original), 'exec'), ns)
scenario, close = ns['scenario'], ns['close']
started = time.monotonic()
binding = json.loads((RUN / 'RUN_BINDING.json').read_text())
binding_sha = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
completed = json.loads((RUN / 'CONTINUOUS_REPLAY_COMPLETE.json').read_text())
assert completed['status'] == 'FR69_CONTINUOUS_REPLAY_COMPLETE'
assert completed['binding_sha256'] == binding_sha
assert completed['history_days'] == 30 and not completed['nav_reset_inside_oos']
models, files = {}, {}
for config in ('RIDGE-1', 'RIVER-1', 'XGB-S'):
    receipt_path = RUN / config / 'COMPLETE.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'COMPLETE_CONTINUOUS_REPLAY'
    assert receipt['binding_sha256'] == binding_sha
    assert completed['completion_receipt_sha256'][config] == sha(receipt_path)
    files[str(receipt_path)] = sha(receipt_path)
    results = {}
    for spread in (2, 4, 8):
        actual = {}
        for kind in ('daily', 'trades'):
            rel = next(p for p in receipt['artifacts'] if p.endswith(f'/{kind}-{spread}.parquet'))
            path = RUN / rel
            assert sha(path) == receipt['artifacts'][rel]
            files[str(path)] = sha(path)
            actual[kind] = pl.read_parquet(path).to_dicts()
        assert len(actual['daily']) == 14
        summary = receipt['evaluation']['economics'][str(spread)]
        result = scenario(actual['trades'], actual['daily'], summary, spread)
        navs = [10000.] + [row['nav'] for row in actual['daily']]
        high, mdd = navs[0], 0.
        for nav in navs[1:]:
            high = max(high, nav)
            mdd = max(mdd, 1 - nav / high)
        close(summary['max_drawdown'], mdd, 'previous-peak drawdown', 1e-10)
        # One actual cash/position path spans the 07-22 boundary; no week reset.
        result.update(days=14, independently_recomputed_max_drawdown=mdd,
                      continuous_daily_initial_nav=10000., week_reset_applied=False)
        results[str(spread)] = result
    models[config] = results
output = {'status': 'FR69_CONTINUOUS_ACTUAL_FINANCE_ARITHMETIC_VERIFIED',
          'created_utc': datetime.now(UTC).isoformat(), 'binding_sha256': binding_sha,
          'models_checked': 3, 'cost_scenarios': 9, 'models': models,
          'actual_financial_file_hashes': files,
          'accepted_arithmetic_original_sha256': sha(original),
          'arithmetic_prefix_sha256': hashlib.sha256(prefix.encode()).hexdigest(),
          'auditor_sha256': sha(Path(__file__)),
          'elapsed_seconds': time.monotonic() - started,
          'auditor_peak_RAM_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
          'fits': 0, 'formal_six_fold_complete': False, 'candidate_qualification': False,
          'scope': 'Exact accepted financial function reused; actual nine ledgers, continuous cash/position path, fee/spread/slippage/NAV/turnover/MDD; no model or evaluator refit.'}
with (RUN / 'ROOT_CONTINUOUS_FINANCE_ARITHMETIC_V1.json').open('x') as stream:
    json.dump(output, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps({key: output[key] for key in ('status', 'models_checked', 'cost_scenarios', 'auditor_peak_RAM_bytes')}))
