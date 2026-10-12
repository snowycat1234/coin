import argparse,gzip,importlib.util,io,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from policy import sleeve_targets,checkpoint_prediction,past_risk_prices
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PREV=ROOT/'research/short-selection-attribution-20261012'
sys.path.insert(0,str(PREV));spec=importlib.util.spec_from_file_location('attr',PREV/'run.py');attr=importlib.util.module_from_spec(spec);spec.loader.exec_module(attr);m=attr.m
SEED=811441;END=m.utc('2022-09-15');ARMS=('GROSS_MATCHED_COUPLED','UNBOUND')

def ci(difference,mask):
    rng=np.random.default_rng(SEED+1);n=len(mask);start=rng.integers(0,n,(1000,int(np.ceil(n/14))))
    ix=((start[:,:,None]+np.arange(14))%n).reshape(1000,-1)[:,:n]
    return np.quantile(np.nanmean(np.where(mask,difference,np.nan)[ix],axis=1),[.025,.975]).tolist()

def risk(source,dates,net):
    out=net.copy();peak=0.
    for j,t in enumerate(dates):
        own=np.flatnonzero(out[j]!=0)
        if not len(own):continue
        past=past_risk_prices(source['close_available_us'],source['close'],t,own,m.DAY_US)
        r=np.diff(past,axis=0)/past[:-1];out[j,own],_=attr.signed_risk_weights(out[j,own],r,annual_vol_target=.10)
        covariance=np.atleast_2d(np.cov(r,rowvar=False,ddof=1))*365;peak=max(peak,float(np.sqrt(max(0.,out[j,own]@covariance@out[j,own]))))
    m.require(peak<=.1+1e-10 and np.abs(out).max()<=.3+1e-12 and np.abs(out).sum(1).max()<=.6+1e-12,'Same risk/caps')
    return out,peak

def native_pair(state,dates,target,source_commit):
    nativepath=ROOT/'research/short-native-activity-20261012';sys.path.insert(0,str(nativepath));spec=importlib.util.spec_from_file_location('native',nativepath/'run.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    b=native.bridge;begin,end=m.utc('2022-01-01'),m.utc('2022-02-01');b.configure(state,'Q12022')
    protocol=json.loads((ROOT/'research/native-mark-inputs-20261011/PROTOCOL.json').read_text())
    tp,tc=b.certificate(protocol['trade_source_commit'],b.TRADE,'Q12022');mp,mc=b.certificate(protocol['mark_source_commit'],b.MARK,'Q12022')
    prevt,_=b.certificate(protocol['trade_source_commit'],b.TRADE,'Y2021');prevm,_=b.certificate(protocol['mark_source_commit'],b.MARK,'DEC2021')
    inv,*_=b.inventories();reader=b.SourceReader(inv,state,local=False);trade={};mark={};daily=[]
    for s in native.SYMBOLS:
        tr=next(r for r in tp['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01');mr=next(r for r in mp['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01')
        m.require(tr['past_boundary']==prevt['end_boundaries'][s] and mr['past_boundary']==prevm['end_boundaries'][s],'Same certifiedprevious boundary')
        tf,te=b.decoded_month(reader,tr['source'],begin//1000,end//1000);mf,me=b.complete_month(reader,mr['source'],begin//1000,end//1000)
        trade[s]=native.source_bars(tf,tr['source'],'klines',added_repair_rows=sum(r['added_actual_rows'] for r in te['repairs']))
        mark[s]=native.source_bars(mf,mr['source'],'markPriceKlines',added_repair_rows=sum(r['added_actual_rows'] for r in me['repairs']))
        for t in range(begin,end,m.DAY_US):daily.append(dict(symbol=s,close_us=t,close=tr['past_boundary']['close'] if t==begin else native.exact_boundary(trade[s],t)['price']))
    reader.close();events,funder=native.fund_events(state,begin,end);chosen=(dates>=begin)&(dates<end);nd=dates[chosen]
    def blocks():
        for t in range(begin,end,m.DAY_US):yield native.legacy_projection(native.day_block(native.SYMBOLS,trade,mark,t))
    out={}
    for arm in ARMS:
        w=target[arm][chosen];native.targets(nd,w,begin,end,begin,native.SYMBOLS)
        def factory(daily,clocks,mode):
            np.testing.assert_array_equal(clocks,nd)
            return native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,j])) for i,t in enumerate(nd) for j,s in enumerate(native.SYMBOLS)]),dict(arm=arm,fit_available_us=begin,source_commit=source_commit)
        window=dict(start=begin,end=end,symbols=native.SYMBOLS,daily=native.pl.DataFrame(daily),events=events,minute_blocks=blocks)
        sim=native.NativeDailySimulator(window,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory)
        while sim.cursor<end and sim.stop is None:sim.advance_day()
        case=sim.result();episodes,quant=native.episodes(case['trades'],native.SYMBOLS)
        for s in native.SYMBOLS:m.require(quant[s]==sim.account.positions[s].quantity,'Exactperassetinventory')
        finance=native.nav_bridge(case['trades'],case['funding'],quant,case['summary']['terminal_mark_prices'],sim.account.nav())
        saved=native.save_case(case,state/(arm+'_ACCOUNT'));summary=saved['summary']
        body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body['summary']=summary;body['targets']=case['targets'].to_dicts();m.save(state/(arm+'_ACCOUNT.json'),body)
        np.savez_compressed(state/(arm+'_MINUTE.npz'),**{k:case['minute'][k].to_numpy() for k in case['minute'].columns})
        # Actual complete scheduler checkpoint, no fabricated summary reconstruction.
        snapshot=sim.snapshot();raw=json.dumps(snapshot,sort_keys=True,allow_nan=False).encode();(state/(arm+'_SNAPSHOT.json.gz')).write_bytes(gzip.compress(raw,mtime=0))
        out[arm]=dict(summary=summary,episodes=episodes,independent_NAV_bridge=finance);print('NEW_NATIVE_PAIR_COMPLETE',arm,summary['NAV'],'paidflat',summary['terminal_cash_realized'],flush=True)
    return dict(new_accounts=2,old_account_reruns=0,trade_certificate=tc,mark_certificate=mc,funding=funder,cases=out)

