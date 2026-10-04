"""Independent endpoint and Decimal journal review, no main-script import/replay."""
from pathlib import Path
from datetime import datetime,UTC
from decimal import Decimal,getcontext
import hashlib,json,os,resource,time,gc
import numpy as np
import polars as pl
from quant import resources
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');OUT=STATE/'d069-exit-wait-independent-20261005-v1'
P=ROOT/'protocols/DONCHIAN_EXIT_WAIT_20261005_V1.json';R=ROOT/'reports/fast_research/DONCHIAN_EXIT_WAIT_20261005_V1.json';REPORT=ROOT/'reports/DONCHIAN_EXIT_WAIT_INDEPENDENT_REVIEW_20261005_V1.md'
M=60000000;DAY=1440*M;getcontext().prec=50;began=time.monotonic();errors={};counts=dict(assets=0,episodes=0,months=0,base_FebMar_asset_state_cells=0);boundary_fund=0;first_fund=0

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def d(v):return Decimal.from_float(v) if isinstance(v,float) else Decimal(str(v))
def exact(row,key):return Decimal(row['decimal_strings'][key]) if key in row.get('decimal_strings',{}) else d(row[key])
def read(receipt):
    p=Path(receipt['path']);assert p.resolve().is_relative_to(STATE) or p.resolve().is_relative_to(ROOT/'reports');assert sha(p)==receipt['sha256'];return json.loads(p.read_text())
def compare(name,computed,saved):
    error=abs(d(computed)-d(saved));errors[name]=max(errors.get(name,Decimal(0)),error);assert error<Decimal('1e-7'),(name,error)
def add(a,b):return {key:a[key]+b[key] for key in a}
def zero():return dict.fromkeys(('gross_USDT','fees_USDT','execution_USDT','funding_USDT','net_USDT','fill_legs','filled_notional_USDT'),Decimal(0))
def paired(a,b,record,name):
    for label,value in [('baseline',a),('challenger',b),('increment',{k:b[k]-a[k] for k in a})]:
        for key,number in value.items():compare(name+'_'+key,number,record[label][key])
