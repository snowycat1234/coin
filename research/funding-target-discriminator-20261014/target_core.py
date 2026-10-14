"""Exact original CS31 state -> daily HOLD200 match -> STATIC50 target.

Target-only preparation. No execution quotes, future returns, funding cash,
cost/turnover proxy, account/NAV, wallet or learned model is computed.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
DAY=86_400_000_000;WEEK=7*DAY;ANCHOR=1_704_067_200_000_000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def originals():
    p=HERE/'original2021/original_functions.py'
    spec=importlib.util.spec_from_file_location('funding_target_exact_originals',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.load_originals(p.parent)


def context(t,p,d):
    k=int(np.searchsorted(t,d));valid=np.zeros(5,bool)
    if k<30 or k>=len(t) or t[k]!=d or np.any(np.diff(t[k-30:k+1])!=DAY):
        return valid,None,None,k
    history=p[k-30:k+1]
    valid=np.all(np.isfinite(history)&(history>0),axis=0)
    with np.errstate(invalid='ignore',divide='ignore',over='ignore'):
        returns=np.diff(history,axis=0)/history[:-1]
        price=p[k-1]/p[k-22]-1.
    return valid,returns,price,k


def replay_cs(t,p,decisions,score_provider):
    """Original CS31 weekly state; HOLD200 never clears or gates this state.

    score_provider(d,valid,price) returns paired scores and a whole-rank
    source-known flag. Funding-unknown ranks are retained as explicit taint,
    never interpreted as a real cash signal or dropped to a smaller universe.
    Original price-eligibility min4 and sticky raw clearing are preserved.
    """
    t=np.asarray(t,np.int64);p=np.asarray(p,float);d=np.asarray(decisions,np.int64)
    if p.shape!=(len(t),5) or len(d)<1 or np.any(np.diff(t)!=DAY) or np.any(np.diff(d)!=DAY):
        raise ValueError('Original contiguous CORE5 close/output clocks required')
    f=originals();first=ANCHOR+(int(d[0])-ANCHOR)//WEEK*WEEK
    output={int(at):i for i,at in enumerate(d)}
    arms={a:np.zeros((len(d),5)) for a in ('PRICE_ONLY','FUNDING_ADJUSTED')}
    raw={a:np.zeros(5) for a in arms};source_known=False;owner=first
    eligibility=[];owner_clocks=[];owner_known=[];rank_records=[]
    for at in range(first,int(d[-1])+DAY,DAY):
        valid,returns,price,k=context(t,p,at)
        if (at-ANCHOR)%WEEK==0:
            scores,source_known,proof=score_provider(at,valid,price)
            owner=at
            for a in arms:
                score=np.asarray(scores[a],float)
                if score.shape!=(5,):raise ValueError('Ordered paired CORE5 scores required')
                if source_known and np.any(valid&~np.isfinite(score)):
                    raise ValueError('Known rank has nonfinite original score')
                raw[a]=f.market_neutral(score[None,:],valid[None,:],k=2,gross=.6)[0] if source_known else np.zeros(5)
            rank_records.append({'rank_us':at,'CS31_eligible':valid.tolist(),
                'source_known':bool(source_known),'proof':proof,
                'raw':{a:w.tolist() for a,w in raw.items()}})
        for a in arms:
            raw[a][~valid]=0.  # Original sticky clearing; not undone on recovery.
            row=np.zeros(5);held=np.flatnonzero(raw[a]!=0.)
            if len(held):
                row[held],_=f.signed_risk_weights(raw[a][held],returns[:,held],annual_vol_target=.10)
            if at in output:arms[a][output[at]]=row
        if at in output:
            eligibility.append(valid.tolist());owner_clocks.append(owner);owner_known.append(bool(source_known))
    return arms,{'current_eligible':eligibility,'owning_rank_us':owner_clocks,
                 'owning_rank_source_known':owner_known,'rank_records':rank_records}


def match_and_scale(t,p,d,cs,cs_diagnostic,hold,hold_mask):
    """Execute unchanged original match and allocate AST function bodies.

    Only public_targets' returned CS component is supplied by the paired
    frozen CS replay. All original matching and risk function code is unchanged.
    """
    f=originals();namespace=f.match.__globals__;old=namespace['public_targets']
    def fixed_cs(close,clocks,decisions,symbols,allowed):
        if (tuple(symbols)!=SYMBOLS or tuple(allowed)!=SYMBOLS
            or not np.array_equal(close,p,equal_nan=True) or not np.array_equal(clocks,t)
            or not np.array_equal(decisions,d)):
            raise ValueError('Original match dependency inputs changed')
        return np.asarray(cs,float),{'current_eligible':cs_diagnostic['current_eligible']}
    namespace['public_targets']=fixed_cs
    try:
        matched,match_proof,_,_=f.match(t,p,d,hold,hold_mask)
    finally:namespace['public_targets']=old
    components={a:matched[a] for a in ('CS_MATCHED','VOL_MATCHED')}
    components['STATIC50']=.5*components['CS_MATCHED']+.5*components['VOL_MATCHED']
    sized,cov,risk_proof=f.allocate(t,p,d,components)
    return sized['STATIC50'],cov,{'match':match_proof,'risk':risk_proof}


def paired_targets(t,p,d,hold,hold_mask,score_provider):
    cs,diag=replay_cs(t,p,d,score_provider)
    masks=np.asarray(hold_mask,bool);elig=np.asarray(diag['current_eligible'],bool)
    # Preserve exactly the original DAILY gate, including the64-clock context.
    admission=[]
    for i,at in enumerate(d):
        k=int(np.searchsorted(t,at))
        clock=(k>=63 and k<len(t) and t[k]==at and np.all(np.diff(t[k-63:k+1])==DAY))
        admission.append(bool(clock and masks[i].all() and elig[i].all()
                              and np.isfinite(p[k-30:k+1]).all() and (p[k-30:k+1]>0).all()))
    admitted=np.asarray(admission,bool);owner_known=np.asarray(diag['owning_rank_source_known'],bool)
    not_ready=admitted&~owner_known
    result={};proofs={};covariance=None
    for a in cs:
        target,cov,proof=match_and_scale(t,p,d,cs[a],diag,hold,hold_mask)
        # Unknown owning rank with an admitted daily output cannot become a
        # fabricated zero target, support drop or no-op. Retain explicit NaN.
        target[not_ready]=np.nan;result[a]=target;proofs[a]=proof
        if covariance is not None:np.testing.assert_array_equal(cov,covariance)
        covariance=cov
    return result,covariance,{'daily_original_admission':admitted,
        'daily_required_source_not_ready':not_ready,'CS':diag,'risk':proofs}
