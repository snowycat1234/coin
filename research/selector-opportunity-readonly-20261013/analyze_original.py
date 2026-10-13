"""Read-only saved-wallet/target descriptions. No fitting, replay, or selector profit simulation."""
import calendar, csv, datetime as dt, hashlib, json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent; BASE=HERE.parent; DAY=86_400_000_000
spec={}
for arm,raw in [('CSH','STATIC50'),('SMA','SMA200_10PCT'),('HALF','EXACTHALF'),('HOLD','VOL_MATCHED')]:
    p=BASE/'coin_2021_strategy_comparison_20261013/state_first_authorized_run'/f'Y2021_{raw}_FINE_ORIGINAL'
    spec[2021,arm]=(p/'DAILY.csv',p/'RESULT.json',p/'BINDING.json')
for y in [2023,2025]:
    for arm,raw in [('CSH','STATIC50'),('HOLD','VOL_MATCHED')]:
        p=HERE/'public_inputs';spec[y,arm]=(p/f'Y{y}_{raw}_DAILY.csv',p/f'Y{y}_{raw}_RESULT.json',p/f'Y{y}_{raw}_BINDING.json')
    p=HERE/'inputs';spec[y,'SMA']=(p/f'Y{y}_SMA_DAILY.csv',p/f'Y{y}_SMA_RESULT.json',p/f'Y{y}_SMA_BINDING.json')
    p=BASE/'coin_native_half_mix_20261013'/f'STATE_Y{y}';spec[y,'HALF']=(p/'DAILY.csv',p/'RESULT.json',p/'BINDING.json')
for arm,raw in [('CSH','STATIC50'),('SMA','SMA200_10PCT'),('HALF','EXACTHALF'),('HOLD','VOL_MATCHED')]:
    p=BASE/'coin_expanded_coverage_20261013/wallets'/raw;spec[2024,arm]=(p/'DAILY.csv',p/'RESULT.json',p/'BINDING.json')

data={}; manifest=[]; annual=[]; monthly=[]; states=[]; paired=[]
target={}
for y in [2021,2024]:
    path=BASE/('coin_2021_strategy_comparison_20261013/targets/Y2021.npz' if y==2021 else 'coin_expanded_coverage_20261013/targets/Y2024_TARGETS.npz')
    z=np.load(path,allow_pickle=False);target[y]={'decisions':z['decision_us'],'CSH':z['STATIC50'],'SMA':z['SMA200_10PCT']}
for y in [2023,2025]:
    a=np.load(BASE/f'coin_strong_candidates_20261013/STATIC50_Y{y}.npz',allow_pickle=False)
    b=np.load(BASE/f'coin_strong_candidates_20261013/SMA200_Y{y}.npz',allow_pickle=False)
    assert np.array_equal(a['decision_us'],b['decision_us']) and np.array_equal(a['symbol_order'],b['symbol_order'])
    target[y]={'decisions':a['decision_us'],'CSH':a['STATIC50'],'SMA':b['SMA200_10PCT']}
