"""Extract predetermined audited paths; no account replay, fit or tuning."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
import polars as pl

O=Path('/workspace/scratch/68ef1b82bcac/native_history_experiment')
S=O.parent;B=S/'restored_authorized_native';OUT=O/'fixed_path_calibration'
DAY=86400000000;MINUTE=60000000
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc(t):return datetime.fromtimestamp(t/1e6,timezone.utc).isoformat()

def extract(tag,account,npz,work,path_rows,request,role,output):
    summary=json.loads((account/'summary.json').read_text())
    audit_file=account.parent/'INDEPENDENT_AUDIT.json'
    audit=json.loads(audit_file.read_text());assert audit['status'].startswith('PASS_')
    with np.load(npz,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    dates=a['decision_us'];symbols=a['symbol_order'].tolist();experts=a['expert_order'].tolist()
    minute=pl.read_parquet(account/'minute_nav_inventory.parquet')
    end=int(dates[-1])+DAY
    assert minute.height==len(dates)*1440 and summary['terminal_cash_realized']
    assert [r['decision_us'] for r in path_rows]==dates.tolist()
    requests=np.asarray([r.get('request',request) for r in path_rows],float)
    budgets=np.asarray([r['budget'] for r in path_rows],float)
    proposed=np.asarray([r['targets'] for r in path_rows],float)
    applied=proposed.copy();applied[-1]=0.
    native_targets=pl.read_parquet(account/'targets.parquet')
    lookup={(int(r['available_us']),r['symbol']):r['target_weight'] for r in native_targets.iter_rows(named=True)}
    assert np.array_equal(applied,np.asarray([[lookup[int(t),s] for s in symbols] for t in dates]))
    ends=minute.filter(pl.col('close_us')%DAY==0).sort('close_us')
    assert ends['close_us'].to_list()==(dates+DAY).tolist()
    before={};after={}
    for field in ('nav','free_cash','isolated_balance','cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover'):
        after[field]=ends[field].to_numpy()
        initial=10000. if field in ('nav','free_cash') else 0.
        before[field]=np.r_[initial,after[field][:-1]]
    positions={}
    for suffix in ('quantity','signed_marked_notional','isolated_balance','isolated_equity','signed_weight'):
        values=ends.select([s+'_'+suffix for s in symbols]).to_numpy()
        positions[suffix+'_after']=values
        positions[suffix+'_before']=np.vstack([np.zeros((1,5)),values[:-1]])
    trades=json.loads((account/'trades.json').read_text())
    funding=json.loads((account/'funding.json').read_text())
    liquidations=json.loads((account/'liquidations.json').read_text())
    basis=np.zeros((len(dates),5));entry={s:0. for s in symbols};cursor=0
    for i,t in enumerate(dates):
        while cursor<len(trades) and trades[cursor]['event_us']<=int(t):
            r=trades[cursor];entry[r['symbol']]=r['entry_price_after'];cursor+=1
        basis[i]=[entry[s] for s in symbols]
    trade_next=[];mark_next=[];mark_sources=[]
    for s in symbols:
        table=pl.read_parquet(work/'data/normalized'/(s+'_daily.parquet'))
        trade_lookup=dict(zip(table['close_us'].to_list(),table['close'].to_list()))
        assert np.array_equal(a['market_close'][:,symbols.index(s)],np.asarray([trade_lookup[int(t)] for t in dates]))
        trade_next.append([trade_lookup[int(t)+DAY] for t in dates])
        marks=[]
        for p in sorted((work/'data/normalized/minute'/s/'markPriceKlines').glob('*.parquet')):
            q=pl.read_parquet(p).select('available_us','close').filter(pl.col('available_us').is_in((dates+DAY).tolist()))
            if q.height:marks.append(q);mark_sources.append(dict(path=str(p),sha256=sha(p)))
        marks=pl.concat(marks);mark_lookup=dict(zip(marks['available_us'].to_list(),marks['close'].to_list()))
        mark_next.append([mark_lookup[int(t)+DAY] for t in dates])
    native_delta=after['nav']-before['nav']
    assert abs(native_delta.sum()-summary['net_PnL'])<1e-8
    arrays=dict(decision_us=dates,interval_end_us=dates+DAY,symbol_order=np.asarray(symbols),expert_order=np.asarray(experts),
        desired_request=requests,budget_after=budgets,budget_before=np.vstack([np.eye(len(experts))[0],budgets[:-1]]),
        proposed_mapped_targets=proposed,actually_applied_targets=applied,
        global_forced_terminal_day=a['terminal_zero_target'],
        causal_trade_close_before=a['market_close'],causal_market13=a['market_state13'],
        causal_market13_available_us=a['market_state13_available_us'],causal_expert_targets=a['expert_targets'],causal_target_available_us=a['target_available_us'],
        observed_trade_close_after=np.asarray(trade_next).T,observed_mark_close_after=np.asarray(mark_next).T,
        observed_native_NAV_before=before['nav'],observed_native_NAV_after=after['nav'],observed_native_net_increment_USDT=native_delta,
        observed_native_fees_USDT=after['cumulative_fees']-before['cumulative_fees'],
        observed_native_execution_USDT=after['cumulative_execution_costs']-before['cumulative_execution_costs'],
        observed_native_funding_USDT=after['cumulative_funding']-before['cumulative_funding'],
        observed_native_fill_turnover_USDT=after['cumulative_turnover']-before['cumulative_turnover'],
        native_free_cash_before=before['free_cash'],native_free_cash_after=after['free_cash'],native_entry_basis_before=basis,
        **{'native_'+k:v for k,v in positions.items()})
    panel_npz=output/(tag+'.npz');np.savez_compressed(panel_npz,**arrays)
    witnesses=[]
    if tag=='TAIL_E6_RIDGE_FAILURE_WITNESS':
        expected=int(datetime(2024,11,10,0,45,tzinfo=timezone.utc).timestamp()*1e6)
        assert len(liquidations)==1 and liquidations[0]['symbol']=='DOGEUSDT' and liquidations[0]['event_us']==expected
        start=int(datetime(2024,11,9,tzinfo=timezone.utc).timestamp()*1e6);stop=start+2*DAY
        view=minute.filter((pl.col('close_us')>=start)&(pl.col('close_us')<=stop))
        assert view.height==2881
        np.savez_compressed(output/'TAIL_INTRADAY_LIQUIDATION_WITNESS.npz',columns=np.asarray(view.columns),values=view.to_numpy())
        witnesses=dict(start_us=start,end_us=stop,intraday_rows=view.height,liquidations=liquidations,
            trades=[r for r in trades if start<r['event_us']<=stop],funding=[r for r in funding if start<r['event_us']<=stop],
            warning='Execution failure witness only, not training, development-validation or model-selection data. Liquidation loss is already in the bankruptcy CLOSE trade and NAV; do not subtract lost margin again.')
    detail=dict(tag=tag,role=role,calendar=dict(start_us=int(dates[0]),end_exclusive_us=end,days=len(dates)),
        arrays=dict(file=panel_npz.name,sha256=sha(panel_npz),shapes={k:list(v.shape) for k,v in arrays.items()}),
        native_summary=summary,source=dict(input_npz=dict(path=str(npz),sha256=sha(npz)),
            proposal_sha256=sha(account.parent/'PROPOSALS.json') if (account.parent/'PROPOSALS.json').exists() else sha(B/'results/student/predictions.jsonl'),
            journals={p.name:sha(p) for p in [account/'summary.json',account/'minute_nav_inventory.parquet',account/'trades.json',account/'funding.json',account/'liquidations.json',audit_file]},
            mark_endpoint_sources=mark_sources),
        full_signed_trade_journal=trades,full_funding_event_journal=funding,intraday_failure_witness=witnesses,
        exact_costs=dict(fee_fraction_per_side=.00055,half_spread_bps_per_side=4,slippage_bps_per_side=4,nominal_roundtrip_bps=27,funding_scale=1),
        finance_contract=dict(initial_capital_USDT=10000,isolated_leverage=1,automatic_margin=False,gross_cap=.6,single_asset_abs_cap=.3,budget_discretionary_daily_L1=.1,
            annual_past_covariance_target=.1,target_quantity_NAV_buffer=.99,fees_and_execution_charged_once=True,
            funding_rate_unit='UNCONFIRMED_CONDITIONAL_RAW_AS_FRACTION_1',MMR='.005_UNCERTIFIED_RESEARCH_ASSUMPTION'),
        boundary_convention='End-of-day minute snapshots include same-time eligible funding. First before-state is fresh10k cash. Applied targets differ from proposals on compulsory final cash day. Actual event and inventory state are authoritative.',
        leakage_warning='Only fields prefixed causal_* and predecision state are eligible model inputs. observed_* outcomes, after-state and full future journals are calibration targets, never inference inputs.',
        independent_audit=audit)
    (output/(tag+'.json')).write_text(json.dumps(detail,indent=2,allow_nan=False)+'\n')
    return dict(tag=tag,role=role,days=len(dates),native_net_PnL=summary['net_PnL'],liquidations=len(liquidations),array_file=panel_npz.name,sha256=sha(panel_npz))

def main():
    OUT.mkdir(exist_ok=False)
    family=O/'e5_h1/family';tail=O/'original_control'
    cases=[]
    cases.append(extract('H1_E5_FAMILY_EW',family/'account',S/'h1_fixed_e5_inputs/inputs/H1_E5_INPUTS.npz',S/'h1_fixed_e5_inputs',
        json.loads((family/'PROPOSALS.json').read_text()),[0.,.25,.25,.25,.25],
        'Predetermined training-window fixed-path financial calibration. No policy fit and no path selection by proxy utility.',OUT))
    cases.append(extract('TAIL_E6_RIDGE_FAILURE_WITNESS',tail/'account',B/'inputs/TAIL_INPUTS.npz',O/'tail_data',
        [json.loads(l) for l in (B/'results/student/predictions.jsonl').read_text().splitlines()],None,
        'Predetermined known-liquidation execution failure witness only. Excluded from training, validation and model selection.',OUT))
    index=dict(schema='PREDETERMINED_FIXED_PATH_NATIVE_CALIBRATION_PANEL_V1',cases=cases,new_fits=0,new_native_replays=0,new_price_downloads=0,
        source_and_full_inputs_increment_commit='b82412e9a34fcdaf7e44f2f9f2664e5b503b90a1',
        reconstruction='These files are the small direct calibration panel; no90MB market archive is needed to read them. Full native engine/data are in prior verified storage increments.',
        array_semantics='Quantities are signed contracts; target and signed_weight are NAV fractions. Funding has signed USDT cashflow. Cost increments are positive expenses. Net equals native NAV delta, not sum of separate expert profits.',
        files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file()])
    (OUT/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps(dict(cases=cases,total_bytes=sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()))),flush=True)

if __name__=='__main__':main()
