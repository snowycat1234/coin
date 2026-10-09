"""Read-only observed inventory/PnL attribution; no accounts or model inference.

Gross-size versus signed-composition is an algebraic partition of recorded
inventory differences. It is not an executable counterfactual or switching gain.
"""
import argparse,csv,hashlib,importlib.util,json,os,resource,sys
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import polars as pl

HERE=Path(__file__).resolve().parent
START,END,DAY,MINUTE=1714521600000000,1719792000000000,86400000000,60000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
ARMS=('V2_GRU64_NO_CASH','V2_GRU64_WITH_CASH','V2_LATEST_MLP_NO_CASH','V2_LATEST_MLP_WITH_CASH')
COMMITS=('2bf2dc03e1ca3f0594b7b15dcff0cdb5651c5f1d','df1bc4b875e02c860d8c369ce01bdf03dee6ca43')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
date=lambda t:datetime.fromtimestamp(int(t)/1e6,UTC).date().isoformat()


def check_file(p,r):
    assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],p.name


def markets(state):
    root=state/'h1_validation/original/h1_market';manifest=root/'reports/DATASET_MANIFEST.json'
    assert sha(manifest)=='8facb75645001306c8179284a057c70ed6c01fc7439b84ffc6f3cb532042cebd'
    registered={r['relative_path']:r for r in read(manifest)['artifacts']};columns=[];initial=[];sources=[]
    expected=np.arange(START+MINUTE,END+1,MINUTE,dtype=np.int64)
    for symbol in SYMBOLS:
        frames=[]
        n=f'data/normalized/minute/{symbol}/markPriceKlines/2024-04.parquet';p=root/n;check_file(p,registered[n]);sources.append(dict(relative_path=n,sha256=registered[n]['sha256']))
        prior=pl.read_parquet(p,columns=['timestamp_ms','close']).filter(pl.col('timestamp_ms')==(START-MINUTE)//1000)
        assert prior.height==1;initial.append(prior['close'][0])
        for month in ('2024-05','2024-06'):
            n=f'data/normalized/minute/{symbol}/markPriceKlines/{month}.parquet';p=root/n;check_file(p,registered[n]);sources.append(dict(relative_path=n,sha256=registered[n]['sha256']))
            frames.append(pl.read_parquet(p,columns=['timestamp_ms','close']))
        d=pl.concat(frames).sort('timestamp_ms');assert np.array_equal(d['timestamp_ms'].to_numpy()*1000+MINUTE,expected)
        columns.append(d['close'].to_numpy())
    p=np.column_stack(columns);assert p.shape==(87840,5) and np.isfinite(p).all() and (p>0).all()
    initial=np.array(initial);endpoints=p[1439::1440];previous=np.vstack((initial,endpoints[:-1]))
    return p,initial,endpoints/previous-1,sources


def account(state,name,marks,initial_marks):
    control=name in ('STATIC50','CASH50');root=state/('results61' if control else 'temporal-v2-native61')/name
    member=HERE/('comparison61' if control else 'temporal-v2-native61-cash-results' if 'WITH_CASH' in name else 'temporal-v2-native61-results')/'RESULT_MEMBER_HASHES.json'
    prefix=('results61/' if control else 'accounts/')+name+'/'
    hashes={r['path']:r for r in read(member)['files']};sources=[]
    for n in ('INDEPENDENT_AUDIT.json','account/summary.json','account/minute_nav_inventory.parquet','account/daily_nav.parquet','account/trades.json','account/targets.parquet'):
        p=root/n;check_file(p,hashes[prefix+n]);sources.append(dict(path=prefix+n,sha256=hashes[prefix+n]['sha256']))
    s=read(root/'account/summary.json');audit=read(root/'INDEPENDENT_AUDIT.json')
    assert audit['status'].startswith('PASS_') and s['completed_minutes']==87840 and s['liquidation_count']==0 and s['terminal_cash_realized']
    cols=['close_us','nav','gross_notional','gross_weight','net_signed_weight','cumulative_fees','cumulative_execution_costs','cumulative_funding']+[symbol+k for k in ('_quantity','_signed_marked_notional') for symbol in SYMBOLS]
    d=pl.read_parquet(root/'account/minute_nav_inventory.parquet',columns=cols)
    assert np.array_equal(d['close_us'].to_numpy(),np.arange(START+MINUTE,END+1,MINUTE))
    q=d.select([s+'_quantity' for s in SYMBOLS]).to_numpy();notional=d.select([s+'_signed_marked_notional' for s in SYMBOLS]).to_numpy()
    assert np.max(abs(q*marks-notional))<1e-6
    qprior=np.vstack((np.zeros(5),q[:-1]));markprior=np.vstack((initial_marks,marks[:-1]))
    hold=qprior*(marks-markprior);fill=np.zeros_like(hold);dq=np.zeros_like(hold)
    for t in read(root/'account/trades.json'):
        exact=t['decimal_strings'];i=(t['event_us']-START)//MINUTE;j=SYMBOLS.index(t['symbol'])
        assert 0<=i<87840 and t['event_us']%MINUTE==1
        delta=float(exact['position_delta']);mid=float(exact['execution_mid_price'])
        dq[i,j]+=delta;fill[i,j]+=delta*(marks[i,j]-mid)
    assert np.max(abs(qprior+dq-q))<1e-7
    endpoints=np.arange(1439,87840,1440);days=np.arange(START,END,DAY,dtype=np.int64)
    differences=lambda col:np.diff(np.r_[10000. if col=='nav' else 0.,d[col].to_numpy()[endpoints]])
    net,fees,execution,funding=(differences(k) for k in ('nav','cumulative_fees','cumulative_execution_costs','cumulative_funding'))
    price=(hold+fill).reshape(61,1440,5).sum((1,2));by_asset=(hold+fill).reshape(61,1440,5).sum(1)
    assert np.max(abs(net-(price+funding-fees-execution)))<1e-6
    for actual,field in ((net,'net_PnL'),(price,'gross_PnL_same_quantities'),(fees,'fees_USDT'),(execution,'execution_cost_USDT'),(funding,'funding_USDT')):assert abs(actual.sum()-s[field])<1e-6
    gross=d['gross_weight'].to_numpy().reshape(61,1440);signed=d['net_signed_weight'].to_numpy().reshape(61,1440)
    weights=(notional/d['nav'].to_numpy()[:,None]).reshape(61,1440,5)
    daily=dict(net=net,price=price,funding=funding,fees=fees,execution=execution,gross_mean=gross.mean(1),gross_peak=gross.max(1),net_mean=signed.mean(1),net_positive_minute_fraction=(signed>0).mean(1),long_mean=np.maximum(weights,0).sum(2).mean(1),short_mean=np.maximum(-weights,0).sum(2).mean(1))
    rows=[]
    for i,t in enumerate(days):rows.append(dict(date=date(t),**{k:float(v[i]) for k,v in daily.items()},asset_price_USDT=dict(zip(SYMBOLS,map(float,by_asset[i]))),asset_mean_signed_weight=dict(zip(SYMBOLS,map(float,weights[i].mean(0))))))
    for i,mask in enumerate((np.arange(61)<31,np.arange(61)>=31)):
        assert abs(net[mask].sum()-s['months'][i]['net_PnL'])<1e-6 and abs(price[mask].sum()-s['months'][i]['gross_PnL'])<1e-6
    checks=dict(maximum_inventory_quantity_bridge_error=float(np.max(abs(qprior+dq-q))),maximum_actual_marked_notional_error_USDT=float(np.max(abs(q*marks-notional))),maximum_daily_price_funding_cost_NAV_bridge_error_USDT=float(np.max(abs(net-(price+funding-fees-execution)))),daily_monthly_full_summary_bridges='PASS',completed_minutes=87840,liquidations=0,terminal_paid_flat=True)
    return dict(root=root,summary=s,sources=sources,checks=checks,qprior=qprior,prior_gross=np.r_[0.,d['gross_notional'].to_numpy()[:-1]],hold=hold,fill=fill,rows=rows,daily=daily,by_asset=by_asset)


def mix(state,adapter,context,mapper,name,own):
    if name in ('STATIC50','CASH50'):
        desired=np.tile([0,.5,0,0,.5] if name=='STATIC50' else [.5,.25,0,0,.25],(61,1));provenance='FROZEN_STATIC_REFERENCE'
    else:
        commit=COMMITS['WITH_CASH' in name];bundle=state/'temporal-v2-exports'/commit/name/'MANIFEST.json'
        m,a=adapter.load_bundle(bundle,sha(bundle));desired,_=adapter.validate(m,a,context);provenance=dict(commit=commit,manifest_SHA256=sha(bundle),request_SHA256=m['files'][m['request_file']]['sha256'])
    targets,budget=adapter.mapped(desired,context,mapper)
    actual=pl.read_parquet(own['root']/'account/targets.parquet')['target_weight'].to_numpy().reshape(61,5);assert np.array_equal(targets,actual)
    selected=np.argmax(desired[:,[1,4]],axis=1);changes=np.flatnonzero(selected[1:]!=selected[:-1])+1
    summary={}
    for period,mask in (('ALL',np.ones(61,bool)),('MAY',np.arange(61)<31),('JUNE',np.arange(61)>=31)):
        summary[period]=dict(request_mean=dict(zip(('CASH','VOL','CS'),map(float,desired[mask][:,[0,1,4]].mean(0)))),ramped_budget_mean=dict(zip(('CASH','VOL','CS'),map(float,budget[mask][:,[0,1,4]].mean(0)))),ramped_CS_gt_VOL_dates=int((budget[mask,4]>budget[mask,1]).sum()),requested_CS_gt_VOL_dates=int((desired[mask,4]>desired[mask,1]).sum()))
    active=changes[changes<60]
    return dict(desired=desired,budget=budget,summary=summary,request_dominant_VOL_CS_changes=int(len(changes)),request_dominance_change_dates=[date(START+i*DAY) for i in changes],nonterminal_request_dominant_VOL_CS_changes=int(len(active)),nonterminal_request_dominance_change_dates=[date(START+i*DAY) for i in active],request_total_L1_variation=float(abs(np.diff(desired,axis=0)).sum()),budget_total_L1_variation=float(abs(np.diff(budget,axis=0)).sum()),provenance=provenance,first_ramped_VOL_gt_CS_date=next((date(START+i*DAY) for i in range(60) if budget[i,1]>budget[i,4]),None))


def compare(own,reference,market_returns):
    # Scale recorded reference inventory to the arm's lagged absolute USDT
    # gross, solely as an algebraic basis. No trades or NAV path are constructed.
    ratio=np.divide(own['prior_gross'],reference['prior_gross'],out=np.ones(87840),where=reference['prior_gross']>0)
    scale=(ratio[:,None]-1)*reference['hold']
    composition=own['hold']-ratio[:,None]*reference['hold']
    fill=own['fill']-reference['fill']
    pieces={k:v.reshape(61,1440,5).sum((1,2)) for k,v in [('held_gross_size',scale),('held_signed_composition_and_timing',composition),('fill_to_completed_minute_mark',fill)]}
    price=own['daily']['price']-reference['daily']['price'];assert np.max(abs(sum(pieces.values())-price))<1e-6
    rows=[]
    for i in range(61):
        a,b=own['rows'][i],reference['rows'][i]
        delta={k:a[k]-b[k] for k in ('net','price','funding','fees','execution','gross_mean','net_mean','long_mean','short_mean')}
        row=dict(date=a['date'],arm_net_USDT=a['net'],reference_net_USDT=b['net'],incremental_net_USDT=delta['net'],incremental_price_USDT=delta['price'],incremental_funding_USDT=delta['funding'],incremental_fee_effect_USDT=-delta['fees'],incremental_execution_effect_USDT=-delta['execution'],arm_mean_gross=a['gross_mean'],reference_mean_gross=b['gross_mean'],arm_mean_net_signed=a['net_mean'],reference_mean_net_signed=b['net_mean'],
                 arm_net_positive_minute_fraction=a['net_positive_minute_fraction'],arm_asset_mean_signed_weight=a['asset_mean_signed_weight'],reference_asset_mean_signed_weight=b['asset_mean_signed_weight'],actual_asset_mark_daily_return=dict(zip(SYMBOLS,map(float,market_returns[i]))),actual_equal_weight_mark_daily_return=float(market_returns[i].mean()),
                 price_difference_algebra={k:float(v[i]) for k,v in pieces.items()},incremental_asset_price_USDT={s:float(own['by_asset'][i,j]-reference['by_asset'][i,j]) for j,s in enumerate(SYMBOLS)})
        assert abs(row['incremental_net_USDT']-sum(row[k] for k in ('incremental_price_USDT','incremental_funding_USDT','incremental_fee_effect_USDT','incremental_execution_effect_USDT')))<1e-6;rows.append(row)
    periods={}
    for period,ix in (('ALL',np.arange(61)),('MAY',np.arange(31)),('JUNE',np.arange(31,61))):
        selected=[rows[i] for i in ix]
        totals={k:float(sum(r[k] for r in selected)) for k in ('incremental_net_USDT','incremental_price_USDT','incremental_funding_USDT','incremental_fee_effect_USDT','incremental_execution_effect_USDT')}
        totals.update(arm_net_USDT=float(own['daily']['net'][ix].sum()),reference_net_USDT=float(reference['daily']['net'][ix].sum()),arm_mean_gross=float(own['daily']['gross_mean'][ix].mean()),reference_mean_gross=float(reference['daily']['gross_mean'][ix].mean()),arm_mean_net_signed=float(own['daily']['net_mean'][ix].mean()),reference_mean_net_signed=float(reference['daily']['net_mean'][ix].mean()),price_difference_algebra={k:float(v[ix].sum()) for k,v in pieces.items()})
        periods[period]=totals
    decline=(np.arange(61)>=31)&(market_returns.mean(1)<0)
    observed_decline=dict(scope='EX_POST_JUNE_DATES_WITH_NEGATIVE_EQUAL_WEIGHT_CORE5_ACTUAL_UTC_MARK_RETURN; NOT_A_TRADED_BENCHMARK',dates=int(decline.sum()),arm_positive_daily_mean_net_dates=int((own['daily']['net_mean'][decline]>0).sum()),arm_mean_net_signed=float(own['daily']['net_mean'][decline].mean()),arm_mean_gross=float(own['daily']['gross_mean'][decline].mean()),reference_mean_net_signed=float(reference['daily']['net_mean'][decline].mean()),reference_mean_gross=float(reference['daily']['gross_mean'][decline].mean()),arm_net_positive_minute_fraction=float(own['daily']['net_positive_minute_fraction'][decline].mean()))
    return dict(periods=periods,maximum_daily_price_difference_partition_error_USDT=float(np.max(abs(sum(pieces.values())-price))),observed_June_market_decline_exposure=observed_decline,largest_incremental_loss_dates=sorted(rows,key=lambda r:r['incremental_net_USDT'])[:3],largest_absolute_arm_loss_dates=sorted(rows,key=lambda r:r['arm_net_USDT'])[:3],rows=rows)


def run(state,output):
    p=HERE/'evaluate_requests61.py';assert sha(p)=='948f496f6307576832fa47afcfcd7161b0d855456b49ae511da5066d09f2efbd'
    engine=HERE.parent.parent/'scripts/investment/resumable_perpetual.py';assert sha(engine)=='318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585'
    spec=importlib.util.spec_from_file_location('_attribution_frozen_requests_adapter',p);adapter=importlib.util.module_from_spec(spec);sys.modules[spec.name]=adapter;spec.loader.exec_module(adapter)
    context=adapter.contexts(state,False);mapper=adapter.frozen.modules(state).mapper;marks,initial_marks,market_returns,market_sources=markets(state)
    names=ARMS+('STATIC50','CASH50');accounts={name:account(state,name,marks,initial_marks) for name in names};mixes={name:mix(state,adapter,context,mapper,name,accounts[name]) for name in names}
    teacher_path=state/'h1_validation/original/results/e5_h1/teacher/teacher.jsonl';teacher_sha='f47762601544f6e730e617f08f74f80a1e5930540f2da0cdfe77c08bcf70cb6a';assert sha(teacher_path)==teacher_sha
    teacher=[r for r in (json.loads(line) for line in teacher_path.read_text().splitlines()) if START<=r['decision_us']<END];assert [r['decision_us'] for r in teacher]==list(range(START,END,DAY))
    labels=np.array([r['e5_rewards_USDT'][1]-r['e5_rewards_USDT'][4] for r in teacher]);nonterminal=np.arange(61)<60
    arms={};daily=[]
    for name in ARMS:
        ref='CASH50' if 'WITH_CASH' in name else 'STATIC50';a=accounts[name];m=mixes[name];c=compare(a,accounts[ref],market_returns)
        request_pref=np.sign(m['desired'][:,1]-m['desired'][:,4]);budget_pref=np.sign(m['budget'][:,1]-m['budget'][:,4]);weak=abs(labels)>1e-9
        association={}
        for period,mask in (('ALL',nonterminal),('MAY',nonterminal&(np.arange(61)<31)),('JUNE',nonterminal&(np.arange(61)>=31))):
            association[period]=dict(comparable_dates=int((mask&weak).sum()),requested_dominant_pair_weaker_teacher_candidate_dates=int((mask&weak&(request_pref*labels<0)).sum()),ramped_dominant_pair_weaker_teacher_candidate_dates=int((mask&weak&(budget_pref*labels<0)).sum()))
        s=a['summary'];b=accounts[ref]['summary'];directions={side:{k:s['long_short_marked_contribution'][side][k]-b['long_short_marked_contribution'][side][k] for k in ('gross','funding','fees','execution_cost','net_contribution')} for side in ('LONG','SHORT')}
        pairs=c.pop('rows')
        for i,r in enumerate(pairs):r.update(request_CASH=float(m['desired'][i,0]),request_VOL=float(m['desired'][i,1]),request_CS=float(m['desired'][i,4]),ramped_CASH=float(m['budget'][i,0]),ramped_VOL=float(m['budget'][i,1]),ramped_CS=float(m['budget'][i,4]))
        daily.extend(dict(arm=name,reference=ref,**r) for r in pairs)
        arms[name]=dict(primary_reference=ref,**c,allocation={k:v for k,v in m.items() if k not in ('desired','budget')},incremental_long_short_contribution=directions,teacher_state_candidate_rank_association=association,own_summary={k:s[k] for k in ('net_PnL','trade_legs','normalized_total_turnover','minute_max_drawdown','realized_exposure')})
    result=dict(schema='READ_ONLY_FOUR_FROZEN_V2_NATIVE61_ATTRIBUTION_V1',status='PASS_IMMUTABLE_JOURNALS_FULL_DAILY_PRICE_FUND_COST_BRIDGES_AND_INVENTORY_ALGEBRA',arms=arms,
                code=dict(attribution_source_SHA256=sha(Path(__file__)),frozen_adapter_SHA256=sha(p),guard_OFF_financial_engine_SHA256=sha(engine)),source_dataset_manifest_SHA256='8facb75645001306c8179284a057c70ed6c01fc7439b84ffc6f3cb532042cebd',source_account_checks={n:accounts[n]['checks'] for n in names},frozen_requested_budget_mapping={'accounts':6,'daily_asset_targets_each':305,'comparison':'ALL_BIT_IDENTICAL_TO_PRESERVED_JOURNALS'},
                references={n:dict(net_PnL=accounts[n]['summary']['net_PnL'],allocation={k:v for k,v in mixes[n].items() if k not in ('desired','budget')}) for n in ('STATIC50','CASH50')},
                source_account_members={n:accounts[n]['sources'] for n in names},source_actual_mark_members=market_sources,
                teacher_candidate_label=dict(sha256=teacher_sha,scope='EXISTING_NATIVE_GREEDY_TEACHER_SELF_STATE_1DAY_CANDIDATES; NOT_THESE_ARMS_STATES_OR_PURE_SEPARATE_EXPERT_WALLETS',money_or_regret_summed=False,terminal_ties_excluded=True),
                interpretation=dict(primary_reference='Static50 for no-cash, Cash50 for cash-enabled; same admitted action sets but unequal actual risk.',
                  budget='Requested and ramped expert simplex weights are not literal NAV allocation. Netting, individual covariance scaling, .99 sizing, marks and actual fills determine observed gross/net exposure.',
                  price_algebra='At each completed minute, observed price PnL=q_prior*(mark_now-mark_prior)+sum(actual_signed_fill_delta*(mark_now-actual_mid)). Lagged reference inventory is decomposed by actual absolute-USDT gross ratio into proportional size and residual signed composition/timing; fill-to-mark difference is separate. Zero reference gross uses ratio1. This arithmetic creates no executable scaled wallet.',
                  expert_ranking='Weaker-choice counts are ex-post associations conditional on the old teacher wallet, not current-arm native regret; no CS/VOL standalone May-June native accounts are available. They cannot diagnose profitable executable switches.',
                  causal_limits='Independent-account differences are observed comparisons, not causal gains, switching regret or summed oracle payoffs. No controlled same-exposure allocation or timing ablation was run; these data alone do not establish overfitting.'),
                native_wallets_run=0,new_fits=0,models_loaded=0,provider_downloads=0,journals_modified=False)
    output.mkdir(exist_ok=False);(output/'ATTRIBUTION.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (output/'DAILY_DIFFERENCES.csv').open('x',newline='') as f:
        flat=[]
        for row in daily:
            r={k:v for k,v in row.items() if not isinstance(v,dict)}
            for field,prefix in (('price_difference_algebra','price_'),('incremental_asset_price_USDT','asset_price_'),('arm_asset_mean_signed_weight','arm_mean_weight_'),('reference_asset_mean_signed_weight','reference_mean_weight_'),('actual_asset_mark_daily_return','actual_mark_return_')):r.update({prefix+k:v for k,v in row[field].items()})
            flat.append(r)
        writer=csv.DictWriter(f,fieldnames=list(flat[0]),lineterminator='\n');writer.writeheader();writer.writerows(flat)
    print(json.dumps({n:dict(reference=r['primary_reference'],periods=r['periods'],largest_incremental_loss_dates=r['largest_incremental_loss_dates'],allocation=r['allocation'],rank_association=r['teacher_state_candidate_rank_association']) for n,r in arms.items()}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(2_000_000_000,2_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(120,120));run(a.state,a.output)
