import os,time
from pathlib import Path
import numpy as np
import polars as pl
from .common import atomic,guard,read,sha

class Progress:
    def __init__(self,state,case_id):self.state=state;self.case_id=case_id
    def update(self,label,current,total,unit,**kwargs):
        atomic(self.state/'progress'/(self.case_id+'.json'),dict(case_id=self.case_id,current=current,total=total,phase=label,updated=time.time(),**kwargs))

def execute(task):
    from .inputs import window
    from .funding import AdverseFundingAccount,independent
    from quant.bybit_isolated_account import BybitIsolatedAccount
    from scripts.investment import perpetual_directional as engine
    from scripts.investment.bybit_cost_inputs import snapshot_cost
    state=Path(task['state']);repo=Path(task['repo']);cid=task['id'];dest=state/'accounts'/cid
    completed_index=state/'progress'/(cid+'-accepted.json')
    if completed_index.exists() or (dest/'ACCEPTED.json').exists():
        receipt=read(completed_index if completed_index.exists() else dest/'ACCEPTED.json')
        if receipt['task']!=task:raise ValueError('Resume task differs from completed immutable account')
        for entry in receipt['saved']['artifacts'].values():
            if sha(entry['path'])!=entry['sha256']:raise ValueError('Completed account bytes changed')
        return receipt
    # Never overwrite failed/partial account directories. An interrupted attempt stays reviewable.
    if dest.exists():dest=state/'accounts'/(cid+'-attempt-'+str(time.time_ns()))
    guard(state);p=Progress(state,cid);p.update('加载共享只读输入',0,525600,'分钟')
    w=window(state);target_path=state/'targets'/(task['unit']+'-'+task['algorithm']+'.parquet')
    weight_path=state/'targets'/(task['unit']+'-'+task['algorithm']+'-weights.npy')
    if sha(target_path)!=task['target_sha256'] or sha(weight_path)!=task['weight_sha256']:raise ValueError('Frozen worker weight/target identity changed')
    for entry in read(state/'cache/INPUT_BINDING.json')['files']:
        if sha(state/'cache'/entry['path'])!=entry['sha256']:raise ValueError('Worker shared input bytes changed')
    targets=pl.read_parquet(target_path)
    def factory(bars,decisions,mode):
        if not np.array_equal(targets['available_us'].to_numpy(),decisions):raise ValueError('Exact frozen causal daily path required')
        return targets,dict(algorithm=task['algorithm'],unit=task['unit'],weight_path_sha256=task['weight_sha256'],
            target_path_sha256=sha(target_path),feedback='CONTINUOUS_NET_SHADOW_NOT_FUNDED_SUBACCOUNTS',
            future_winner_used=False,pressure_weights_frozen_to_BASE=True)
    scenario=task['scenario'];stress=scenario=='EXECUTION_X2'
    cost=snapshot_cost(repo/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',symbols=('BTCUSDT',),
        fee_zone_by_symbol={'BTCUSDT':'DERIVATIVES_CRYPTO_STANDARD'},scenario_id=scenario,
        half_spread_bps=8 if stress else 4,slippage_bps=8 if stress else 4,
        execution_source_ref='BYTE_EXACT_ACCEPTED_BINANCE_USDM_2023_BTC_PROXY',execution_status='FIXED_NON_NATIVE_SCENARIO')
    if stress:
        cost['fee_rate_fraction']='0.00110';cost['roundtrip_bps']='54'
        cost['provenance']={**cost['provenance'],'fee_rate_fraction':'0.00110','stress_fee_multiplier':2,
            'fee_time_scope':'REGISTERED_DOUBLE_EXECUTION_COST_PRESSURE_NOT_NEW_ACCOUNT_FEE_EVIDENCE'}
    unit=dict(id=task['unit'],scale=1.0 if task['unit']=='RAW_AS_FRACTION' else .01)
    adverse=scenario=='FUNDING_ADVERSE';started=time.time()
    case=engine.simulate(w,'LONG_SHORT',cost,unit,p,lambda:guard(state),target_factory=factory,
        account_factory=AdverseFundingAccount if adverse else BybitIsolatedAccount,persist_cash_close=True)
    if sha(target_path)!=task['target_sha256'] or sha(weight_path)!=task['weight_sha256']:raise ValueError('Frozen path changed during wallet execution')
    for entry in read(state/'cache/INPUT_BINDING.json')['files']:
        if sha(state/'cache'/entry['path'])!=entry['sha256']:raise ValueError('Shared input changed during wallet execution')
    saved=engine.save_case(case,dest);atomic(dest/'summary.json',saved['summary'])
    saved['artifacts']['summary.json']=dict(path=str(dest/'summary.json'),sha256=sha(dest/'summary.json'),bytes=(dest/'summary.json').stat().st_size)
    p.update('独立核验完整分钟账本',case['summary']['completed_minutes'],525600,'分钟')
    audit=independent(dest,unit['scale'],adverse,state/'audit-scratch')
    receipt=dict(task=task,directory=str(dest),saved=saved,independent=audit,
        native_complete=case['summary']['completed_minutes']==525600 and case['summary']['terminal_cash_realized'],
        elapsed_seconds=time.time()-started)
    atomic(dest/'ACCEPTED.json',receipt)
    atomic(completed_index,receipt)
    p.update('账户完成并已独立核验',case['summary']['completed_minutes'],525600,'分钟')
    return receipt
