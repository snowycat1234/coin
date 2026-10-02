"""UNRUN D036: one independent saved-ledger statistic check, never account replay.
Pinned metadata guards reused; daily centered-dot/rankdata and Polars minute
aggregates are independent of the producer's statistic implementation.
"""
from pathlib import Path
from datetime import UTC, date, datetime, timedelta
import argparse, gc, hashlib, importlib.util, math, os, resource, signal, sys, time, traceback
import numpy as np
import polars as pl
from scipy.stats import rankdata
from quant import resources

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
GUARDS=ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARDS_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
ARCHIVE=ROOT/'docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_INDEPENDENT_SOURCE_20261003_V1.py'
OUT=ROOT/'reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_INDEPENDENT_AUDIT_20261003_V1.json'
STATUS='PASS_D036_SAVED_PUBLIC_PAIR_STATISTICS_AND_SOURCE_BINDINGS_NOT_ENSEMBLE_OR_APR'
ACTUAL_STATUS='COMPLETE_D036_SAVED_PUBLIC_PAIR_COMPLEMENTARITY_DIAGNOSTIC_NOT_ENSEMBLE_OR_LONG_TERM_APR'
MINUTE=60_000_000; DAY=86_400_000_000; CASH_TOL=1e-7; RATIO_TOL=1e-12
FEE_PATH='protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json'
FEE_SHA='d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f'
FINANCE_AST='39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73'
STARTED=time.monotonic(); RSS=1_000_000_000
P='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'; H='COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
FIXED=(('CONT547','2024-01-01','2025-07-01',547),('CONT122','2025-08-01','2025-12-01',122),('CONT90','2025-12-01','2026-03-01',90))
PROOFS={
 'reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json':('c7033ef299071f1d3149381fc19d923487bbbdd1040c4b20c75481058203441d','PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'),
 'reports/fast_research/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json':('70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f','PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE'),
 'reports/fast_research/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json':('a1af8448c0b44b6e79cbb0123f942bde05b773f90ebb01b0a7b751c4f23f77c9','PASS_HYBRID_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE')}
DAILY=('date','nav','return','cash','fees','execution_costs','turnover','gross_weight','stale_prices','stale_exposure')
PROJECTED=('close_us','nav','gross_weight','BTCUSDT_marked_notional','ETHUSDT_marked_notional')
FILES=('daily_nav.parquet','minute_nav_inventory.parquet')
ERRORS=dict(cash_USDT=0.,ratio=0.)

def check(ok,why):
    if not bool(ok): raise ValueError(why)
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def budget():
    check(time.monotonic()-STARTED<=300 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=RSS,'Frozen300s/1GB independent budget')
def stamp(value): return int(datetime.combine(date.fromisoformat(value),datetime.min.time(),UTC).timestamp())*1_000_000
def guards():
    check(sha(GUARDS)==GUARDS_SHA,'Accepted small metadata guard source SHA')
    module_spec=importlib.util.spec_from_file_location('d036_accepted_metadata_guards',GUARDS)
    module=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module); return module
def ratio(a,b): return float(a/b) if b else None
def corr(x,y):
    if len(x)<2 or np.ptp(x)==0 or np.ptp(y)==0:
        return dict(pearson=None,spearman=None,reason='UNDEFINED_CONSTANT_OR_INSUFFICIENT_SERIES')
    def centered(left,right):
        a=left-math.fsum(left)/len(left); b=right-math.fsum(right)/len(right)
        return float(np.dot(a,b)/math.sqrt(float(np.dot(a,a))*float(np.dot(b,b))))
    return dict(pearson=centered(x,y),spearman=centered(rankdata(x,method='average'),rankdata(y,method='average')),reason=None)
