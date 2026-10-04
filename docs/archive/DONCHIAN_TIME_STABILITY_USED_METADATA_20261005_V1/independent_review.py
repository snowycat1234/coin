"""Independent scalar/Decimal review of saved daily NAV, no market/account replay."""
from pathlib import Path
from datetime import UTC,datetime,timedelta,date
from decimal import Decimal,localcontext
import hashlib,json,math,os,resource,time
import numpy as np
import polars as pl
from quant import resources
from quant.metrics import block_bootstrap_mean_ci
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
OUT=STATE/'d068-time-stability-independent-20261005-v1'
REPORT=ROOT/'reports/DONCHIAN_TIME_STABILITY_INDEPENDENT_REVIEW_20261005_V1.md'
PROTOCOL=ROOT/'protocols/DONCHIAN_TIME_STABILITY_20261005_V1.json'
RESULT=ROOT/'reports/fast_research/DONCHIAN_TIME_STABILITY_20261005_V1.json'
start=time.monotonic()
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def D(value):return Decimal.from_float(value) if isinstance(value,float) else Decimal(str(value))
errors={}
def same(kind,computed,reported,tolerance):
    error=abs(float(computed)-float(reported));errors[kind]=max(errors.get(kind,0.),error)
    assert error<=tolerance,(kind,computed,reported,error)
assert sha(PROTOCOL)=='2eab7066727257284ef7cce2b66e2e97a5b98b7bc5feb6f9144555e744aeda14'
protocol=json.loads(PROTOCOL.read_text());result=json.loads(RESULT.read_text())
assert result['protocol_sha256']==sha(PROTOCOL) and result['status']=='COMPLETE_SAVED_PAIR_TIME_DIAGNOSTIC_POST_SELECTION_NOT_APR'
assert protocol['fixed_tranche_indices']==[[0,101],[101,202],[202,303]] and protocol['primary_block_days']==60
assert protocol['blocks_days']==[7,30,60] and protocol['samples_per_case_per_block']==2000 and protocol['seed']==20261005
source_task=json.loads((STATE/'task-progress'/('task-'+result['task_id']+'.json')).read_text());assert source_task['status']=='completed' and source_task['exit_code']==0
accounts=[]
for role in ('baseline_report','challenger_report'):
    ref=protocol[role];assert sha(ref['path'])==ref['sha256'];accounts.append(json.loads(Path(ref['path']).read_text()))
origin=datetime(2024,9,1,tzinfo=UTC);dates=[origin.date()+timedelta(days=i) for i in range(303)]
expected=[int((origin+timedelta(days=i+1)).timestamp())*1000000 for i in range(303)]
assert expected[-1]==protocol['end_us'] and dates[-1]==date(2025,6,30)
month_groups=[]
for i,d in enumerate(dates):
    if not month_groups or month_groups[-1][0]!=d.strftime('%Y-%m'):month_groups.append([d.strftime('%Y-%m'),i,i+1])
    else:month_groups[-1][2]=i+1