def stamp(s):return int(datetime.fromisoformat(s).timestamp())*1000000
assert sha(P)=='f7fbf68b0d5dfd8e69b88ac236351aebb9656cf5abb2e911e938216495fe107d'
protocol=json.loads(P.read_text());result=json.loads(R.read_text());assert result['status']=='COMPLETE_SAVED_EXIT_WAIT_MECHANISM_NOT_CAUSAL_ALPHA'
assert result['protocol_sha256']==sha(P)
main_task=json.loads((STATE/'task-progress'/('task-'+result['task_id']+'.json')).read_text());assert main_task['status']=='completed' and main_task['exit_code']==0
reports=[read(protocol[k]) for k in ('baseline_report','challenger_report')]
start=protocol['start_us'];end=protocol['end_us'];n=(end-start)//M;assert n==436320
labels=('BOTH_FLAT','OLD_LONG_NEW_FLAT','OLD_FLAT_NEW_LONG','BOTH_LONG','INELIGIBLE');episode_witness=[]
for record in result['cases']:
    cases=[next(c for c in account['cases'] if c['id']==record['case_id']) for account in reports]
    assert cases[0]['symbols']==cases[1]['symbols']==record['symbols']
    journals=[];targetmaps=[]
    for case in cases:
        journals.append((read(case['artifacts']['trades.json']),read(case['artifacts']['funding.json'])))
        assert len({(r['fill_id'],r['leg']) for r in journals[-1][0]})==len(journals[-1][0])
        assert len({(r['symbol'],r['event_us']) for r in journals[-1][1]})==len(journals[-1][1])
        for row in journals[-1][1]:
            assert start<=row['event_us']<=end
            if row['event_us']==start:
                first_fund+=1;assert exact(row,'signed_funding_USDT')==0
            if row['event_us']%DAY==0:boundary_fund+=1
        p=Path(case['artifacts']['targets.parquet']['path']);assert sha(p)==case['artifacts']['targets.parquet']['sha256'];frame=pl.read_parquet(p)
        targetmaps.append({s:frame.filter(pl.col('symbol')==s).sort('available_us') for s in record['symbols']})
        p=Path(case['artifacts']['minute_nav_inventory.parquet']['path']);assert sha(p)==case['artifacts']['minute_nav_inventory.parquet']['sha256']
    full=[zero(),zero()];monthsums={month:[zero(),zero()] for month in record['months']};base_states={month:{label:zero() for label in labels} for month in ('2025-02','2025-03')}
    for asset in record['assets']:
        symbol=asset['symbol'];arrays=[];symboljournals=[]
        for case,(trades,funds) in zip(cases,journals):
            frame=pl.read_parquet(case['artifacts']['minute_nav_inventory.parquet']['path'],columns=['close_us',symbol+'_quantity',symbol+'_isolated_equity',symbol+'_isolated_balance'])
            assert frame.height==n and np.array_equal(frame['close_us'].to_numpy(),np.arange(start+M,end+1,M,dtype=np.int64))
            arrays.append((frame[symbol+'_quantity'].to_numpy(),frame[symbol+'_isolated_equity'].to_numpy(),frame[symbol+'_isolated_balance'].to_numpy()))
            symboljournals.append(([r for r in trades if r['symbol']==symbol],[r for r in funds if r['symbol']==symbol]))
        def quantity(side,index):return float(arrays[side][0][index]) if index>=0 else 0.
        def u(side,instant):
            if instant==start:return Decimal(0)
            index=(instant-start)//M-1;assert start<instant<=end and (instant-start)%M==0
            return d(float(arrays[side][1][index]))-d(float(arrays[side][2][index]))
        def money(side,a,b):
            trades,funds=symboljournals[side]
            chosen=[r for r in trades if a<r['event_us']<=b or a==start==r['event_us']]
            events=[r for r in funds if a<r['event_us']<=b or a==start==r['event_us']]
            realized=sum((exact(r,'realized_PnL') for r in chosen),Decimal(0));fee=sum((exact(r,'fee_USDT_mid') for r in chosen),Decimal(0));exe=sum((exact(r,'execution_cost') for r in chosen),Decimal(0));fund=sum((exact(r,'signed_funding_USDT') for r in events),Decimal(0));gross=u(side,b)-u(side,a)+realized+exe
            return dict(gross_USDT=gross,fees_USDT=fee,execution_USDT=exe,funding_USDT=fund,net_USDT=gross-fee-exe+fund,fill_legs=Decimal(len(chosen)),filled_notional_USDT=sum((exact(r,'quantity')*exact(r,'fill_price') for r in chosen),Decimal(0)))
        raw=[targetmaps[side][symbol]['raw_signed_target'].to_list() for side in (0,1)]
        eligible=[targetmaps[side][symbol]['eligibility_reason'].to_list() for side in (0,1)];assert eligible[0]==eligible[1]
        for side in (0,1):assert targetmaps[side][symbol]['available_us'].to_list()==[start+i*DAY for i in range(303)]
        groups=[(int(raw[0][i]>0)+2*int(raw[1][i]>0)) if eligible[0][i]=='ELIGIBLE' else 4 for i in range(303)]
        actual=[money(side,start,end) for side in (0,1)];paired(*actual,asset['total'],'asset_total');full=[add(a,b) for a,b in zip(full,actual)];counts['assets']+=1
        for month,saved in asset['monthly_increments'].items():
            a=stamp(month+'-01T00:00:00+00:00');year,m=map(int,month.split('-'));b=stamp((f'{year+1}-01' if m==12 else f'{year}-{m+1:02d}')+'-01T00:00:00+00:00');bounds=[money(side,a,b) for side in (0,1)]
            for key in saved:compare('asset_month_'+key,bounds[1][key]-bounds[0][key],saved[key])
            monthsums[month]=[add(a,b) for a,b in zip(monthsums[month],bounds)]
        # Fixed base scenario Feb/Mar direct DAY interval decomposition, boundary events remain previous day's bucket.
        if record['case_id']=='LIQUIDITY_TEN_BASE27_RAW_AS_FRACTION':
            for i,group in enumerate(groups):
                month=datetime.fromtimestamp((start+i*DAY)/1000000,UTC).strftime('%Y-%m')
                if month not in base_states:continue
                a=start+i*DAY;b=a+DAY;values=[money(side,a,b) for side in (0,1)]
                base_states[month][labels[group]]=add(base_states[month][labels[group]],{k:values[1][k]-values[0][k] for k in values[0]})
                counts['base_FebMar_asset_state_cells']+=1
        expected=[];i=0
        while i<303:
            if groups[i]!=1:i+=1;continue
            a=i;i+=1
            while i<303 and groups[i]==1:i+=1
            expected.append((a,i))
        episodes=[e for e in record['episodes'] if e['symbol']==symbol];assert len(episodes)==len(expected)
        for (a,b),episode in zip(expected,episodes):
            signal=start+a*DAY;finish=start+b*DAY;assert episode['signal_exit_us']==signal and stamp(episode['start'])==signal and stamp(episode['end_exclusive'])==finish and episode['classification_days']==b-a
            transition='OBSERVED_BOTH_LONG_TO_OLD_LONG_NEW_FLAT' if a>0 and groups[a-1]==3 else 'UNKNOWN_OR_LEFT_CENSORED';assert episode['exit_transition']==transition
            assert transition=='OBSERVED_BOTH_LONG_TO_OLD_LONG_NEW_FLAT'
            assert episode['end_signal_state']==(labels[groups[b]] if b<303 else 'RIGHT_CENSORED_EVALUATION_END')
            future=next((j for j in range(a+1,303) if raw[1][j]>0),None);nextsignal=start+future*DAY if future is not None else None
            assert episode['next_new_long_signal_us']==nextsignal and episode['next_new_long_signal_censored']==(nextsignal is None)
            assert episode['days_to_next_new_long_signal']==(future-a if future is not None else None)
            trades=symboljournals[1][0];sells=[r for r in trades if r['signal_us']==signal and exact(r,'position_delta')<0];opens=[r['event_us'] for r in trades if r['event_us']>=signal and r['leg']=='OPEN' and exact(r,'quantity_before')==0]
            assert episode['exit_signal_sell_legs']==len(sells);compare('exit_sell_quantity',sum((exact(r,'quantity') for r in sells),Decimal(0)),episode['exit_signal_sell_quantity'])
            assert episode['next_actual_flat_to_open_us']==(min(opens) if opens else None)
            first=a*1440;stop=b*1440;before=quantity(1,first-1);compare('pre_exit_quantity',before,episode['actual_new_quantity_before_signal'])
            status='ALREADY_FLAT_BEFORE_SIGNAL' if first==0 or before==0 else 'MATCHED_SIGNAL_REDUCTION_LEGS' if sells else 'NO_MATCHED_SIGNAL_SELL_UNKNOWN';assert episode['actual_exit_status']==status
            flats=np.flatnonzero(arrays[1][0][first:stop]==0);flatclose=start+(first+int(flats[0])+1)*M if len(flats) else None;assert episode['first_observed_new_flat_close_us']==flatclose
            assert episode['old_positive_inventory_minutes']==int(np.count_nonzero(arrays[0][0][first:stop]>0));assert episode['new_positive_inventory_minutes']==int(np.count_nonzero(arrays[1][0][first:stop]>0))
            values=[money(side,signal,finish) for side in (0,1)];paired(*values,episode['paired_asset_money'],'episode');counts['episodes']+=1
            if record['case_id']=='LIQUIDITY_TEN_BASE27_RAW_AS_FRACTION':episode_witness.append((symbol,a,b,float(values[1]['net_USDT']-values[0]['net_USDT'])))
        del frame,arrays,symboljournals;gc.collect()
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=300000000 and time.monotonic()-began<=120
    paired(*full,record['total'],'case_total')
    for month,value in monthsums.items():paired(*value,record['months'][month],'case_month');counts['months']+=1
    for side,case in enumerate(cases):
        for field,summarykey in [('gross_USDT','gross_PnL_same_quantities'),('fees_USDT','fees_USDT'),('execution_USDT','execution_cost_USDT'),('funding_USDT','funding_USDT'),('net_USDT','net_PnL')]:compare('wallet_summary_'+field,full[side][field],case['summary']['decimal_strings'][summarykey])
    if record['case_id']=='LIQUIDITY_TEN_BASE27_RAW_AS_FRACTION':
        for month,states in base_states.items():
            for label,values in states.items():
                for key in values:compare('base_FebMar_state_'+key,values[key],record['monthly_state_increments'][month][label][key])
    del journals,targetmaps;gc.collect()