def compare(expected,published,path=''):
    if isinstance(expected,dict):
        check(isinstance(published,dict),'Published statistic object: '+path)
        for key,value in expected.items():
            check(key in published,'Published statistic missing: '+path+'.'+key)
            compare(value,published[key],path+'.'+key)
    elif isinstance(expected,list): check(expected==published,'Exact ranked UTC dates: '+path)
    elif expected is None: check(published is None,'Undefined statistic must stay null: '+path)
    elif type(expected) is bool or type(expected) is int or isinstance(expected,str): check(type(published)==type(expected) and expected==published,'Exact statistic: '+path)
    else:
        check(type(published) in (int,float) and math.isfinite(float(published)) and math.isfinite(float(expected)),'Finite statistic: '+path)
        money=any(key in path for key in ('PnL_USDT','.fees','.spread_cost','.slippage_cost','.execution_costs'))
        error=abs(float(expected)-float(published)); kind='cash_USDT' if money else 'ratio'; ERRORS[kind]=max(ERRORS[kind],error)
        check(error<=(CASH_TOL if money else RATIO_TOL),'Independent statistic differs: '+path)
def conditional(mask,own,other):
    own_loss=-math.fsum(own[own<0]); other_loss=-math.fsum(other[other<0]); n=int(mask.sum())
    return dict(days=n,own_signed_PnL_USDT=math.fsum(own[mask]),other_signed_PnL_USDT=math.fsum(other[mask]),
        other_negative_fraction=ratio(int(np.sum(other[mask]<0)),n),
        own_negative_loss_share=ratio(-math.fsum(own[mask&(own<0)]),own_loss),other_negative_loss_share=ratio(-math.fsum(other[mask&(other<0)]),other_loss))
def owned(paths):
    total=0
    for folder in paths:
        check(folder.parent==STATE and folder.is_dir() and not folder.is_symlink() and folder.name.startswith('d036-'),'Dedicated D036 ownership only')
        for current,dirs,files in os.walk(folder,followlinks=False):
            check(not any((Path(current)/name).is_symlink() for name in dirs+files),'No ownership symlinks')
            total+=sum((Path(current)/name).stat().st_size for name in files)
    check(total<=5_000_000,'Observed producer+independent STATE within combined5MB'); return total

