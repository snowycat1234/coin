#!/usr/bin/env python3
"""Read-only local integrity and aggregate checks for the OKX44 result package."""
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
    assert result['calendar']['days'] == 44 and result['initial_USDT_each'] == 10000
    for r in result['results']:
        folder = root / 'results' / r['policy']
        summary = json.loads((folder / 'account/summary.json').read_text())
        trades = json.loads((folder / 'account/trades.json').read_text())
        funding = json.loads((folder / 'account/funding.json').read_text())
        econ = json.loads((folder / 'ECONOMICS.json').read_text())
        audit = json.loads((folder / 'INDEPENDENT_AUDIT.json').read_text())
        for a, b in [('net_USDT','net_PnL'),('fees_USDT','fees_USDT'),('execution_cost_USDT','execution_cost_USDT'),('funding_USDT','funding_USDT')]:
            assert r[a] == econ[b] == summary[b], (r['policy'], a)
        assert abs(sum(t['fee_USDT_mid'] for t in trades) - r['fees_USDT']) < 1e-9
        assert abs(sum(t['execution_cost'] for t in trades) - r['execution_cost_USDT']) < 1e-9
        assert abs(sum(f['signed_funding_USDT'] for f in funding) - r['funding_USDT']) < 1e-9
        assert audit['minutes'] == summary['completed_minutes'] == r['full_minutes'] == 63360
        assert r['liquidations'] == summary['liquidation_count'] == 0
        assert r['terminal_flat'] and econ['terminal_flat_proof']['paid_native_closes']
        assert not econ['terminal_flat_proof']['forced_free_fill']
        assert all(v['quantity'] == 0 for v in summary['positions'].values())
        print(r['policy'], 'PASS', 'net_USDT=', r['net_USDT'])
    print('PASS: file hashes and reported journal aggregates. This does not rerun the simulation or certify exchange rules.')

if __name__ == '__main__':
    main()
