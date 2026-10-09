#!/usr/bin/env python3
"""Read-only local integrity and aggregate checks for the OKX41 result package."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    root = p.parse_args().root.resolve()
    manifest = json.loads((root / 'MANIFEST.json').read_text())
    for f in manifest['files']:
        data = (root / f['path']).read_bytes()
        assert len(data) == f['bytes'], f['path']
        assert hashlib.sha256(data).hexdigest() == f['public_sha256'], f['path']
    result = json.loads((root / 'results/RESULTS.json').read_text())
    assert result['calendar']['days'] == 41 and result['fresh_accounts_not_stitched']
    for policy, r in result['wallets'].items():
        folder = root / 'results' / policy
        summary = json.loads((folder / 'account/summary.json').read_text())
        trades = json.loads((folder / 'account/trades.json').read_text())
        funding = json.loads((folder / 'account/funding.json').read_text())
        econ = json.loads((folder / 'ECONOMICS.json').read_text())
        audit = json.loads((folder / 'INDEPENDENT_AUDIT.json').read_text())
        assert r['daily_metrics']['initial_nav'] == 10000
        for k in ('net_PnL','fees_USDT','execution_cost_USDT','funding_USDT'):
            assert r[k] == econ[k] == summary[k], (policy, k)
        assert r['MDD'] == econ['MDD'] == summary['minute_max_drawdown']
        assert abs(sum(t['fee_USDT_mid'] for t in trades) - r['fees_USDT']) < 1e-9
        assert abs(sum(t['execution_cost'] for t in trades) - r['execution_cost_USDT']) < 1e-9
        assert abs(sum(f['signed_funding_USDT'] for f in funding) - r['funding_USDT']) < 1e-9
        assert audit['minutes'] == summary['completed_minutes'] == r['completed_minutes'] == 59040
        assert r['liquidations'] == summary['liquidation_count'] == 0
        assert r['terminal_cash_realized'] and econ['terminal_flat_proof']['paid_native_closes']
        assert not econ['terminal_flat_proof']['forced_free_fill']
        assert all(v['quantity'] == 0 for v in summary['positions'].values())
        assert len(funding) == 615 and all(f['signed_funding_USDT'] == 0 for f in funding[:5])
        print(policy, 'PASS', 'net_USDT=', r['net_PnL'])
    print('PASS: file hashes and reported journal aggregates; no full simulation replay or exchange-rule certification.')

if __name__ == '__main__':
    main()