witnesses=[];nav_ids=[]
with localcontext() as context:
    context.prec=50
    for pair in result['pairs']:
        cases=[next(c for c in account['cases'] if c['id']==pair['case_id']) for account in accounts]
        assert cases[0]['symbols']==cases[1]['symbols'] and cases[0]['cost_id']==cases[1]['cost_id'] and cases[0]['unit_id']==cases[1]['unit_id']
        series=[];logs=[];pnls=[]
        for case in cases:
            ref=case['artifacts']['daily_nav.parquet'];p=Path(ref['path']);assert p.resolve().is_relative_to(STATE) and not p.is_symlink() and sha(p)==ref['sha256']
            frame=pl.read_parquet(p,columns=['day_end_us','nav']);assert frame['day_end_us'].to_list()==expected and frame.height==ref['rows']==303
            values=[D(x) for x in frame['nav'].to_list()];assert all(v.is_finite() and v>0 for v in values)
            previous=[Decimal(10000)]+values[:-1]
            log=[v.ln()-prior.ln() for v,prior in zip(values,previous)]
            pnl=[v-prior for v,prior in zip(values,previous)]
            same('log_telescoping',sum(log),(values[-1]/Decimal(10000)).ln(),1e-12)
            assert sum(pnl)==values[-1]-Decimal(10000)
            summary=case['summary'];assert summary['terminal_cash_realized'] and summary['terminal_marked_notional']==0
            same('terminal_decimal_wallet_bridge_USDT',values[-1],summary['decimal_strings']['NAV'],1e-7)
            same('terminal_decimal_PnL_bridge_USDT',sum(pnl),summary['decimal_strings']['net_PnL'],1e-7)
            series.append(values);logs.append(log);pnls.append(pnl);nav_ids.append(dict(path=str(p),sha256=ref['sha256'],bytes=p.stat().st_size,rows=303))
        delta=[b-a for a,b in zip(logs[0],logs[1])];cash=[b-a for a,b in zip(pnls[0],pnls[1])]
        intervals=[('total',0,303,pair['total'])]
        intervals += [('tranche',a,b,record) for (a,b),record in zip([[0,101],[101,202],[202,303]],pair['fixed_tranches'])]
        intervals += [('month',a,b,record) for (_,a,b),record in zip(month_groups,pair['months'])]
        assert len(pair['fixed_tranches'])==3 and len(pair['months'])==10
        for scope,a,b,record in intervals:
            assert record['start']==dates[a].isoformat() and record['end_inclusive']==dates[b-1].isoformat() and record['days']==b-a
            net=sum(cash[a:b]);logdiff=sum(delta[a:b])
            same('reported_real_PnL_increment_USDT',net,record['net_increment_USDT'],1e-7)
            same('reported_paired_log_increment',logdiff,record['paired_log_return_increment'],1e-12)
            for side,prefix in ((0,'baseline'),(1,'challenger')):
                initial=Decimal(10000) if a==0 else series[side][a-1]
                same('actual_start_end_NAV_USDT',initial,record[prefix+'_start_NAV'],1e-7)
                same('actual_start_end_NAV_USDT',series[side][b-1],record[prefix+'_end_NAV'],1e-7)
                same('actual_segment_PnL_USDT',series[side][b-1]-initial,record[prefix+'_net_USDT'],1e-7)
                same('reported_account_log',sum(logs[side][a:b]),record[prefix+'_log_return'],1e-12)
                same('actual_segment_return',series[side][b-1]/initial-1,record[prefix+'_return'],1e-12)
        same('paired_terminal_log_bridge',sum(delta),(series[1][-1]/series[0][-1]).ln(),1e-12)
        for record in pair['block_intervals']:
            assert record['samples']==2000 and record['seed']==20261005 and record['block_days'] in (7,30,60)
            same('reported_mean_daily_log',sum(delta)/Decimal(303),record['mean_daily_log_increment'],1e-12)
            lo,hi=record['lower_mean_daily_log_increment'],record['upper_mean_daily_log_increment']
            assert lo<=hi and record['includes_zero']==(lo<=0<=hi)
        for month,record in zip(pair['months'],pair['leave_one_month_out_arithmetic_descriptions']):
            assert record['month']==month['start'][:7]
            same('month_out_arithmetic_USDT',sum(cash)-D(month['net_increment_USDT']),record['net_increment_except_month_USDT'],1e-7)
        witnesses.append(dict(case=pair['case_id'],total_increment=float(sum(cash)),tranche_increment=[round(t['net_increment_USDT'],6) for t in pair['fixed_tranches']],primary60=next(i for i in pair['block_intervals'] if i['block_days']==60)))
# Small synthetic index/percentile reference only: no repeat of the 24k market draws.
toy=[-0.3,0.7,-0.1,0.4,0.9,-0.8,0.2,0.5,-0.6,0.1,0.3,-0.2]
for block in (7,30,60):
    rng=np.random.default_rng(20261005);width=min(block,len(toy));count=math.ceil(len(toy)/width);means=[]
    for draw in range(37):
        starts=rng.integers(0,len(toy),size=count).tolist();indices=[]
        for offset in starts:
            for step in range(width):indices.append((offset+step)%len(toy))
        means.append(math.fsum(toy[j] for j in indices[:len(toy)])/len(toy))
    ordered=sorted(means)
    def quantile(q):
        position=(len(ordered)-1)*q;low=math.floor(position);high=math.ceil(position)
        return ordered[low]+(ordered[high]-ordered[low])*(position-low)
    low,high=block_bootstrap_mean_ci(np.asarray(toy),block_days=block,samples=37,seed=20261005)
    same('toy_circular_percentile',quantile(.025),low,1e-14);same('toy_circular_percentile',quantile(.975),high,1e-14)