def run(state,source_commit,expected=None):
    m.require(not state.exists() and not m.git('status','--porcelain'),'FreshSTATE/cleanpublishedsource')
    if not expected:m.require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Sourcepublished')
    m.verify_manifest(HERE/'SOURCE_SHA256.txt');state.mkdir();start=time.monotonic()
    roles,source,frames,holes,v,saved,old,full=attr.load();d=source['decision_us'];known=v['common_feature_known'];x=np.column_stack([source['baseline'],source['targets'].reshape(len(d),-1),source['expert_eligible'],source['asset_eligible'].reshape(len(d),-1)]).astype(float)
    calendar=np.flatnonzero((d>=m.utc('2022-01-01'))&(d<m.utc('2022-09-14')));ed=d[calendar]
    m.require(len(ed)==256 and ed[0]==m.utc('2022-01-01') and ed[-1]==m.utc('2022-09-13') and np.all(np.diff(ed)==m.DAY_US),'Frozen full internal calendar before fit')
    sleeves=pd.read_csv(PREV/'result/TRAIN607_SLEEVE_COSTS.csv').set_index('decision_us');y=sleeves.reindex(d)[['long_utility','short_utility']].to_numpy(float)
    maturity=roles.set_index('decision_us').reward_complete_maturity_us;train=old['training_indices'];trainmature=maturity.loc[d[train]].to_numpy(np.int64)
    m.require(len(train)==181 and np.isfinite(x[train]).all() and np.isfinite(y[train]).all() and (trainmature<m.utc('2021-12-31')).all(),'Sameactualmature181trainingprefix')
    models=dict(mean=old['A_mean'],scale=old['A_scale'],training_indices=train)
    if expected:
        with np.load(io.BytesIO(m.git('show',expected+':research/cs-sleeve-unbinding-20261012/result/MODELS.npz')),allow_pickle=False) as z:models={k:z[k].copy() for k in z.files}
        np.testing.assert_array_equal(train,models['training_indices'])
    else:
        m.save(state/'ATTEMPT.json',dict(attempts=1,new_two_output_Ridge_fits=0,original_model_fits=0,source_commit=source_commit))
        fit_start=time.monotonic();model=Ridge(alpha=30.).fit((x[train]-models['mean'])/models['scale'],y[train]);fit_seconds=time.monotonic()-fit_start
        models['coef']=np.ascontiguousarray(model.coef_);models['intercept']=np.ascontiguousarray(model.intercept_);np.savez_compressed(state/'MODELS.npz',**models)
        with np.load(state/'MODELS.npz',allow_pickle=False) as z:models={k:z[k].copy() for k in z.files}
        m.save(state/'ATTEMPT.json',dict(attempts=1,new_two_output_Ridge_fits=1,original_model_fits=0,fit_seconds=fit_seconds,source_commit=source_commit))
    trainingloss=np.mean((checkpoint_prediction(x[train],models)-y[train])**2,axis=1)
    pd.DataFrame(dict(decision_us=d[train],true_reward_maturity_us=trainmature,effective_loss=trainingloss,objective_weight=1.)).to_csv(state/'ACTUAL_TRAIN_DATES.csv',index=False)
    pred=np.zeros((len(ed),2));good=known[calendar];pred[good]=checkpoint_prediction(x[calendar[good]],models)
    with np.load(ROOT/'research/minute-conditional-selector-20261011/result/VECTORS.npz',allow_pickle=False) as z:
        ridx=np.flatnonzero((z['eval_decision_us']>=ed[0])&(z['eval_decision_us']<=ed[-1]));np.testing.assert_array_equal(z['eval_decision_us'][ridx],ed);budgets=z['A_budgets'][ridx]
    scale=float(old['A_utility_scale']);eligible=np.column_stack([np.ones(len(ed),bool),good&source['expert_eligible'][calendar,2]])
    retention=np.column_stack([attr.budget_path(np.column_stack([np.zeros(len(ed)),pred[:,j]]),scale,cash_index=0,eligible=eligible,max_l1=.1)[0][:,1] for j in range(2)])
    raw,proof=sleeve_targets(source['targets'][calendar],budgets,retention);target={};riskreport={}
    for arm in ARMS:target[arm],riskreport[arm]=risk(source,ed,raw[arm])
    evalmature=maturity.reindex(ed).fillna(np.iinfo(np.int64).max).to_numpy(np.int64)
    mask=np.isin(ed,roles.decision_us)&good&v['label_complete'][calendar].all(1)&(evalmature<END);truth=y[calendar]
    rawloss=np.mean((pred-truth)**2,axis=1);constantloss=np.mean((y[train].mean(0)-truth)**2,axis=1)
    mse=dict(RIDGE=float(rawloss[mask].mean()),TRAIN_MEAN=float(constantloss[mask].mean()));infoCI=ci(constantloss-rawloss,mask);gain=1-mse['RIDGE']/mse['TRAIN_MEAN'];info= gain>=.02 and infoCI[0]>0
    fi=np.searchsorted(frames[tuple(source['symbol_order'])[0]].available_us.to_numpy(np.int64),ed);costs=[];paid={arm:np.full(len(ed),np.nan) for arm in ARMS}
    for arm in ARMS:
        for j in np.flatnonzero(mask):
            result=attr.sleeve_metrics(frames,fi[j],target[arm][j]);paid[arm][j]=result['utility'];costs.append(dict(arm=arm,decision_us=int(ed[j]),**result))
    delta=paid['UNBOUND']-paid['GROSS_MATCHED_COUPLED'];economicCI=ci(delta,mask);economic=economicCI[0]>0;point=float(np.nanmean(delta));native_gate=(info or economic) and point>0
    report=dict(status='PASS_INCREMENT_NATIVE_PROBE_ALLOWED' if native_gate else 'STOP_FIXED_SLEEVE_INCREMENT_GATE',source_commit=source_commit,new_model_fits=1,original_model_or_scaler_fits=0,
        actual_train_dates=len(train),positive_effective_loss_dates=int((trainingloss>0).sum()),small_mechanism_probe_not600date_claim=True,
        fit_available_us=m.utc('2022-01-01'),maximum_train_true_reward_maturity_us=int(trainmature.max()),natural_internal_dates=len(ed),common_mature_dates=int(mask.sum()),
        feature_columns=46,information=dict(MSE=mse,relative_gain=gain,paired95CI=infoCI,gate=bool(info)),
        paid_reference=dict(mean_utility={arm:float(np.nanmean(paid[arm])) for arm in ARMS},unbound_minus_matched_mean=point,paired95CI=economicCI,gate=bool(economic)),
        allocated_CS_gross_matched_each_date=True,target_signed_past30_vol_max=riskreport,
        target_diagnostics={arm:dict(negative_dates=int((target[arm]<-1e-12).any(1).sum()),mean_gross=float(np.abs(target[arm]).sum(1).mean()),mean_short_gross=float(np.maximum(-target[arm],0).sum(1).mean())) for arm in ARMS},
        external59_used=False,forced_short=False,fees_risk_terminal_unchanged=True,old_account_reruns=0,provider_downloads=0,scope='SEEN_TRAINING_INTERNAL_MECHANISM_NOT_NEW_OOS_OR_NATIVE_AUTHORITY')
    np.savez_compressed(state/'VECTORS.npz',decision_us=ed,prediction=pred,retention=retention,common_mature_mask=mask,allocated_CS_gross=proof['allocated_CS_gross'],**{arm+'_targets':w for arm,w in target.items()});pd.DataFrame(costs).to_csv(state/'PAID_REFERENCES.csv',index=False)
    m.require(time.monotonic()-start<120,'Model/stat120sbudget');m.save(state/'PREFIT_NATIVE_GATE.json',report)
    if native_gate:report['native_pair']=native_pair(state,ed,target,source_commit)
    else:report['native_pair']=dict(new_accounts=0,reason='NO_FIXED_INFORMATION_OR_CONDITIONAL_RANK_INCREMENT')
    m.save(state/'RESULT.json',report);m.save(state/'TIMING.json',dict(total_seconds=time.monotonic()-start))
    if expected:
        old_report=json.loads(m.git('show',expected+':research/cs-sleeve-unbinding-20261012/result/RESULT.json'));m.require(report==old_report,'Exactscientificreport')
        names=['ACTUAL_TRAIN_DATES.csv','VECTORS.npz','PAID_REFERENCES.csv']
        if native_gate:names += [arm+suffix for arm in ARMS for suffix in ('_ACCOUNT.json','_MINUTE.npz','_SNAPSHOT.json.gz')]
        for name in names:m.require(m.git('show',expected+':research/cs-sleeve-unbinding-20261012/result/'+name)==(state/name).read_bytes(),'Exactpublic '+name)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_ZERO_FIT_SLEEVE_MECHANISM_RESTORE',new_model_fits=0,old_account_reruns=0,new_verification_accounts=2 if native_gate else 0,artifact_commit=expected))
    m.require(time.monotonic()-start<600,'Overall600sbudget');print(json.dumps({k:v for k,v in report.items() if k!='native_pair'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