for (y,arm),(daily,result,binding) in spec.items():
    raw=daily.read_bytes();r=list(csv.DictReader(raw.decode().splitlines()));j=json.loads(result.read_bytes());b=json.loads(binding.read_bytes())
    for row in r:
        for k in row:row[k]=float(row[k])
        row['close_us']=int(row['close_us']);row['decision_us']=row['close_us']-DAY
        row['date']=dt.datetime.fromtimestamp(row['decision_us']/1e6,dt.timezone.utc).date().isoformat();row['month']=row['date'][:7]
    assert r[0]['decision_us']==int(dt.datetime(y,1,1,tzinfo=dt.timezone.utc).timestamp()*1e6)
    assert all(r[i]['close_us']-r[i-1]['close_us']==DAY for i in range(1,len(r)))
    prev={'nav':10000,'cumulative_fees':0,'cumulative_execution_costs':0,'cumulative_funding':0,'cumulative_turnover':0}
    for row in r:
        row['net_pnl']=row['nav']-prev['nav'];row['daily_return']=row['nav']/prev['nav']-1
        for key,label in [('cumulative_fees','fees'),('cumulative_execution_costs','execution'),('cumulative_funding','funding'),('cumulative_turnover','turnover')]:row[label]=row[key]-prev[key]
        row['price_pnl']=row['net_pnl']+row['fees']+row['execution']-row['funding']
        row['start_nav']=prev['nav'];prev=row
    sj=j.get('summary',j);m=j.get('metrics',j)
    profile=b.get('fine_profile_SHA256',b.get('profile_SHA256',b.get('quantity_profile_SHA256')))
    paid=bool(j.get('paid_flat',sj.get('terminal_cash_realized',False)))
    if profile is None:profile=sj.get('contract',{}).get('quantity_profile_SHA256')
    annual.append(dict(year=y,arm=arm,profile=profile,days=len(r),daily_end_nav=r[-1]['nav'],daily_return=r[-1]['nav']/10000-1,terminal_nav=sj.get('NAV',10000+sj.get('marked_PnL_USDT',0)),full_calendar=len(r)==(366 if calendar.isleap(y) else 365),paid_flat=paid,status=j.get('status'),account_status=sj.get('account_status'),stop_us=sj.get('stop_us'),minute_mean_gross=m.get('mean_actual_gross',m.get('mean_actual_gross_weight')),minute_vol=m.get('annual_daily_vol',m.get('actual_daily_annual_vol')),minute_dd=m.get('minute_drawdown',sj.get('all_observation_max_drawdown')),fees=sum(x['fees'] for x in r),execution=sum(x['execution'] for x in r),funding=sum(x['funding'] for x in r),price_pnl=sum(x['price_pnl'] for x in r)))
    data[y,arm]=r
    manifest.append(dict(year=y,arm=arm,daily=str(daily.relative_to(BASE)),daily_SHA256=hashlib.sha256(raw).hexdigest(),result=str(result.relative_to(BASE)),result_SHA256=hashlib.sha256(result.read_bytes()).hexdigest(),binding=str(binding.relative_to(BASE)),binding_SHA256=hashlib.sha256(binding.read_bytes()).hexdigest(),profile=profile,source_index_SHA256=b.get('source_index_SHA256'),target_archive_SHA256=b.get('target_archive_SHA256')))
    for mon in dict.fromkeys(x['month'] for x in r):
        q=[x for x in r if x['month']==mon];expected=calendar.monthrange(y,int(mon[-2:]))[1]
        monthly.append(dict(year=y,month=mon,arm=arm,days=len(q),complete_month=len(q)==expected,net_return=q[-1]['nav']/q[0]['start_nav']-1,net_pnl=sum(x['net_pnl'] for x in q),price_pnl=sum(x['price_pnl'] for x in q),fees=sum(x['fees'] for x in q),execution=sum(x['execution'] for x in q),funding=sum(x['funding'] for x in q),turnover=sum(x['turnover'] for x in q),mean_day_end_gross=float(np.mean([x['gross_weight'] for x in q])),mean_day_end_signed_net=float(np.mean([x['net_signed_weight'] for x in q])) ))
