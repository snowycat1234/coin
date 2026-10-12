"""Frozen four-arm allocation experiment using the existing default native wallet."""
import argparse,gzip,hashlib,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from dependencies import recover

def save(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(state,source_commit,expected=None):
    assert not state.exists() and state.resolve().is_relative_to(Path('/workspace'))
    state.mkdir();began=time.monotonic();dep,dependency=recover(state);sys.path.insert(0,str(dep))
    from allocator import targets,DAY,ARMS,SYMBOLS
    npath=ROOT/'research/short-native-activity-20261012';sys.path.insert(0,str(npath))
    spec=importlib.util.spec_from_file_location('hrp_native',npath/'run.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);b=native.bridge
    assert not b.git('status','--porcelain'),'Clean published source required'
    if not expected:assert b.git('rev-parse','HEAD').decode().strip()==source_commit
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        digest,name=line.split(maxsplit=1);assert sha(ROOT/name)==digest,name
    assert tuple(native.SYMBOLS)==SYMBOLS
    start,end=native.utc('2022-01-01'),native.utc('2022-02-01');d=np.arange(start,end,DAY)
    risk_path=ROOT/'research/minute-conditional-selector-20261011/input/SOURCE_PREPARED.npz'
    protocol=json.loads((HERE/'PROTOCOL.json').read_text());assert sha(risk_path)==protocol['source_risk_npz_SHA256']
    with np.load(risk_path,allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==SYMBOLS
        t=z['close_available_us'];price=z['close'];ids=np.searchsorted(z['decision_us'],d)
        np.testing.assert_array_equal(z['decision_us'][ids],d);mask=z['asset_eligible'][ids,1,:]
    assert mask.shape==(31,5) and mask.all(),'All Jan members ready; do not silently change original-control eligibility'
    weights,proof,matrix=targets(t,price,d,mask)
    assert len(matrix)==31 and all(r['reason']=='ELIGIBLE' for r in proof)
    changed=price.copy();changed[t>d[14]]*=np.linspace(1.1,2.,int((t>d[14]).sum()))[:,None]
    suffix,_,sm=targets(t,changed,d,mask)
    for arm in ARMS:np.testing.assert_array_equal(weights[arm][:15],suffix[arm][:15])
    for a,c in zip(matrix[:15],sm[:15]):
        np.testing.assert_array_equal(a['covariance'],c['covariance']);np.testing.assert_array_equal(a['linkage'],c['linkage'])
    from scripts.investment.public_sma_perpetual import signed_risk_weights
    for j,at in enumerate(d):
        k=int(np.searchsorted(t,at));past=price[k-30:k+1];r=np.diff(past,axis=0)/past[:-1]
        sample=r.std(0,ddof=1);inverse=sample.min()/sample;raw=np.minimum(.3,.6*inverse/inverse.sum())
        old,_=signed_risk_weights(raw,r);np.testing.assert_allclose(weights['IVOL_ORIGINAL'][j],old,rtol=1e-13,atol=1e-14)
    b.configure(state,'Q12022');proto=json.loads((native.NATIVE/'PROTOCOL.json').read_text())
    tp,tc=b.certificate(proto['trade_source_commit'],b.TRADE,'Q12022');mp,mc=b.certificate(proto['mark_source_commit'],b.MARK,'Q12022')
    prevt,pt=b.certificate(proto['trade_source_commit'],b.TRADE,'Y2021');prevm,pm=b.certificate(proto['mark_source_commit'],b.MARK,'DEC2021')
    inv,*_=b.inventories();reader=b.SourceReader(inv,state,local=False);trade={};mark={};daily=[];sources=[]
    for asset,s in enumerate(SYMBOLS):
        tr=next(r for r in tp['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01');mr=next(r for r in mp['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01')
        assert tr['past_boundary']==prevt['end_boundaries'][s] and mr['past_boundary']==prevm['end_boundaries'][s]
        assert tr['past_boundary']['available_us']==mr['past_boundary']['available_us']==start
        tf,te=b.decoded_month(reader,tr['source'],start//1000,end//1000);mf,me=b.complete_month(reader,mr['source'],start//1000,end//1000)
        trade[s]=native.source_bars(tf,tr['source'],'klines',added_repair_rows=sum(r['added_actual_rows'] for r in te['repairs']))
        mark[s]=native.source_bars(mf,mr['source'],'markPriceKlines',added_repair_rows=sum(r['added_actual_rows'] for r in me['repairs']))
        for at in d:
            actual=tr['past_boundary']['close'] if at==start else native.exact_boundary(trade[s],int(at))['price']
            k=int(np.searchsorted(t,at));assert abs(price[k,asset]-actual)<=1e-12*abs(actual),'Saved risk vs actual-source completed close identity'
            daily.append(dict(symbol=s,close_us=int(at),close=float(actual)))
        sources.append(dict(symbol=s,trade_ZIP_SHA256=tr['source']['ZIP_SHA256'],mark_ZIP_SHA256=mr['source']['ZIP_SHA256'],minutes=len(tf)))
        print('HRP_SOURCE_VERIFIED',s,len(tf),len(mf),flush=True)
    reader.close();events,funding=native.fund_events(state,start,end)
    def blocks():
        for at in d:yield native.legacy_projection(native.day_block(SYMBOLS,trade,mark,int(at)))
    window=dict(start=start,end=end,symbols=SYMBOLS,daily=native.pl.DataFrame(daily),events=events,minute_blocks=blocks)
    save(state/'CAUSAL_PROOF.json',dict(proof=proof,all_Jan_members_ready=True,original_formula_parity=True,real_source_completed_close_parity=True,real_suffix_invariance=True,dependencies=dependency))
    array=dict(decision_us=d,symbol_order=np.array(SYMBOLS),availability_mask=mask,**{arm:weights[arm] for arm in ARMS})
    for key in ('covariance','correlation_used','distance_used','linkage','leaf_order','normalized_HRP','normalized_IVOL','normalized_IVAR','raw_HRP','raw_IVOL','raw_IVAR'):array[key]=np.stack([m[key] for m in matrix])
    np.savez_compressed(state/'ALLOCATION.npz',**array)
    reports={};daily_returns={}
    for arm in ARMS:
        w=weights[arm];native.targets(d,w,start,end,start,SYMBOLS)
        def factory(_daily,clocks,mode):
            np.testing.assert_array_equal(clocks,d)
            return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(source='PAST30_ALLOCATION_ONLY',arm=arm,source_commit=source_commit,policy_protocol_SHA256=sha(HERE/'PROTOCOL.json'),all_directions='LONG')
        sim=native.NativeDailySimulator(window,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory)
        while sim.cursor<end and sim.stop is None:
            sim.advance_day();assert time.monotonic()-began<600
            if sim.rows_written//1440 in (1,10,20,31):print('HRP_ACTUAL_ACCOUNT',arm,sim.rows_written//1440,flush=True)
        case=sim.result();ep,q=native.episodes(case['trades'],SYMBOLS);assert not ep and all(v>=0 for v in q.values())
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(case['trades'],case['funding'],q,case['summary']['terminal_mark_prices'],sim.account.nav())
        saved=native.save_case(case,state/(arm+'_ACCOUNT'));summary=saved['summary'];minute=case['minute']
        assert abs(sum(v['net_contribution'] for v in summary['long_short_marked_contribution'].values())-(summary['NAV']-10000))<1e-7
        day=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,day['nav'].to_numpy()];ret=np.diff(nav)/nav[:-1];daily_returns[arm]=ret
        metric=dict(realized_daily_annual_vol=float(ret.std(ddof=1)*np.sqrt(365)) if len(ret)>1 else None,realized_daily_observations=len(ret))
        if len(ret)>=7:
            rolling=nav[7:]/nav[:-7]-1;k=int(np.argmin(rolling));metric.update(worst_rolling_7day_return=float(rolling[k]),worst_7day_start_us=int(start+k*DAY),worst_7day_end_us=int(start+(k+7)*DAY))
        report=dict(summary=summary,liquidation_events=len(case.get('liquidations',[])),independent_decimal_NAV_bridge=finance,rejection_reasons=native.rejection_counts(case['rejections']),metrics=metric,paid_flat=bool(summary['terminal_cash_realized']),full_calendar=summary['completed_minutes']==44640,snapshot_recovery='PASS')
        reports[arm]=report
        body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body['liquidations']=case.get('liquidations',[]);body['summary']=summary;body['targets']=case['targets'].to_dicts();save(state/(arm+'_ACCOUNT.json'),body)
        np.savez_compressed(state/(arm+'_MINUTE.npz'),**{k:minute[k].to_numpy() for k in minute.columns})
        snap=sim.snapshot();(state/(arm+'_SNAPSHOT.json.gz')).write_bytes(gzip.compress(json.dumps(snap,sort_keys=True,allow_nan=False,separators=(',',':')).encode(),mtime=0))
        restored=native.NativeDailySimulator.from_snapshot(snap,window)
        assert restored.account.snapshot()==sim.account.snapshot() and restored.cursor==sim.cursor and restored.weights==sim.weights,'Genuine state restoration'
        del restored,snap,case,sim,minute
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<1_000_000_000
        print('HRP_ACCOUNT_RESULT',arm,summary['NAV'],report['paid_flat'],metric,flush=True)
    comparisons={};rng=np.random.default_rng(811620)
    for control in ('IVOL_MATCHED','IVAR_MATCHED'):
        if not all(r['full_calendar'] for r in reports.values()):
            comparisons[control]=dict(status='NOT_EVALUABLE_INCOMPLETE_CALENDAR',gates=dict(full_calendar=False))
            continue
        h=reports['HRP_MATCHED'];c=reports[control];delta=daily_returns['HRP_MATCHED']-daily_returns[control]
        assert len(delta)==31
        draws=[]
        for _ in range(1000):
            starts=rng.integers(0,len(delta),size=3);ids=np.concatenate([(s+np.arange(14))%len(delta) for s in starts])[:len(delta)];draws.append(float(delta[ids].mean()))
        lo,hi=np.quantile(draws,[.025,.975]);ratio=h['metrics']['realized_daily_annual_vol']/c['metrics']['realized_daily_annual_vol']
        comparisons[control]=dict(marked_net_increment_USDT=h['summary']['net_PnL']-c['summary']['net_PnL'],mean_daily_return_difference=float(delta.mean()),bootstrap_95CI=[float(lo),float(hi)],realized_vol_ratio=float(ratio),gates=dict(net_increment=h['summary']['net_PnL']>c['summary']['net_PnL'],daily_difference_CI=float(lo)>0,realized_vol=ratio<=1.10,drawdown=h['summary']['all_observation_max_drawdown']<=c['summary']['all_observation_max_drawdown'],worst_7day=h['metrics']['worst_rolling_7day_return']>=c['metrics']['worst_rolling_7day_return']))
    account_gate=all(r['full_calendar'] and r['paid_flat'] and r['liquidation_events']==0 for r in reports.values())
    passed=account_gate and all(all(c['gates'].values()) for c in comparisons.values())
    report=dict(status='PASS_CONDITIONAL_HRP_CONTINUATION_GATES' if passed else 'STOP_FIXED_HRP_ALLOCATION_GATES',source_commit=source_commit,protocol_SHA256=sha(HERE/'PROTOCOL.json'),attempts=1,new_allocation_accounts=4,new_supervised_fits=0,old_account_reruns=0,provider_downloads=0,account_gate=account_gate,arms=reports,comparisons=comparisons,sources=sources,source_certificates=dict(trade=tc,mark=mc,priortrade=pt,priormark=pm,funding=funding),data_role=protocol['data_role'],authority='CONDITIONAL_EXISTING_NATIVE_SOFTWARE_KERNEL_FEE_UNIT_CHARGE_MARK_MMR_ARRIVAL_NOT_NATIVE_CERTIFIED',prediction_increment='NOT_APPLICABLE_ALLOCATION_ONLY',investment_candidate='NONE')
    save(state/'RESULT.json',report)
    names=['CAUSAL_PROOF.json','ALLOCATION.npz','RESULT.json']+[arm+suffix for arm in ARMS for suffix in ('_ACCOUNT.json','_MINUTE.npz','_SNAPSHOT.json.gz')]
    assert sum((state/n).stat().st_size for n in names)<64_000_000
    save(state/'TIMING.json',dict(seconds=time.monotonic()-began,result_bytes=sum((state/n).stat().st_size for n in names)))
    if expected:
        for name in names:assert b.git('show',expected+':research/hrp-risk-allocation-20261012/result/'+name)==(state/name).read_bytes(),'Exact public restore '+name
        save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_HRP_FOUR_ACCOUNTS',artifact_commit=expected,science_source_commit=source_commit,verification_accounts=4,new_supervised_fits=0,provider_downloads=0,old_account_reruns=0))
    print(json.dumps(dict(status=report['status'],account_gate=account_gate,comparisons=comparisons),indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
