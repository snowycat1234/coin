"""Cold-restore checks of saved artifacts only; no wallet stepping or RNG draw."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from core import ARMS,YEARS,INPUT_HASHES,read_npz,sha256,calendar
from score import (HERE,ROOT,OLD_SCORE,OLD_SCORE_SHA256,REFERENCE,REFERENCE_SHA256,
                   ECONOMICS,ECONOMICS_SHA256,RISK,RISK_SHA256,load_module,
                   verify_target,paired_ci,SEEDS,CAPITAL,COST,PROTOCOL_SHA256)
from prepare_targets import check_execution_inputs


def run(inputs_dir):
    manifest=json.loads((HERE/'TARGETS_MANIFEST.json').read_text())
    publication=json.loads((HERE/'PUBLICATION_RECORD.json').read_text())
    output=json.loads((HERE/'results/RESULTS.json').read_text())
    files=json.loads((HERE/'results/OUTPUTS_MANIFEST.json').read_text())
    assert output['protocol_SHA256']==PROTOCOL_SHA256==manifest['protocol_SHA256']
    assert output['published_commit']==publication['commit_sha']==files['published_commit']
    assert output['publication_record_SHA256']==sha256(HERE/'PUBLICATION_RECORD.json')==files['publication_record_SHA256']
    assert files['status']=='SCORED_FROZEN_THREE_ARMS_TWO_YEARS'
    for name,expected in files['files'].items():
        assert sha256(HERE/'results'/name)==expected,(name,'saved artifact SHA differs')
    for name,expected in manifest['target_files'].items():
        assert sha256(HERE/name)==expected,(name,'saved target SHA differs')
    for path,expected in ((OLD_SCORE,OLD_SCORE_SHA256),(REFERENCE,REFERENCE_SHA256),(ECONOMICS,ECONOMICS_SHA256),(RISK,RISK_SHA256)):
        assert sha256(path)==expected,(path,'dependency SHA differs')
    audit_module=load_module('saved_only_decimal_audit',OLD_SCORE)
    checks=0
    for year in YEARS:
        execution=check_execution_inputs(Path(inputs_dir)/f'Y{year}.npz',year)
        targets=verify_target(HERE/'targets'/f'Y{year}.npz',year)
        assert sha256(Path(inputs_dir)/f'Y{year}.npz')==INPUT_HASHES[year]
        assert np.array_equal(execution['decision_us'],targets['decision_us'])==True
        yr=output['years'][str(year)]
        daily={}
        for arm in ARMS:
            saved=yr['arms'][arm]
            p=HERE/'results'/saved['quantity_rows_file']
            assert sha256(p)==saved['quantity_rows_SHA256']
            rows=json.loads(p.read_text())
            assert len(rows)==365
            m=saved['metrics']
            assert m['days']==365 and m['hypothetical_cost_terminal'] and all(v==0 for v in m['positions'])
            assert m['net_USDT']==rows[-1]['nav_after']-CAPITAL
            assert abs(m['trading_cost']-sum(row['trading_cost_proxy'] for row in rows))<1e-10
            assert abs(m['funding_cash']+sum(row['funding_debit_proxy'] for row in rows))<1e-10
            audit=audit_module.decimal_audit(execution['decision_us'],targets[arm],execution['p0'],execution['p1'],execution['funding_per_unit'],m,rows)
            assert audit==saved['decimal_audit'] and audit['passed'],(year,arm,audit.get('errors'))
            daily[arm]=np.asarray([r['daily_return'] for r in rows])
            checks+=1
        bpath=HERE/'results'/yr['bootstrap_file']
        assert sha256(bpath)==yr['bootstrap_SHA256']
        b=read_npz(bpath);idx=b['indices']
        assert idx.shape==(1000,365) and np.issubdtype(idx.dtype,np.integer) and idx.min()>=0 and idx.max()<365
        assert np.array_equal(b['COMBINED_minus_STATIC50'],(daily['COMBINED']-daily['STATIC50'])[idx].mean(axis=1))
        assert np.array_equal(b['COMBINED_minus_SMA200'],(daily['COMBINED']-daily['SMA200'])[idx].mean(axis=1))
        assert paired_ci(daily,idx)==yr['inference']
        split=.5*(yr['arms']['STATIC50']['metrics']['net_USDT']+yr['arms']['SMA200']['metrics']['net_USDT'])/CAPITAL
        rebalance=float(np.prod(1+.5*(daily['STATIC50']+daily['SMA200']))-1)
        assert abs(split-yr['benchmarks']['initial_split_arithmetic_mean_cumulative_net_return'])<1e-14
        assert abs(rebalance-yr['benchmarks']['daily_50_50_rebalanced_compounded_net_return'])<1e-14
    assert checks==6
    assert output['all_frozen_quality_gates_pass']==all(output['quality_gates'].values())
    return dict(status='PASS_COLD_RESTORE_SAVED_ARTIFACTS_ONLY',decimal_audits=checks,
                paired_bootstrap_replays=2,independent_wallet_or_rng_runs=0,
                results_SHA256=sha256(HERE/'results/RESULTS.json'),
                original_external_execution_input_hashes={str(y):INPUT_HASHES[y] for y in YEARS})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-inputs',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(run(args.execution_inputs),sort_keys=True))