for y in [2021,2023,2024,2025]:
    a=data[y,'CSH'];b=data[y,'SMA'];n=min(len(a),len(b));a=a[:n];b=b[:n]
    assert all(x['close_us']==z['close_us'] for x,z in zip(a,b))
    for mon in dict.fromkeys(x['month'] for x in a):
        ix=[i for i,x in enumerate(a) if x['month']==mon];aa=[a[i] for i in ix];bb=[b[i] for i in ix]
        cr=aa[-1]['nav']/aa[0]['start_nav']-1;sr=bb[-1]['nav']/bb[0]['start_nav']-1
        dp=sum(z['price_pnl']-x['price_pnl'] for x,z in zip(aa,bb));df=sum(z['funding']-x['funding'] for x,z in zip(aa,bb));dc=sum(x['fees']+x['execution']-z['fees']-z['execution'] for x,z in zip(aa,bb));dn=bb[-1]['nav']-bb[0]['start_nav']-aa[-1]['nav']+aa[0]['start_nav'];assert abs(dp+df+dc-dn)<1e-8
        pr=100*(sum(x['price_pnl'] for x in bb)/bb[0]['start_nav']-sum(x['price_pnl'] for x in aa)/aa[0]['start_nav'])
        fr=100*(sum(x['funding'] for x in bb)/bb[0]['start_nav']-sum(x['funding'] for x in aa)/aa[0]['start_nav'])
        cs=100*(sum(x['fees']+x['execution'] for x in aa)/aa[0]['start_nav']-sum(x['fees']+x['execution'] for x in bb)/bb[0]['start_nav'])
        assert abs(pr+fr+cs-100*(sr-cr))<1e-10
        paired.append(dict(year=y,month=mon,days=len(ix),complete_month=len(ix)==calendar.monthrange(y,int(mon[-2:]))[1],csh_return=cr,sma_return=sr,sma_minus_csh_pp=100*(sr-cr),both_lose=cr<0 and sr<0,sma_wins=sr>cr,delta_net_USDT=dn,delta_price_USDT=dp,delta_funding_USDT=df,trading_cost_saving_USDT=dc,delta_price_return_pp=pr,delta_funding_return_pp=fr,trading_cost_saving_return_pp=cs,mean_csh_end_gross=float(np.mean([x['gross_weight'] for x in aa])),mean_sma_end_gross=float(np.mean([x['gross_weight'] for x in bb]))))
    for label in ['CSH_CASH','SMA_NET_LONG','SMA_NET_SHORT','SMA_NET_ZERO']:
        ids=[]
        for i in range(n):
            assert target[y]['decisions'][i]==a[i]['decision_us']
            cw=target[y]['CSH'][i];sw=target[y]['SMA'][i]
            lab='CSH_CASH' if sum(abs(cw))<1e-12 else ('SMA_NET_LONG' if sum(sw)>1e-12 else ('SMA_NET_SHORT' if sum(sw)<-1e-12 else 'SMA_NET_ZERO'))
            if lab==label:ids.append(i)
        if not ids:continue
        aa=[a[i] for i in ids];bb=[b[i] for i in ids]
        states.append(dict(year=y,state=label,days=len(ids),delta_net_USDT=sum(z['net_pnl']-x['net_pnl'] for x,z in zip(aa,bb)),delta_price_USDT=sum(z['price_pnl']-x['price_pnl'] for x,z in zip(aa,bb)),delta_funding_USDT=sum(z['funding']-x['funding'] for x,z in zip(aa,bb)),trading_cost_saving_USDT=sum(x['fees']+x['execution']-z['fees']-z['execution'] for x,z in zip(aa,bb)),sma_better_days=sum(z['daily_return']>x['daily_return'] for x,z in zip(aa,bb)),mean_csh_target_gross=float(np.mean(np.abs(target[y]['CSH'][ids]).sum(1))),mean_sma_target_gross=float(np.mean(np.abs(target[y]['SMA'][ids]).sum(1)))))
def write_csv(name,rows):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write_csv('MONTHLY.csv',monthly);write_csv('SMA_CSH_MONTHLY.csv',paired);write_csv('STATE_ATTRIBUTION.csv',states)
summary=[]
for y in [2021,2023,2024,2025]:
    p=[x for x in paired if x['year']==y];complete=[x for x in p if x['complete_month']]
    a=data[y,'CSH'];b=data[y,'SMA'];n=min(len(a),len(b));a=a[:n];b=b[:n]
    summary.append(dict(year=y,common_days=n,common_end_date=a[-1]['date'],csh_common_return=a[-1]['nav']/10000-1,sma_common_return=b[-1]['nav']/10000-1,sma_winning_complete_months=[x['month'] for x in complete if x['sma_wins']],joint_losing_complete_months=[x['month'] for x in complete if x['both_lose']],sma_positive_winning_complete_months=[x['month'] for x in complete if x['sma_wins'] and x['sma_return']>0],positive_delta_price_complete_months=[x['month'] for x in complete if x['delta_price_USDT']>0],common_delta_price_USDT=sum(x['delta_price_USDT'] for x in p),common_delta_funding_USDT=sum(x['delta_funding_USDT'] for x in p),common_trading_cost_saving_USDT=sum(x['trading_cost_saving_USDT'] for x in p),common_delta_net_USDT=b[-1]['nav']-a[-1]['nav'],daily_return_correlation=float(np.corrcoef([x['daily_return'] for x in a],[x['daily_return'] for x in b])[0,1])))
output=dict(scope='SAVED_ACCOUNTS_ONLY_DESCRIPTIVE_NOT_SELECTOR_RETURN_NOT_OOS',funding='RAW_AS_FRACTION_UNCERTIFIED',fees='BASE27_5.5_FEE_4_SPREAD_4_SLIPPAGE_PER_SIDE',new_wallets=0,fits=0,provider_downloads=0,annual=annual,paired_summary=summary,states=states,manifest=manifest)
(HERE/'RESULT.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(dict(paired_summary=summary,states=states),indent=2))