def metadata(g,spec,actual,protocol_sha):
    check(actual['status']==ACTUAL_STATUS and actual['completed_periods']==3 and actual['completed_files']==12 and actual['source_bytes_unchanged'],'Fresh complete diagnostic, not partial')
    task=g.closed(actual['binding']['task_id']); record=task['task']; check(record['pid']>0 and record['start_ticks']>0,'Real completed diagnostic process')
    run=Path(actual['run_dir']); binding,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256'])
    check(binding==actual['binding'] and binding['protocol_sha256']==protocol_sha and str(run)==spec['run_dir'],'Actual RUN_BINDING/protocol routing')
    check(binding['source_hashes']==spec['frozen_sources'] and actual['calculation_rules']==spec['calculation_rules'] and actual['decision_rule']==spec['decision_rule'],'Exact frozen input and calculation/decision scope')
    check(actual['models_fit']==actual['orders_sent']==actual['GPU']==0 and not actual['locked_consumed'] and not actual['ensemble_NAV_generated'] and not actual['native_account_certified'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','No account/market/qualification reinterpretation')
    check(spec['classification']=='SCREENING_SAVED_LEDGER_COMPLEMENTARITY_NOT_ENSEMBLE' and spec['budgets']['peak_RSS_bytes']==RSS and spec['budgets']['wall_seconds']==300 and spec['budgets']['module_combined_STATE_bytes']==5_000_000,'Preregistered scope/resources')
    rules=spec['calculation_rules']; check(rules['cash_tolerance']==CASH_TOL and rules['ratio_tolerance']==RATIO_TOL and rules['tail_fraction']==.10 and rules['no_ensemble_NAV'] and rules['periods_independent'],'Fixed statistics/tolerances; no combined NAV')
    fee=spec['fee_profile']; check(fee==dict(path=FEE_PATH,sha256=FEE_SHA,market_type='SPOT',fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1',fee_bps_per_side=10,half_spread_bps_per_side=4,slippage_bps_per_side=4,nominal_roundtrip_bps=36,data_venue='Binance',fee_reference_venue='Bybit',native_market_certified=False)
        and spec['frozen_sources'].get(FEE_PATH)==FEE_SHA,'Original accepted native-fee proxy36bp')
    for relative,digest in binding['source_hashes'].items():
        g.small(g.project(relative),digest,False); g.small(run/'source-snapshot'/relative,digest,False)
    proofs=[]
    for relative,(digest,status) in PROOFS.items():
        check(spec['frozen_sources'].get(relative)==digest,'Original accepted independent scope SHA')
        value,_=g.small(g.project(relative),digest); check(value['status']==status,'Original partial/composite scope not relabeled fresh'); proofs.extend(value['ledgers'])
    contexts=[]; artifacts=[]
    check(len(spec['periods'])==3 and len(actual['cases'])==3,'All separate windows, no pooled selector')
    for period,(identifier,start,end,days) in zip(spec['periods'],FIXED,strict=True):
        check((period['id'],period['start'],period['end_exclusive'],period['days'],period['minutes'],period['initial_nav'])==(identifier,start,end,days,days*1440,10000),'Exact fixed window/calendar/capital')
        check(set(period['legs'])=={'P','H'},'Exactly two strategy legs')
        legs={}; producers={}
        for side,strategy in (('P',P),('H',H)):
            item=period['legs'][side]; check(item['strategy']==strategy and spec['frozen_sources'].get(item['producer_path'])==item['producer_sha256'],'Pinned original producer/strategy')
            producer,_=g.small(g.project(item['producer_path']),item['producer_sha256']); producers[side]=producer
            check(producer['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and producer['all_planned_ledgers_complete'] and producer['source_bytes_unchanged'],'Existing accepted complete account')
            folds=[f for f in producer['folds'] if f['fold']==identifier]; check(len(folds)==1 and folds[0]['days']==days and folds[0]['start_us']==stamp(start) and folds[0]['end_us']==stamp(end),'Original whole window')
            rows=[r for r in folds[0]['results'] if r['strategy']==strategy and r['spread_bps']==8]
            audit_rows=[r for r in proofs if r['fold']==identifier and r['strategy']==strategy and r['spread_bps']==8]
            check(len(rows)==len(audit_rows)==1 and rows[0]['nominal_roundtrip_bps']==36,'Unique original accepted ledger selector')
            row=rows[0]; summary=row['summary']; check(summary['initial_nav']==10000 and summary['period_days']==days and set(item['artifacts'])==set(FILES),'Same initial capital and12 allowed artifacts')
            check(summary['fee_settlement_version']=='BYBIT_SPOT_RECEIVED_ASSET_V1' and summary['bybit_fee_profile_sha256']==FEE_SHA and summary['derived_AST_SHA256']==FINANCE_AST
                and not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven'],'Reuse accepted exact fee/cost and qualification scope only')
            for name in FILES:
                artifact=item['artifacts'][name]; prior=row['artifacts'][name]
                check(artifact==dict(path=str(Path(row['directory'])/name),sha256=prior['sha256'],bytes=prior['bytes'],rows=days if name==FILES[0] else days*1440)
                    and audit_rows[0]['ledger_artifact_hashes'][name]==artifact['sha256'],'Exact old producer/audit artifact SHA/path/size/count')
                artifacts.append(dict(period=identifier,side=side,filename=name,**artifact))
            legs[side]=dict(summary=row['summary'],artifacts=item['artifacts'])
        check(producers['P']['minute_source']['sha256']==producers['H']['minute_source']['sha256'] and producers['P']['source_receipt_sha256']==producers['H']['source_receipt_sha256']
            and producers['P']['registration_start']['hyperparameters']==producers['H']['registration_start']['hyperparameters'],'Same source/capital/risk rule, not matched actual vol')
        contexts.append((period,legs))
    check(len(artifacts)==12 and len({a['path'] for a in artifacts})==12,'Twelve unique saved ledger files only')
    check(spec['budgets']['input_bytes']==sum(a['bytes'] for a in artifacts) and spec['budgets']['input_files']==12 and spec['budgets']['additional_market_copy_bytes']==0,'Exact saved input bytes, no market copy')
    check({(a['period'],a['side'],a['filename'],a['path'],a['sha256'],a['bytes'],a['rows']) for a in artifacts}
        =={(a['period'],a['side'],a['filename'],a['path'],a['sha256'],a['bytes'],a['rows']) for a in actual['input_bindings']},'Fresh diagnostic uses exactly these12 inputs')
    for item in artifacts:
        original=Path(item['path']); path=original.resolve(); check(path==original and path.is_relative_to(STATE) and path.is_file() and path.suffix=='.parquet','Immutable exact saved ledger path')
        for ancestor in (path,*path.parents):
            check(not ancestor.is_symlink(),'No saved artifact symlinks')
            if ancestor==STATE: break
        check(path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'Exact ledger bytes before any arrays')
    g.bounded(actual['resources_before']); g.bounded(actual['resources_after'])
    check(actual['peak_RSS_bytes']<=RSS and actual['elapsed_seconds']<=300,'Completed diagnostic runtime budget')
    return contexts,artifacts,task

def read_daily(item,period,summary):
    frame=pl.read_parquet(item['path'],columns=DAILY); n=period['days']
    expected=[date.fromisoformat(period['start'])+timedelta(days=i) for i in range(n)]
    check(frame.height==n and frame.schema['date']==pl.Date and frame['date'].to_list()==expected and frame.null_count().sum_horizontal().sum()==0,'Complete ordered UTC day rows')
    check(not frame['stale_prices'].any() and not frame['stale_exposure'].any(),'No stale saved valuations')
    check(np.isfinite(frame.select(pl.exclude('date','stale_prices','stale_exposure')).to_numpy()).all(),'Finite saved daily fields')
    nav=frame['nav'].to_numpy(); previous=np.r_[10000.,nav[:-1]]; delta=nav-previous; ret=delta/previous
    check(np.all(nav>0) and np.max(np.abs(ret-frame['return'].to_numpy()))<=RATIO_TOL,'Recorded continuous net return identity')
    for field,saved in (('fees','fees'),('execution_costs','execution_costs'),('turnover','turnover')):
        compare(math.fsum(frame[field].to_numpy()),summary[saved],'daily.'+field)
    compare(float(nav[-1]-10000),summary['net_cash_PnL'],'daily.net_PnL_USDT')
    compare(math.fsum(delta)+math.fsum(frame['fees'].to_numpy())+math.fsum(frame['execution_costs'].to_numpy()),summary['gross_cash_PnL_same_quantities'],'daily.gross_PnL_USDT')
    return dict(nav=nav,pnl=delta,returns=ret,dates=expected)

def exposure(period,legs,daily):
    frames={}; start,end=stamp(period['start']),stamp(period['end_exclusive'])
    for side in ('P','H'):
        frame=pl.read_parquet(legs[side]['artifacts'][FILES[1]]['path'],columns=PROJECTED)
        check(frame.height==period['minutes'] and frame.schema['close_us']==pl.Int64 and frame.null_count().sum_horizontal().sum()==0,'Complete original integer minute rows')
        close=frame['close_us']; check(close[0]==start+MINUTE and close[-1]==end and close.diff().drop_nulls().eq(MINUTE).all(),'Exclusive full UTC minute close grid')
        check(frame.select(pl.all_horizontal([pl.col(c).is_finite() for c in PROJECTED[1:]]).all()).item() and frame['nav'].min()>0,'Finite positive minute NAV')
        check(frame.select(pl.all_horizontal([pl.col(c)>=0 for c in PROJECTED[-2:]]).all()).item(),'Long-only actual marked holdings')
        error=frame.select(((pl.col(PROJECTED[-2])+pl.col(PROJECTED[-1]))/pl.col('nav')-pl.col('gross_weight')).abs().max()).item(); check(error<=RATIO_TOL,'Actual marked weight identity')
        ends=frame.filter(pl.col('close_us')%DAY==0); check(ends.height==period['days'],'All daily exclusive endpoints')
        check(ends['close_us'].to_list()==[start+(i+1)*DAY for i in range(period['days'])],'Daily date is next UTC00:00')
        check(max(abs(a-b) for a,b in zip(ends['nav'].to_list(),daily[side]['nav'],strict=True))<=CASH_TOL,'Saved daily/minute endpoint NAV matches')
        frames[side]=frame.select('close_us',*( (pl.col(symbol+'_marked_notional')/pl.col('nav')).alias(side+symbol) for symbol in ('BTCUSDT','ETHUSDT')))
    joined=frames['P'].join(frames['H'],on='close_us',how='inner',validate='1:1'); check(joined.height==period['minutes'],'No minute lost in exact pair join')
    joined=joined.with_columns((pl.col('PBTCUSDT')+pl.col('PETHUSDT')).alias('pg'),(pl.col('HBTCUSDT')+pl.col('HETHUSDT')).alias('hg'))
    value=joined.select((pl.min_horizontal('PBTCUSDT','HBTCUSDT')+pl.min_horizontal('PETHUSDT','HETHUSDT')).sum().alias('min_sum'),
        (pl.max_horizontal('PBTCUSDT','HBTCUSDT')+pl.max_horizontal('PETHUSDT','HETHUSDT')).sum().alias('max_sum'),
        ((pl.col('pg')>0)&(pl.col('hg')>0)).sum().alias('both'),((pl.col('pg')>0)|(pl.col('hg')>0)).sum().alias('either'),
        pl.col('pg').mean().alias('meanp'),pl.col('hg').mean().alias('meanh')).row(0,named=True)
    overlap=dict(strict_positive_including_dust=True,actual_marked_positions_not_targets=True,both_active_fraction=value['both']/period['minutes'],either_active_fraction=value['either']/period['minutes'],
        active_time_Jaccard=ratio(value['both'],value['either']),active_indicator_correlation=corr((joined['pg'].to_numpy()>0).astype(float),(joined['hg'].to_numpy()>0).astype(float)),
        gross_weight_correlation=corr(joined['pg'].to_numpy(),joined['hg'].to_numpy()),mean_gross_weight_P=value['meanp'],mean_gross_weight_H=value['meanh'],matched_asset_weight_overlap=ratio(value['min_sum'],value['max_sum']),
        weight_overlap_status='DEFINED' if value['max_sum']>0 else 'UNKNOWN_ZERO_DENOMINATOR',per_asset={})
    for symbol in ('BTCUSDT','ETHUSDT'):
        aggregate=joined.select(pl.min_horizontal('P'+symbol,'H'+symbol).sum().alias('a'),pl.max_horizontal('P'+symbol,'H'+symbol).sum().alias('b')).row(0,named=True)
        overlap['per_asset'][symbol]=dict(weight_overlap=ratio(aggregate['a'],aggregate['b']),weight_correlation=corr(joined['P'+symbol].to_numpy(),joined['H'+symbol].to_numpy()))
    return overlap

def statistics(period,legs):
    daily={s:read_daily(legs[s]['artifacts'][FILES[0]],period,legs[s]['summary']) for s in ('P','H')}
    dp,dh=daily['P']['pnl'],daily['H']['pnl']; both=(dp<0)&(dh<0); n=period['days']; k=math.ceil(.1*n); tails={}; masks={}; eligibility={}; sensitive=[]
    for side,own,other in (('P',dp,dh),('H',dh,dp)):
        selected=sorted(range(n),key=lambda i:(float(own[i]),daily['P']['dates'][i]))[:k]; mask=np.zeros(n,dtype=bool); mask[selected]=True; masks[side]=mask
        negative_count=int(np.sum(own<0)); eligibility[side]=negative_count>=k
        tails[side]={**conditional(mask,own,other),'k':k,'negative_day_count':negative_count,'all_k_negative':all(own[i]<0 for i in selected),
            'tail_status':'QUALIFIED_FIXED_NEGATIVE_TAIL' if eligibility[side] else 'UNKNOWN_INSUFFICIENT_NEGATIVE_DAYS',
            'UTC_dates':[str(daily['P']['dates'][i]) for i in selected],'selection_uses_saved_outcomes_not_a_trading_signal':True}
        total=tails[side]['other_signed_PnL_USDT']
        tails[side].update(other_leg_tail_net_PnL_USDT=total,other_leg_offset_point_condition=total>=0,other_rounding_sensitive=abs(total)<=CASH_TOL,
            offset_interpretation='CASH_EQUIVALENT_ZERO_AT_POINT' if total==0 else ('POSITIVE_OTHER_LEG_PNL' if total>0 else 'NEGATIVE_OTHER_LEG_PNL'))
        if abs(total)<=CASH_TOL: sensitive.append(dict(side=side,other_tail_signed_net_PnL_USDT=total,point_predicate_ge_zero=total>=0,exact_zero=total==0,comparison_tolerance_USDT=CASH_TOL))
    intersection=int(np.sum(masks['P']&masks['H'])); valid=all(eligibility.values())
    metrics=dict(period=period['id'],days=n,minutes=period['minutes'],net_return={s:float(daily[s]['nav'][-1]/10000-1) for s in ('P','H')},
        net_PnL_USDT={s:float(daily[s]['nav'][-1]-10000) for s in ('P','H')},
        saved_costs={s:{key:legs[s]['summary'][key] for key in ('fees','spread_cost','slippage_cost','turnover','trade_count')} for s in ('P','H')},
        daily_PnL_correlation=corr(dp,dh),daily_net_return_correlation=corr(daily['P']['returns'],daily['H']['returns']),co_negative_days=int(both.sum()),co_negative_fraction_all_days=float(both.mean()),
        on_P_negative_days=conditional(dp<0,dp,dh),on_H_negative_days=conditional(dh<0,dh,dp),both_negative_loss_concentration={s:conditional(both,own,other) for s,own,other in (('P',dp,dh),('H',dh,dp))},
        worst_10_percent_days=tails,worst_tail_intersection_days=intersection,worst_tail_intersection_fraction=intersection/k,
        worst_tail_overlap_status='DEFINED' if valid else 'UNKNOWN_INSUFFICIENT_NEGATIVE_DAYS',
        actual_marked_exposure_overlap=exposure(period,legs,daily),no_ensemble_NAV_or_return_generated=True,summary_scope='DESCRIPTIVE_SAVED_LEDGER_NOT_COMMON_ACCOUNT_OR_APR')
    facts=dict(tail_count=k,negative_days={s:int(np.sum(daily[s]['pnl']<0)) for s in ('P','H')},tail_eligible=eligibility,
        rounding_sensitive_offsets=sensitive,UNKNOWN_statistics_never_PASS=True,exposure_aggregate_path='POLARS_MIN_MAX_EXPRESSIONS_PER_WINDOW_NOT_POOLED')
    return metrics,facts

def decision(cases,facts,rules):
    check(rules['criteria']=='ALL' and rules['later_period_daily_PnL_Pearson_max_exclusive']==.8 and rules['later_period_worst10pct_tail_overlap_max_exclusive']==.7 and rules['every_period_weighted_min_max_exposure_overlap_max_exclusive']==.8,'Exact preregistered four budget rules')
    later=[c for c in cases if c['period'] in ('CONT122','CONT90')]; check(len(later)==2,'Both later windows, no selector choice')
    pearson={c['period']:c['daily_PnL_correlation']['pearson'] is not None and c['daily_PnL_correlation']['pearson']<.8 for c in later}
    tail={c['period']:c['worst_tail_overlap_status']=='DEFINED' and c['worst_tail_intersection_fraction']<.7 for c in later}
    protect={c['period']:any(facts[c['period']]['tail_eligible'][s] and c['worst_10_percent_days'][s]['other_signed_PnL_USDT']>=0 for s in ('P','H')) for c in cases}
    overlap={c['period']:c['actual_marked_exposure_overlap']['matched_asset_weight_overlap'] is not None and c['actual_marked_exposure_overlap']['matched_asset_weight_overlap']<.8 for c in cases}
    details=dict(later_daily_PnL_Pearson=pearson,later_worst10pct_overlap=tail,tail_other_signed_net_PnL_nonnegative=protect,
        two_periods_including_a_later_offset=sum(protect.values())>=2 and any(protect[c['period']] for c in later),every_period_weighted_min_max_exposure_overlap=overlap,
        scope='BUDGET_SCREEN_ONLY_FIXED50_50_NEW_SHARED_ACCOUNT_NOT_QUALIFICATION',rounding_sensitive_offsets=[dict(period=p,**w) for p,f in facts.items() for w in f['rounding_sensitive_offsets']],numeric_band_did_not_change_signed_predicate=True)
    return all(pearson.values()) and all(tail.values()) and details['two_periods_including_a_later_offset'] and all(overlap.values()),details

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','actual','run-dir','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); g=guards(); work=args.run_dir.resolve(); output=args.output.resolve()
    check(os.environ.get('COIN_TASK_ID') and work.parent==STATE and work.name.startswith('d036-') and not work.exists() and output==OUT and not output.exists(),'Exclusive bounded/progress D036 audit')
    check(args.protocol.resolve().parent==ROOT/'protocols' and args.actual.resolve().parent==ROOT/'reports/fast_research','Only frozen root protocol/fresh result')
    spec,protocol_sha=g.small(args.protocol.resolve()); check(args.actual.resolve()==(ROOT/spec['output_path']).resolve(),'Exact versioned diagnostic report routing')
    actual,actual_sha=g.small(args.actual.resolve()); _,code_sha=g.small(__file__,parse=False); g.small(ARCHIVE,code_sha,False)
    check(Path(sys.prefix).resolve()==Path(spec['environment']['sys_prefix']).resolve() and pl.thread_pool_size()<=2,'Clean CPU2 environment')
    work.mkdir(); binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=code_sha,guard_source_sha256=GUARDS_SHA,protocol_path=str(args.protocol.resolve()),protocol_sha256=protocol_sha,
        actual_report_sha256=actual_sha,actual_reports={str(args.actual.resolve()):actual_sha},python=sys.executable,sys_prefix=sys.prefix,exact_command=' '.join(sys.argv))
    rb_sha,_=g.write(work/'RUN_BINDING.json',binding)
    report=dict(status='FAIL_D036_INDEPENDENT_SAVED_LEDGER_STATISTICS',binding=binding,run_binding_sha256=rb_sha,independent_source=str(Path(__file__).resolve()),independent_source_sha256=code_sha,
        verified_source_hashes=spec['frozen_sources'],cases=[],case_verification={},input_bindings=[],completed_periods_verified=0,completed_files_verified=0,budget_screen_pass=None,
        candidate_status='NO_QUALIFIED_CANDIDATE',native_account_certified=False,ensemble_NAV_generated=False,long_term_APR='NOT_EVALUABLE',old_account_finance_or_source_QA_replayed=False,
        maximum_independent_RSS_bytes=RSS,maximum_wall_seconds=300,statistic_tolerances=dict(cash_USDT=CASH_TOL,ratio=RATIO_TOL))
    signal.signal(signal.SIGTERM,lambda *args:(_ for _ in ()).throw(TimeoutError('Bounded audit terminated')))
    try:
        before=resources.status(); g.bounded(before); report['resources_before']=before
        contexts,artifacts,task=metadata(g,spec,actual,protocol_sha); report['actual_task']=task; report['input_bindings']=artifacts
        for period,legs in contexts:
            metrics,facts=statistics(period,legs); published=[c for c in actual['cases'] if c['period']==period['id']]
            check(len(published)==1,'Exactly published fixed period'); compare(metrics,published[0],period['id'])
            report['cases'].append(metrics); report['case_verification'][period['id']]=facts; report['completed_periods_verified']+=1; report['completed_files_verified']+=4
            print('Verified saved statistics '+period['id'],flush=True); gc.collect(); budget()
        screen,details=decision(report['cases'],report['case_verification'],spec['decision_rule'])
        for item in artifacts: check(sha(item['path'])==item['sha256'],'Final immutable ledger byte identity')
        g.small(args.actual.resolve(),actual_sha); g.small(args.protocol.resolve(),protocol_sha)
        for relative,digest in spec['frozen_sources'].items(): g.small(g.project(relative),digest,False)
        report.update(status=STATUS,budget_screen_pass=bool(screen),decision_details=details,completed_daily_rows_verified=1518,completed_minute_rows_verified=2_185_920,
            completed_period_days_verified=759,maximum_statistic_errors=dict(ERRORS),observed_producer_and_independent_STATE_bytes=owned([Path(actual['run_dir']),work]),
            sourceproof_scope='EXACT_ACCEPTED_ARTIFACTS_AND_FRESH_DIAGNOSTIC_TASK_NO_OLD_FINANCE_REPLAY',statistic_implementation='CENTERED_DOT_PEARSON_SCIPY_AVERAGE_RANKDATA_SPEARMAN_AND_POLARS_MIN_MAX_EXPOSURE')
        budget()
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error),traceback=traceback.format_exc(),maximum_statistic_errors=dict(ERRORS)); raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-STARTED,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_after=resources.status())
        g.bounded(report['resources_after']); digest,_=g.write(output,report); print(str(output)+' '+digest,flush=True)
if __name__=='__main__': main()
