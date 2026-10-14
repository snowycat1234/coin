"""One frozen full-four-year raw CS basket discriminator. Parent GO required.

No native wallet, economic target, covariance scaling, forward labels, fit or
future profitability is evaluated. Do not use this program before final review.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import json
import os
from pathlib import Path
import resource
import shutil
import time
# Mandatory numerical/GPU bounds are established BEFORE NumPy is imported by
# the standalone historical command. Synthetic imports never run history.
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[_name]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import numpy as np
from core import DAY, SYMBOLS, score_at, scheduled_ranks
from bind_sources import HERE, AUTHORITY, calendar, load, sha


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {k:clean(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def independent_basket(scores, ready):
    """Independent Python stable sort, reproducing original float recipe."""
    if not ready or max(scores)-min(scores) <= 1e-12:
        return [0.]*5
    order=sorted(range(5), key=lambda i:scores[i])
    out=[0.]*5
    for i in order[:2]: out[i]=-.15
    for i in order[-2:]: out[i]=.15
    return out


def scope_conclusion(calendar_records, context_records):
    """Opening ownership context is required support, never an extra rank."""
    required=calendar_records+context_records
    missing=[r for r in required if not r['original_admission_cash']
             and r['status']!='READY_PAIRED_BASKETS']
    changed=any(r['paired_basket_changed'] for r in required
                if r['status']=='READY_PAIRED_BASKETS')
    if missing:return 'INCONCLUSIVE_SOURCE_NOT_READY'
    return 'FEATURE_CHANGES_BASKETS_CONDITIONAL' if changed else 'STOP_FUNDING_BASKET_NOOP_ON_ADMITTED_ORIGINAL_SUPPORT_CONDITIONAL'


def independent_check(t, p, mask, streams, d, result):
    """Direct actual-event loops and Decimal binary-Float64-value sums.

    The primary float simple-return and original stable-tie rule stay fixed.
    Independent higher-precision funding sums must reproduce signed baskets;
    any numerical rank disagreement stops, rather than selecting a new recipe.
    """
    k=int(np.searchsorted(t,d)); sums=[]; checked_ids=[]
    for a,s in enumerate(streams):
        ids=[]
        with localcontext() as context:
            context.prec=100
            total=Decimal(0)
            for at,rate in zip(s.times,s.rates):
                if d-22*DAY <= int(at) < d-DAY:
                    ids.append(int(at)); total += Decimal.from_float(float(rate))
            sums.append(float(total))
        proof=result['funding_proof'][a]
        if proof['value'] is not None:
            assert ids == proof['event_ids']
            assert abs(sums[-1]-proof['value']) <= 2e-15*max(1.,abs(sums[-1]))
        checked_ids.append(ids)
    if result['status'] == 'READY_PAIRED_BASKETS':
        price=[float(p[k-1,a])/float(p[k-22,a])-1. for a in range(5)]
        adjusted=[v-f for v,f in zip(price,sums)]
        assert np.allclose(price,result['price_score'],rtol=0.,atol=2e-15)
        assert np.allclose(adjusted,result['funding_adjusted_score'],rtol=0.,atol=2e-15)
        assert independent_basket(price,True) == result['price_only_raw_basket'].tolist()
        assert independent_basket(adjusted,True) == result['funding_adjusted_raw_basket'].tolist(), 'INDEPENDENT_NUMERIC_BASKET_DISAGREEMENT'
        # Causality on actual sources: mutate every unavailable future event,
        # remove all future certificate keys, and perturb future close values.
        from core import EventStream
        prefix=[]
        for s in streams:
            keep=s.times < d-DAY
            cert={q:v for q,v in s.complete_day_event_ids.items() if q < d-DAY}
            prefix.append(EventStream(s.times[keep],s.rates[keep],s.hours[keep],cert,
                          None if s.normalized_hours is None else s.normalized_hours[keep],s.interval_provenance))
        pp=p.copy(); pp[t>d]=np.nan
        causal=score_at(t,pp,mask,prefix,d)
        # Caller supplies the exact existing original mask; no future source
        # data may influence scores/readiness or any signed basket.
        for key in ('price_score','funding_adjusted_score','price_only_raw_basket','funding_adjusted_raw_basket'):
            np.testing.assert_array_equal(causal[key],result[key])
    return {'status':'PASS_DIRECT_DECIMAL_EVENT_SUM_STABLE_BASKET_AND_CAUSAL_PREFIX',
            'decimal_sums_float64':sums,'checked_actual_event_counts':[len(v) for v in checked_ids]}


def guards():
    assert os.environ.get('FUNDING_RANK_OUTER_TIMEOUT_SECONDS') == '120', 'MANDATORY_OUTER_TIMEOUT_WRAPPER_REQUIRED'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000))
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    assert shutil.disk_usage(HERE).free >= 16_106_127_360, 'DISK_RESERVE_STOP'
    mem={line.split(':')[0]:int(line.split()[1])*1024
         for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line and line.split()[1].isdigit()}
    assert mem['SwapTotal'] == 0, 'SWAP_STOP'
    assert mem['MemTotal']-mem['MemAvailable'] <= 8_000_000_000, 'HOST_MEMORY_STOP'


def runtime_guard(begun):
    assert time.monotonic()-begun < 120, 'WALL_TIME_STOP'
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= 2_000_000_000, 'RSS_STOP'


def run(go, output):
    assert not output.exists(), 'Never overwrite an attempted historical pass'
    manifest_raw=(HERE/'FINAL_SOURCE_MANIFEST.json').read_bytes(); manifest=json.loads(manifest_raw)
    permission=json.loads(go.read_bytes())
    assert permission['action'] == 'ONE_FULL_SOURCE_BASKET_ONLY_PASS_2021_2023_2024_2025'
    assert permission['final_manifest_sha256'] == sha(manifest_raw)
    assert permission['funding_scale'] == 'CONDITIONAL_RAW_FRACTION1'
    assert permission['completeness_authority'] == AUTHORITY
    assert permission['wallets'] == permission['fits'] == permission['provider_requests'] == 0
    for name,pin in manifest['files'].items():
        raw=(HERE/name).read_bytes(); assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],name
    # The review receipt is an additive immutable object, not part of its own
    # manifest. Exact parent permission must bind that independent PASS.
    review_raw=(HERE/'FINAL_SOURCE_REVIEW_RECEIPT.json').read_bytes()
    assert sha(review_raw) == permission['review_receipt_sha256']
    review=json.loads(review_raw)
    assert review['status'] == 'PASS_SOURCE_ADMISSION_AND_FROZEN_BASKET_RUNNER_CONDITIONAL'
    assert review['final_manifest_sha256'] == sha(manifest_raw)
    guards(); begun=time.monotonic(); output.mkdir(parents=True)
    (output/'ATTEMPT_START.json').write_text(json.dumps({'action':permission['action'],
        'final_manifest_sha256':sha(manifest_raw),'parent_go_sha256':sha(go.read_bytes()),
        'scope':'One fixed full-four-year raw basket comparison; no wallet, fits or provider requests.'},indent=2)+'\n')
    datasets,_=load(); records=[]; inventories={}
    for year in (2021,2023,2024,2025):
        t,p,mask,streams=datasets[year]; start,end=calendar(year)
        preceding,ranks=scheduled_ranks(start,end)
        # Ownership context is never counted as an extra scored calendar rank.
        clocks=([preceding] if preceding<start else [])+ranks
        year_records=[]; context_records=[]
        for d in clocks:
            runtime_guard(begun)
            result=score_at(t,p,mask,streams,d)
            proof=independent_check(t,p,mask,streams,d,result)
            ready=result['status']=='READY_PAIRED_BASKETS'
            result.update(year=year,role='OWNERSHIP_CONTEXT_ONLY' if d<start else 'SCHEDULED_CALENDAR_RANK',
                          independent=proof,
                          price_rank_order=sorted(range(5),key=lambda i:result['price_score'][i]) if ready else None,
                          funding_rank_order=sorted(range(5),key=lambda i:result['funding_adjusted_score'][i]) if ready else None,
                          original_admission_cash=not all(result['original_ready']))
            records.append(result)
            if d>=start: year_records.append(result)
            else: context_records.append(result)
        ready=[r for r in year_records if r['status']=='READY_PAIRED_BASKETS']
        missing=[r for r in year_records if not r['original_admission_cash'] and r['status']!='READY_PAIRED_BASKETS']
        changes=sum(r['paired_basket_changed'] for r in ready)
        inventories[str(year)]={'scheduled_calendar_ranks':len(ranks),'ownership_context_clock_us':preceding,
            'paired_ready_ranks':len(ready),'original_admission_cash_ranks':sum(r['original_admission_cash'] for r in year_records),
            'required_source_not_ready_ranks':len(missing),'rank_order_changed':sum(r['price_rank_order']!=r['funding_rank_order'] for r in ready),
            'signed_raw_basket_changed':changes,
            'ownership_context_original_active_source_not_ready':sum(not r['original_admission_cash'] and r['status']!='READY_PAIRED_BASKETS' for r in context_records),
            'ownership_context_basket_changed':any(r['paired_basket_changed'] for r in context_records if r['status']=='READY_PAIRED_BASKETS'),
            'price_fully_tied_cash_ranks':sum(np.ptp(r['price_score'])<=1e-12 for r in ready),
            'adjusted_fully_tied_cash_ranks':sum(np.ptp(r['funding_adjusted_score'])<=1e-12 for r in ready),
            'conclusion':scope_conclusion(year_records,context_records)}
    runtime_guard(begun)
    raw=b''.join((json.dumps(clean(r),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode() for r in records)
    assert len(raw)<=10_000_000, 'OUTPUT_BUDGET_STOP'; (output/'RANK_RECORDS.jsonl').write_bytes(raw)
    summary={'status':'COMPLETED_ONE_FIXED_FOUR_YEAR_SOURCE_BASKET_ONLY_PASS',
        'final_manifest_sha256':sha(manifest_raw),'review_receipt_sha256':sha(review_raw),
        'parent_go_sha256':sha(go.read_bytes()),'completeness_authority':AUTHORITY,
        'provider_complete_set_certified':False,'funding_unit_certified':False,
        'historical_publication_time_certified':False,'score_is_exact_funded_PnL':False,
        'years':inventories,'rank_records_sha256':sha(raw),'rank_records_bytes':len(raw),
        'elapsed_seconds':time.monotonic()-begun,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'CPU_threads':1,'historical_passes':1,'wallets':0,'fits':0,'provider_requests':0,
        'interpretation':'Paired same-lag CS raw baskets only. No economic improvement, risk-scaled target identity, CSH or original-wallet identity is established.'}
    (output/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--parent-go',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    try:
        run(args.parent_go,args.output)
    except Exception as error:
        if args.output.exists() and not (args.output/'SUMMARY.json').exists():
            (args.output/'ATTEMPT_FAILURE.json').write_text(json.dumps({'status':'FAILED_ATTEMPT_PRESERVED',
                'error_type':type(error).__name__,'error':str(error),'automatic_retry':False},indent=2)+'\n')
        raise