assert time.monotonic()-start<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=300000000
assert sha(PROTOCOL)==result['protocol_sha256']
lines=['# D068 saved-wallet independent review','',f"Status: PASS independent arithmetic and fixed calendar scope; no independent alpha, OOS or APR claim.",'',f"Actual bounded task: `{os.environ['COIN_TASK_ID']}`. Execution closure: PENDING_ROOT_TOOL_CONFIRMATION.",f"Helper: `{Path(__file__)}`; SHA256 `{sha(__file__)}`.",f"Protocol SHA256 `{sha(PROTOCOL)}`; actual main result SHA256 `{sha(RESULT)}`. Main task `{result['task_id']}` confirmed completed exit 0.",'','## Independent calculations','',
'Opened only eight saved daily_nav Parquets (2 columns), exact SHA and complete ordered 303 UTC endpoints. Independently built dates by scalar timedelta, first previous NAV 10000, Decimal.from_float plus 50-digit scalar ln differences and direct end-minus-start wallet PnL. No producer summary functions, replay, target factory or main script imported.',
'Fixed 101-day slices: 2024-09-01–2024-12-10, 2024-12-11–2025-03-21, 2025-03-22–2025-06-30. Verified all 12 slices, 40 month slices and 4 totals against actual preceding and endpoint NAV; no reset to 10000. Eight final daily endpoints reconcile to the full Decimal wallet NAV and net PnL with zero terminal inventory.',
'', '| Maximum independent discrepancy | Value |','|---|---|']
for name,value in errors.items():lines.append(f'| {name} | {value:.12g} |')
lines+=['','## Financial interpretation','', '| condition | net increment USDT | fixed 101-day increments USDT | primary 60-day mean log CI |','|---|---:|---|---|']
for row in witnesses:
    interval=row['primary60'];lines.append(f"| {row['case']} | {row['total_increment']:.6f} | {row['tranche_increment']} | [{interval['lower_mean_daily_log_increment']:.9g}, {interval['upper_mean_daily_log_increment']:.9g}] |")
lines+=['','Every fixed condition reverses sign across time slices; third slice supplies more than the full-period net increment, while the middle slice loses incremental money. This rejects a stable advantage claim for this evaluated recipe/window. It does not prove that all exit10 rules or all trend strategies fail.',
'All 12 reported 7/30/60-day intervals include zero. Main block-bootstrap loop is the unchanged existing circular paired-mean function, seed and blocks bound before this diagnostic. Independently checked circular wrapping/truncation and interpolated percentiles on only 3×37 synthetic draws; did not repeat the 24,000 empirical draws. The empirical percentile numerical endpoints were not independently re-estimated.',
'Intervals assume block resampling is a useful dependence approximation; circular end-to-start stitching and changing regimes limit inference. About five complete 60-day blocks is a descriptive scale, not an effective sample-size certification. Bootstrap replication does not increase historical length; parameter choice followed prior seen results, and the diagnostic does not correct strategy-selection bias. Four friction/funding scenarios are paired sensitivities of the same history, not four independent studies.',
'Log-return differences compare each evolving wallet denominator; dollar increments use actual shared wallets, not a sum of separately reset accounts. Actual risks remain unmatched; this is not risk-normalized alpha. Data are Binance/Bybit-fee proxy, funding units remain scenarios, no native fills or historical venue rules are certified. Daily endpoints retain the previously accepted same-timestamp funding convention; this review verifies arithmetic, not new market-time semantics.',
'',f"Resource: elapsed {time.monotonic()-start:.6f}s; process peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024} bytes; eight Parquet payloads {sum(r['bytes'] for r in nav_ids)} bytes. Shared RAM guard: `{json.dumps(resources.status(),ensure_ascii=False)}`.",
'No fit/HPO, download, market replay, locked data, credential use, orders, leverage/caps change or evidence overwrite. Investment remains NONE/CASH; this only supports keeping exit10 as a research configuration with independent evidence required for promotion.','', '## Saved NAV identities','']
lines += [f"- `{r['path']}` SHA `{r['sha256']}`, {r['bytes']} bytes, 303 rows." for r in nav_ids]
text='\n'.join(lines)+'\n';assert len(text.encode())<1000000
with REPORT.open('x') as f:f.write(text)
print(json.dumps(dict(status='PASS_INDEPENDENT_DAILY_NAV_TIME_ARITHMETIC_NOT_ALPHA',task_id=os.environ['COIN_TASK_ID'],errors=errors,elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,report=str(REPORT)),ensure_ascii=False),flush=True)