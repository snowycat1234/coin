"""Publication- and parent-go-gated conditional daily proxy for saved half-mix."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import numpy as np

for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[variable]='1'
from core import (ARMS, YEARS, SYMBOLS, INPUT_HASHES, calendar, read_npz,
                  save_npz, sha256, write_json, check_weights)
from prepare_targets import check_execution_inputs, PROTOCOL_SHA256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD_SCORE=ROOT/'research/cs-sma-agreement-20261013/score.py'
REFERENCE=ROOT/'research/settled-funding-direction-20261012/core.py'
OLD_SCORE_SHA256='1e0198a7998bdc53309efe54ac0d71fd456e543d8c894e6b2fde7f31bfa5e2f2'
REFERENCE_SHA256='e536049425dd404fac155d9fc757e5ee82199d88e3733ca49216c40a29253245'
ECONOMICS=ROOT/'modules/collector_research/pipeline/economics.py'
ECONOMICS_SHA256='637441050d0d42bc1a579510272b3fa5f456620dbfb8b45932cc37e894e34a3e'
RISK=ROOT/'research/portfolio-risk-budget-20261012/risk_budget.py'
RISK_SHA256='69de58ac83536dfbf1ec3715aadfa65da741c970c4cb5b417bb4c1e8062b19a6'
SEEDS={2023:811762,2025:811763}
COST=.00135
CAPITAL=10000.


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_publication(path):
    r=json.loads(Path(path).read_text())
    if (r.get('repository')!='snowycat1234/coin' or
        r.get('branch')!='research/static50-sma-half-proxy-20261013' or
        r.get('remote_verified') is not True or
        not re.fullmatch(r'[0-9a-f]{40}',r.get('commit_sha',''))):
        raise ValueError('Parent-verified exact remote publication is required')
    manifest=json.loads((HERE/'TARGETS_MANIFEST.json').read_text())
    if manifest['protocol_SHA256']!=PROTOCOL_SHA256 or sha256(HERE/'PROTOCOL.json')!=PROTOCOL_SHA256 or manifest['economic_runs_started'] is not False:
        raise ValueError('Frozen prescore protocol/manifest mismatch')
    if any(sha256(path)!=expected for path,expected in ((OLD_SCORE,OLD_SCORE_SHA256),(REFERENCE,REFERENCE_SHA256),(ECONOMICS,ECONOMICS_SHA256),(RISK,RISK_SHA256))):
        raise ValueError('Unchanged Decimal audit, economic kernel, reference, or risk identity mismatch')
    qa=json.loads((HERE/'QA.json').read_text())
    if (qa.get('status')!='PASS_FROZEN_TARGETS_NO_ECONOMIC_SCORING' or qa.get('economic_runs_started') is not False
            or qa.get('synthetic_tests_run')!=10 or qa.get('failures')!=0 or qa.get('errors')!=0):
        raise ValueError('Prescore QA certification mismatch')
    required=[HERE/name for name in ('PROTOCOL.json','core.py','test_core.py','test_accounting.py','prepare_targets.py','TARGETS_MANIFEST.json','QA.json','score.py')]
    required += [HERE/'targets'/f'Y{year}{suffix}' for year in YEARS for suffix in ('.npz','_PROOF.json')]
    required += [OLD_SCORE,REFERENCE,ECONOMICS,RISK]
    for file in required:
        key=file.relative_to(ROOT).as_posix()
        if r.get('files',{}).get(key)!=sha256(file):
            raise ValueError('Remote publication hash missing/mismatched: '+key)
    for key,value in manifest['target_files'].items():
        if sha256(HERE/key)!=value: raise ValueError('Frozen saved target changed: '+key)
    return r,manifest


def verify_target(path,year):
    t=read_npz(path)
    if set(t)!=set(('decision_us','symbol_order','annual_covariance')+ARMS):
        raise ValueError('Saved target schema differs')
    if not np.array_equal(t['decision_us'],calendar(year)) or tuple(t['symbol_order'])!=SYMBOLS:
        raise ValueError('Full aligned target calendar/order required')
    for arm in ARMS: check_weights(t[arm])
    if not np.array_equal(t['COMBINED'],.5*t['STATIC50']+.5*t['SMA200']):
        raise ValueError('Saved target is not exact half-sum')
    c=t['annual_covariance']
    if c.shape!=(365,5,5) or not np.isfinite(c).all() or not np.allclose(c,c.transpose(0,2,1),rtol=0,atol=1e-12) or np.linalg.eigvalsh(c).min() < -1e-10:
        raise ValueError('Saved covariance not finite symmetric PSD')
    return t


def exposure(weights,covariance):
    w=np.asarray(weights)
    gross=np.abs(w).sum(axis=1)
    sig=np.sqrt(np.maximum(0,np.einsum('ni,nij,nj->n',w,covariance,w)))
    return dict(mean_gross=float(gross.mean()),max_gross=float(gross.max()),
                max_asset_abs_weight=float(np.abs(w).max()),cash_days=int(np.count_nonzero(gross==0)),
                mean_estimated_annual_sigma=float(sig.mean()),max_estimated_annual_sigma=float(sig.max()),
                mean_long=float(np.maximum(w,0).sum(axis=1).mean()),
                mean_short=float(-np.minimum(w,0).sum(axis=1).mean()))


def paired_ci(daily,indices):
    results={}
    for control in ('STATIC50','SMA200'):
        delta=daily['COMBINED']-daily[control]
        samples=delta[indices].mean(axis=1)
        lo,hi=np.quantile(samples,[.025,.975])
        results[control]=dict(mean_daily_return_increment=float(delta.mean()),
                              paired_mean_daily_return_95pct_CI=[float(lo),float(hi)],
                              CI_lower_positive=bool(lo>0))
    return results


def run(publication_record,execution_inputs,output_dir,*,parent_go=False):
    if parent_go is not True: raise ValueError('Explicit parent go is required before economics')
    publication,manifest=verify_publication(publication_record)
    old=load_module('frozen_cs_sma_score',OLD_SCORE)
    reference=old.reference
    out=Path(output_dir)
    if out.exists() and any(out.iterdir()): raise ValueError('Refuse to overwrite scored artifacts')
    # Validate both complete years before first economic reference call.
    prepared={}
    for year in YEARS:
        x=check_execution_inputs(Path(execution_inputs)/f'Y{year}.npz',year)
        t=verify_target(HERE/'targets'/f'Y{year}.npz',year)
        proof=json.loads((HERE/'targets'/f'Y{year}_PROOF.json').read_text())
        if proof.get('days')!=365 or len(proof.get('rows',[]))!=365 or not proof.get('mix_exact') or not proof.get('no_post_mix_rescale'):
            raise ValueError('Saved target proof incomplete')
        prepared[year]=(x,t,proof)
    out.mkdir(parents=True,exist_ok=True)
    result=dict(experiment='static50-sma-half-proxy-20261013',
                status='CONDITIONAL_SAVED_HISTORICAL_PROXY',
                published_commit=publication['commit_sha'],
                protocol_SHA256=PROTOCOL_SHA256,
                publication_record_SHA256=sha256(publication_record),
                target_manifest_SHA256=sha256(HERE/'TARGETS_MANIFEST.json'),
                original_source_hashes=manifest['original_source_hashes'],
                execution_input_hashes=manifest['execution_input_hashes'],
                economic_model='UNCHANGED_DAILY_QUANTITY_REFERENCE',
                per_side_cost_rate=COST,capital_per_independent_wallet_USDT=CAPITAL,
                caveats=['Known development years, not pristine out-of-sample or holdout',
                         'Conditional proxy only: no native account, margin, liquidation, capacity, minQty, or fills',
                         'Paired CIs are conditional and not research-selection-adjusted',
                         'Quality gates do not authorize deployment'],
                bootstrap=dict(draws=1000,block_calendar_days=14,seeds={str(k):v for k,v in SEEDS.items()},shared_paired_dates=True),
                years={})
    artifacts={}
    all_paid=True;all_audited=True;all_positive=True;all_dd=True
    for year in YEARS:
        x,t,proof=prepared[year]
        yearout=dict(arms={},comparisons={},benchmarks={},inference=None)
        daily={}
        for arm in ARMS:
            metric,rows=reference(x['decision_us'],t[arm],x['p0'],x['p1'],x['funding_per_unit'],x['owned_interval_valid'])
            rowpath=out/f'Y{year}_{arm}_ROWS.json'
            write_json(rowpath,rows)
            saved=json.loads(rowpath.read_text())
            audit=old.decimal_audit(x['decision_us'],t[arm],x['p0'],x['p1'],x['funding_per_unit'],metric,saved)
            metric['cumulative_net_return']=metric['net_USDT']/CAPITAL if metric['net_USDT'] is not None else None
            metric['rebalance_turnover_USDT']=sum(r['turnover_USDT'] for r in saved)
            metric['terminal_turnover_USDT']=metric['terminal_cost_proxy_USDT']/COST
            metric['total_turnover_USDT']=metric['rebalance_turnover_USDT']+metric['terminal_turnover_USDT']
            yearout['arms'][arm]=dict(metrics=metric,decimal_audit=audit,
                                      exposure=exposure(t[arm],t['annual_covariance']),
                                      quantity_rows_file=rowpath.name,quantity_rows_SHA256=sha256(rowpath))
            artifacts[rowpath.name]=sha256(rowpath)
            paid=len(saved)==365 and metric['hypothetical_cost_terminal'] and metric['days']==365
            all_paid &= bool(paid)
            all_audited &= bool(audit['passed'])
            if paid:
                daily[arm]=np.array([r['daily_return'] for r in saved],dtype=np.float64)
        combo=yearout['arms']['COMBINED']['metrics']
        all_positive &= combo['net_USDT'] is not None and combo['net_USDT']>0
        all_dd &= combo['drawdown']<=.12
        c=yearout['arms']
        for control in ('STATIC50','SMA200'):
            m=c[control]['metrics']
            yearout['comparisons'][control]=dict(
                combined_minus_control_net_USDT=(combo['net_USDT']-m['net_USDT']) if combo['net_USDT'] is not None and m['net_USDT'] is not None else None,
                combined_minus_control_drawdown=combo['drawdown']-m['drawdown'],
                combined_minus_control_annual_vol=combo['annual_vol']-m['annual_vol'] if combo['annual_vol'] is not None and m['annual_vol'] is not None else None,
                combined_minus_control_mean_gross=c['COMBINED']['exposure']['mean_gross']-c[control]['exposure']['mean_gross'])
        if len(daily)==3:
            indices=old.bootstrap_indices(365,SEEDS[year])
            inference=paired_ci(daily,indices)
            bpath=out/f'Y{year}_BOOTSTRAP.npz'
            save_npz(bpath,indices=indices,
                     COMBINED_minus_STATIC50=(daily['COMBINED']-daily['STATIC50'])[indices].mean(axis=1),
                     COMBINED_minus_SMA200=(daily['COMBINED']-daily['SMA200'])[indices].mean(axis=1))
            b=read_npz(bpath)
            if not np.array_equal(b['indices'],indices) or paired_ci(daily,b['indices'])!=inference:
                raise ValueError('Persisted paired samples fail replay')
            yearout['inference']=inference
            yearout['bootstrap_file']=bpath.name;yearout['bootstrap_SHA256']=sha256(bpath)
            artifacts[bpath.name]=sha256(bpath)
            # Two distinct paper benchmarks, neither substitutes for the shared-wallet mix.
            initial_split_return=.5*(c['STATIC50']['metrics']['cumulative_net_return']+c['SMA200']['metrics']['cumulative_net_return'])
            daily_rebalanced_returns=.5*daily['STATIC50']+.5*daily['SMA200']
            daily_rebalanced_return=float(np.prod(1+daily_rebalanced_returns)-1)
            yearout['benchmarks']=dict(initial_split_arithmetic_mean_cumulative_net_return=float(initial_split_return),
                                       daily_50_50_rebalanced_compounded_net_return=daily_rebalanced_return,
                                       method='Control-wallet arithmetic / daily return paper benchmark; no extra shared execution or transaction fees charged')
        yearout['mix_target_diagnostics']=dict(
            exact_half_sum=True,no_post_mix_risk_scale=True,
            mean_signed_cancellation_gross=float(np.mean([row['signed_cancellation_gross'] for row in proof['rows']])),
            full_cash_days=int(sum(row['mix_cash'] for row in proof['rows'])),
            annual_sigma_triangle_all_days=bool(all(row['mix_annual_sigma']<=.5*(row['static_annual_sigma']+row['sma_annual_sigma'])+1e-10 for row in proof['rows'])))
        result['years'][str(year)]=yearout
    result['quality_gates']=dict(source_identity_and_full_calendars=True,
                                 complete_paid_proxy_terminal_both_years=bool(all_paid),
                                 independent_Decimal_audit_all_arms_both_years=bool(all_audited),
                                 combined_net_positive_both_years=bool(all_positive),
                                 combined_max_drawdown_le_12pct_both_years=bool(all_dd))
    result['all_frozen_quality_gates_pass']=all(result['quality_gates'].values())
    result['comparison_not_quality_gate']='No required win over both components, no alpha claim from lower gross, no deployment approval.'
    resultpath=out/'RESULTS.json';write_json(resultpath,result);artifacts[resultpath.name]=sha256(resultpath)
    write_json(out/'OUTPUTS_MANIFEST.json',dict(status='SCORED_FROZEN_THREE_ARMS_TWO_YEARS',
               files=artifacts,protocol_SHA256=PROTOCOL_SHA256,published_commit=publication['commit_sha'],
               publication_record_SHA256=result['publication_record_SHA256']))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--publication-record',type=Path,required=True)
    p.add_argument('--execution-inputs',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,default=HERE/'results')
    p.add_argument('--parent-go',action='store_true',help='Affirms parent explicit post-publication authorization')
    args=p.parse_args()
    result=run(args.publication_record,args.execution_inputs,args.output_dir,parent_go=args.parent_go)
    print(json.dumps(dict(quality_gates=result['quality_gates'],all_pass=result['all_frozen_quality_gates_pass']),sort_keys=True))