assert counts['assets']==40 and counts['episodes']==52 and counts['months']==40
assert sha(P)==result['protocol_sha256']
lines=['# D069 independent saved-exit episode review','', 'Status: PASS endpoint/Decimal journal bridges and actual signal/inventory scope; not a counterfactual or alpha certification.','',f"Actual task `{os.environ['COIN_TASK_ID']}`; closure PENDING_ROOT_TOOL_CONFIRMATION.",f"Helper `{Path(__file__)}` SHA `{sha(__file__)}`.",f"Protocol SHA `{sha(P)}`; actual result SHA `{sha(R)}`; main task `{result['task_id']}` confirmed completed exit 0.",'','## Independent arithmetic and coverage','',f"Verified {counts['assets']} per-asset full-span pairs, four full wallet totals, {counts['months']} case months plus 400 asset-months, all {counts['episodes']} episodes, and {counts['base_FebMar_asset_state_cells']} asset-day state assignments in fixed BASE27/fraction February/March. No main script imported; no 80 full monetary vectors or fresh account replay built.",
'One asset at a time, independently obtained U endpoints from saved isolated_equity minus isolated_balance using 50-digit Decimal converted from the actual stored Float64s. Original fill/funding decimal_strings were summed by scalar comparisons start < event <= end. First evaluation-boundary events were separately retained and verified zero funding. Therefore exact UTC-end funding is included in the earlier closed-minute/day; raw classifications use that day’s minute-open decision, not the next decision at the endpoint.',
'Gross = end U − start U + realized fill PnL + execution cost; net then subtracts fees and execution and adds signed funding. Collateral transfer/release is not revenue; execution embedded in fill PnL is added back only to report gross. A nonzero starting U is preserved at every episode/month, rather than reset.',
'', '| Maximum absolute discrepancy (50-digit Decimal comparison) | Value |','|---|---|']
lines += [f'| {key} | {float(value):.12g} |' for key,value in sorted(errors.items())]
lines += ['', '## Actual episode boundaries and inventory','',
'All 13 episodes per condition (52 total) are eligible preceding BOTH_LONG → OLD_LONG_NEW_FLAT transitions, rather than inferred from a profitable interval. Independently rebuilt contiguous states, ending state, censorship, subsequent positive raw signal and separately subsequent actual flat-to-OPEN fill. Verified matched signal SELL leg quantities, pre-signal actual quantity, first observed minute-end zero inventory and old/new positive-inventory minute counts; partial inventory remains real. State classification does not imply the order reason caused a profit.',
f'Base fraction reference episodes (symbol, start day index, exclusive end day index, actual two-account asset net increment): `{episode_witness}`.',
'', '## Conclusions and limits','',
'Bridges explain where the already simulated paired wallet difference occurred. They do not answer what returns cancelling an exit, changing reentry timing, ignoring risk reductions or redistributing capital would have produced; those require a new complete strategy/account experiment. A per-asset matched-period flow difference is not an independent full-capital portfolio result.',
'All five raw signal categories retain BOTH_FLAT, BOTH_LONG, divergent long/flat and INELIGIBLE accounting. The fixed February/March subcheck independently validates the important recovery-period state split; full all-month state monetary rederivation and per-minute NAV/event bridges were not repeated here. Main recorded bridges and previous independent financial ledger evidence are separate scope. This check does not revalidate market QA, labels, exchange fills or historical margin rules.',
'Four conditions share the same selected history and signals; funding fractions/percent remain scenarios and Binance price plus Bybit fees is proxy. No unseen/OOS/selection-bias correction, risk matching, APR or deployable alpha qualification results. Original earlier-exit gains and recovery losses remain preserved, investment NONE/CASH.',
'',f"Resource: {time.monotonic()-began:.6f}s, peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024} bytes; shared guard `{json.dumps(resources.status())}`.",f"UTC-day-boundary funding journal rows inspected: {boundary_fund}; first start-time zero-funding rows: {first_fund}. Zero model fits/HPO/API/new data QA/replays, no keys/locked/orders/GPU/Git or existing source edits."]
text='\n'.join(lines)+'\n';assert len(text.encode())<1000000
with REPORT.open('x') as f:f.write(text)
print(json.dumps(dict(status='PASS_ENDPOINT_AND_DECIMAL_JOURNAL_NOT_COUNTERFACTUAL',task_id=os.environ['COIN_TASK_ID'],counts=counts,max_error_USDT=float(max(errors.values())),elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,report=str(REPORT))),flush=True)