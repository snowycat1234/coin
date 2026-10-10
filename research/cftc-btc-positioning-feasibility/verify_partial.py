"""Check faithful offline reconstruction and a fully excluded requested domain."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def check(saved, rebuilt, receipt):
    a = json.loads((saved / 'RESULT.json').read_text())
    b = json.loads((rebuilt / 'RESULT.json').read_text())
    a.pop('created_UTC')
    b.pop('created_UTC')
    if a != b:
        raise ValueError('Reconstructed decision/source/coverage fields differ')
    original = (saved / 'DAILY_EXCLUSIONS.csv').read_bytes()
    if original != (rebuilt / 'DAILY_EXCLUSIONS.csv').read_bytes():
        raise ValueError('Reconstructed exclusion bytes differ')
    with (saved / 'DAILY_EXCLUSIONS.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 365 + 365 + 365 + 182:
        raise ValueError('Wrong requested daily domain length')
    if rows[0]['decision_UTC'] != '2021-01-01T00:00:00Z' or rows[-1]['decision_UTC'] != '2024-06-30T00:00:00Z':
        raise ValueError('Wrong domain boundaries')
    if len({x['decision_UTC'] for x in rows}) != len(rows):
        raise ValueError('Duplicate decision dates')
    if not all(x['eligible'] == 'False' and x['feature_value'] == '' for x in rows):
        raise ValueError('Unverified input exposed as eligible or synthetic feature')
    for s in a['snapshot_sources']:
        body = (saved / s['path']).read_bytes()
        if len(body) != s['bytes'] or hashlib.sha256(body).hexdigest() != s['SHA256']:
            raise ValueError('Snapshot byte/size binding differs')
    result = dict(status='OFFLINE_PARTIAL_RECONSTRUCTION_VERIFIED',
        comparison='All decision/source/coverage fields equal except generated creation time; exact exclusions equal',
        requested_decision_days=len(rows),eligible=0,nonblank_feature_values=0,
        snapshot_SHA256_bindings_verified=len(a['snapshot_sources']),
        exclusions_SHA256=hashlib.sha256(original).hexdigest(),market_rows_tested=0,
        causality_clock_on_actual_reports='NOT_RUN_NO_VERIFIED_REPORTS_OR_RELEASES')
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saved',type=Path,required=True)
    p.add_argument('--rebuilt',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    args = p.parse_args()
    check(args.saved,args.rebuilt,args.receipt)
