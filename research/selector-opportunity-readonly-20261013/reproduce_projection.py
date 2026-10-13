"""Zero-fit reproduction from the minimal saved-day projection, with hash/bridge checks."""
import argparse, calendar, csv, datetime as dt, hashlib, json
from pathlib import Path
import numpy as np

DAY=86_400_000_000
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists(),'Output must be fresh; never overwrite an earlier record.'
    src=args.input.resolve();ident=json.loads((src/'SOURCE_IDENTITIES.json').read_bytes());raw=(src/'DAILY_PROJECTION.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ident['projection_sha256']
    rows=list(csv.DictReader(raw.decode().splitlines()));assert len(rows)==ident['rows']==5798
    data={};monthly=[];paired=[];states=[]
    for rr in rows:
        y=int(rr.pop('year'));arm=rr.pop('arm');r={k:float(v) for k,v in rr.items() if v!=''};r['close_us']=int(r['close_us']);r['decision_us']=r['close_us']-DAY
        r['date']=dt.datetime.fromtimestamp(r['decision_us']/1e6,dt.timezone.utc).date().isoformat();r['month']=r['date'][:7];data.setdefault((y,arm),[]).append(r)
    assert len(data)==16
    for (y,arm),r in data.items():
        prev={'nav':10000,'cumulative_fees':0,'cumulative_execution_costs':0,'cumulative_funding':0,'cumulative_turnover':0}
        for i,x in enumerate(r):
            if i:assert x['close_us']-r[i-1]['close_us']==DAY
            else:assert x['date']==f'{y}-01-01'
            x['net_pnl']=x['nav']-prev['nav'];x['daily_return']=x['nav']/prev['nav']-1
            for key,label in [('cumulative_fees','fees'),('cumulative_execution_costs','execution'),('cumulative_funding','funding'),('cumulative_turnover','turnover')]:x[label]=x[key]-prev[key]
            x['price_pnl']=x['net_pnl']+x['fees']+x['execution']-x['funding'];x['start_nav']=prev['nav'];prev=x
        a=next(z for z in ident['annual_original_metadata'] if z['year']==y and z['arm']==arm)
        assert len(r)==a['days'] and r[-1]['nav']==a['daily_end_nav']
        for mon in dict.fromkeys(x['month'] for x in r):
            q=[x for x in r if x['month']==mon];expected=calendar.monthrange(y,int(mon[-2:]))[1]
            monthly.append(dict(year=y,month=mon,arm=arm,days=len(q),complete_month=len(q)==expected,net_return=q[-1]['nav']/q[0]['start_nav']-1,net_pnl=sum(x['net_pnl'] for x in q),price_pnl=sum(x['price_pnl'] for x in q),fees=sum(x['fees'] for x in q),execution=sum(x['execution'] for x in q),funding=sum(x['funding'] for x in q),turnover=sum(x['turnover'] for x in q),mean_day_end_gross=float(np.mean([x['gross_weight'] for x in q])),mean_day_end_signed_net=float(np.mean([x['net_signed_weight'] for x in q]))))
    for y in [2021,2023,2024,2025]:
        profiles={x['profile'] for x in ident['annual_original_metadata'] if x['year']==y};assert len(profiles)==1
        a=data[y,'CSH'];b=data[y,'SMA'];n=min(len(a),len(b));a=a[:n];b=b[:n];assert all(x['close_us']==z['close_us'] for x,z in zip(a,b))
        for mon in dict.fromkeys(x['month'] for x in a):
            ix=[i for i,x in enumerate(a) if x['month']==mon];aa=[a[i] for i in ix];bb=[b[i] for i in ix]
            cr=aa[-1]['nav']/aa[0]['start_nav']-1;sr=bb[-1]['nav']/bb[0]['start_nav']-1
            dp=sum(z['price_pnl']-x['price_pnl'] for x,z in zip(aa,bb));df=sum(z['funding']-x['funding'] for x,z in zip(aa,bb));dc=sum(x['fees']+x['execution']-z['fees']-z['execution'] for x,z in zip(aa,bb));dn=bb[-1]['nav']-bb[0]['start_nav']-aa[-1]['nav']+aa[0]['start_nav'];assert abs(dp+df+dc-dn)<1e-8
            pr=100*(sum(x['price_pnl'] for x in bb)/bb[0]['start_nav']-sum(x['price_pnl'] for x in aa)/aa[0]['start_nav']);fr=100*(sum(x['funding'] for x in bb)/bb[0]['start_nav']-sum(x['funding'] for x in aa)/aa[0]['start_nav']);cs=100*(sum(x['fees']+x['execution'] for x in aa)/aa[0]['start_nav']-sum(x['fees']+x['execution'] for x in bb)/bb[0]['start_nav']);assert abs(pr+fr+cs-100*(sr-cr))<1e-10
            paired.append(dict(year=y,month=mon,days=len(ix),complete_month=len(ix)==calendar.monthrange(y,int(mon[-2:]))[1],csh_return=cr,sma_return=sr,sma_minus_csh_pp=100*(sr-cr),both_lose=cr<0 and sr<0,sma_wins=sr>cr,delta_net_USDT=dn,delta_price_USDT=dp,delta_funding_USDT=df,trading_cost_saving_USDT=dc,delta_price_return_pp=pr,delta_funding_return_pp=fr,trading_cost_saving_return_pp=cs,mean_csh_end_gross=float(np.mean([x['gross_weight'] for x in aa])),mean_sma_end_gross=float(np.mean([x['gross_weight'] for x in bb]))))
        for label in ['CSH_CASH','SMA_NET_LONG','SMA_NET_SHORT','SMA_NET_ZERO']:
            ids=[]
            for i in range(n):
                lab='CSH_CASH' if a[i]['target_gross']<1e-12 else ('SMA_NET_LONG' if b[i]['target_net']>1e-12 else ('SMA_NET_SHORT' if b[i]['target_net']<-1e-12 else 'SMA_NET_ZERO'))
                if lab==label:ids.append(i)
            if not ids:continue
            aa=[a[i] for i in ids];bb=[b[i] for i in ids]
            states.append(dict(year=y,state=label,days=len(ids),delta_net_USDT=sum(z['net_pnl']-x['net_pnl'] for x,z in zip(aa,bb)),delta_price_USDT=sum(z['price_pnl']-x['price_pnl'] for x,z in zip(aa,bb)),delta_funding_USDT=sum(z['funding']-x['funding'] for x,z in zip(aa,bb)),trading_cost_saving_USDT=sum(x['fees']+x['execution']-z['fees']-z['execution'] for x,z in zip(aa,bb)),sma_better_days=sum(z['daily_return']>x['daily_return'] for x,z in zip(aa,bb)),mean_csh_target_gross=float(np.mean([x['target_gross'] for x in aa])),mean_sma_target_gross=float(np.mean([x['target_gross'] for x in bb]))))
    args.output.mkdir(parents=True)
    checks=[]
    for name,rr in [('MONTHLY.csv',monthly),('SMA_CSH_MONTHLY.csv',paired),('STATE_ATTRIBUTION.csv',states)]:
        p=args.output/name
        with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
        assert p.read_bytes()==(src/name).read_bytes(),name
        checks.append(dict(file=name,rows=len(rr),SHA256=hashlib.sha256(p.read_bytes()).hexdigest(),exact_bytes=True))
    assert len(paired)==47 and sum(x['complete_month'] for x in paired)==46
    receipt=dict(status='PASS_EXACT_PROJECTION_AGGREGATION_ONLY',projection_rows=5798,checks=checks,all_47_money_and_return_bridges=True,source_and_wallet_restoration=False,new_wallets=0,new_targets=0,fits=0,provider_downloads=0,financial_imports=0)
    (args.output/'REPRODUCTION.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
