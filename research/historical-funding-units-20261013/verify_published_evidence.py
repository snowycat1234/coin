"""Stdlib-only published-byte and fixed-tape arithmetic verification.

This checks the published audit receipts, not original raw rows or full journals.
Those are separately SHA-bound but are not duplicated in this publication.
"""
import hashlib,json
from decimal import Decimal,localcontext
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    manifest=json.loads((HERE/'SHA256_MANIFEST.json').read_text())
    for row in manifest['files']:
        p=HERE/row['file'];raw=p.read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['SHA256'],row['file']
    sources=json.loads((HERE/'SOURCE_IDENTITIES.json').read_text())
    rows=sources['official_raw_members']
    assert len(rows)==90 and sum(r['raw_rows'] for r in rows)==8235
    assert len({(r['year'],r['month'],r['symbol']) for r in rows})==90
    assert all(r['raw_rows']==r['prepared_float_exact_matches']==r['prepared_decimal_exact_matches'] for r in rows)
    assert sum(r['raw_rows'] for r in rows if r['year']==2024)==2760
    assert sum(r['raw_rows'] for r in rows if r['year']==2025)==5475
    assert all(r['consumer_parquet_float_exact_matches']==r['raw_rows'] for r in rows if r['year']==2025)
    claim=sources['source_matches']['official_raw_matches']
    assert claim['source_rate_scale_transformation']==1 and claim['economic_rate_unit_certified'] is False
    fee=json.loads((HERE/'FIXED_TAPE_FUNDING_AUDIT.json').read_text())
    with localcontext() as ctx:
        ctx.prec=60
        for c in fee['cases']:
            f=Decimal(c['recorded_signed_funding_cash_USDT']);net=Decimal(c['recorded_net_USDT'])
            delta=(Decimal('.01')-1)*f
            assert delta==Decimal(c['fixed_tape_scale_point01_minus_scale1_cash_USDT'])
            assert net+delta==Decimal(c['fixed_tape_same_quantities_scale_point01_net_USDT'])
            assert c['duplicate_event_ids']==0 and c['source_rate_exact_matches']==c['events']
            assert c['all_owned_rate_fraction_equals_raw_numeric']
            assert c['actual_strategy_counterfactual_return'].startswith('NOT_COMPUTED_OR_BOUNDED')
    branch_rows=(HERE/'BRANCH_HEADS_20261013_1610.txt').read_text().splitlines()
    assert len(branch_rows)==91
    print(json.dumps(dict(status='PASS_PUBLISHED_BYTES_AND_RECEIPT_ARITHMETIC_ONLY',files=len(manifest['files']),original_raw_identity_receipt_events=8235,fixed_tape_cases=len(fee['cases']),branch_snapshot_lines=91,new_provider_requests=0,new_wallets=0,new_fits=0,full_original_row_or_wallet_replay=False),sort_keys=True))
if __name__=='__main__':main()
