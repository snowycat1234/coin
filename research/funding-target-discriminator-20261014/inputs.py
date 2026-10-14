"""Original source/target admission; outcome arrays remain unselected."""
import hashlib
import json
import os
from pathlib import Path
import sys
from decimal import Decimal,localcontext
import numpy as np
from target_core import HERE,DAY,SYMBOLS,originals

SOURCE=Path(os.environ.get('FUNDING_RANK_SOURCE_DIR',str(HERE.parent/'coin_funding_rank_source_admission_20261013'))).resolve()
EXTERNAL_PINS={'core.py':('61d58fc15ca01f8b5692c276aa07a1ee0bf4e8a0dc10e11684c269590709922e',10447),
               'bind_sources.py':('da41f62f175df4164b56545efe5fc9592dad1d8a021cb287577f3e19f62384c5',13881),
               'FINAL_SOURCE_MANIFEST.json':('3d8f54ad0a02565e101a413adeb30ec99e3762e2587bed51dcb15bdd38c965f4',6276)}
for name,pin in EXTERNAL_PINS.items():
    raw=(SOURCE/name).read_bytes()
    assert len(raw)==pin[1] and hashlib.sha256(raw).hexdigest()==pin[0],name
sys.path.insert(0,str(SOURCE))
from bind_sources import load as source_load,calendar,ROOT
from core import settled_sum,EventStream

SAVED={2021:('48fbcdd8881700341dfd8d07c00cf0e6a6ead851658dd8b93f15d00044084494',83732),
       2023:('5a1a99b9651320f752347853399d293c27723c25e457335a5759e2e1733c85ad',25151),
       2025:('c2c4ec2597eac6a0e177b6890ba20391a63dec70572ddd31e6902ce5f5c3e0e3',25435)}


def load():
    datasets,_=source_load();f=originals();out={}
    for year in (2021,2023,2024,2025):
        t,p,m,streams=datasets[year];start,end=calendar(year)
        d=np.arange(start,end,DAY,dtype=np.int64);k=np.searchsorted(t,d)
        assert np.array_equal(t[k],d);mask=m[k].copy()
        if year==2021:
            path=HERE/'inputs_restored/Y2021_ORIGINAL_TARGETS.npz';raw=path.read_bytes()
            assert len(raw)==SAVED[year][1] and hashlib.sha256(raw).hexdigest()==SAVED[year][0]
            with np.load(path,allow_pickle=False) as z:
                assert tuple(z['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(z['decision_us'],d)
                hold=z['HOLD_original'].copy();np.testing.assert_array_equal(z['HOLD_mask'],mask)
                reference=z['STATIC50'].copy();reference_cov=z['annual_covariance'].copy()
        else:
            assert mask.all();hold=np.zeros((len(d),5))
            for i,at in enumerate(d):
                j=int(np.searchsorted(t,at));past=p[j-30:j+1]
                returns=np.diff(past,axis=0)/past[:-1]
                hold[i],_=f.signed_risk_weights(np.full(5,.6/5),returns)
            if year==2024:
                with np.load(ROOT/'Y2024_TARGETS.npz',allow_pickle=False) as z:
                    assert tuple(z['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(z['decision_us'],d)
                    reference=z['STATIC50'].copy();reference_cov=z['annual_covariance'].copy()
            else:
                path=HERE/f'inputs_restored/Y{year}_ORIGINAL_TARGETS.npz';raw=path.read_bytes()
                assert len(raw)==SAVED[year][1] and hashlib.sha256(raw).hexdigest()==SAVED[year][0]
                with np.load(path,allow_pickle=False) as z:
                    assert tuple(z['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(z['decision_us'],d)
                    reference=z['STATIC50'].copy();reference_cov=None
        assert np.isfinite(hold).all() and not np.any(hold[~mask]!=0)
        out[year]=(t,p,d,hold,mask,streams,reference,reference_cov)
    return out


def frozen_funding_provider(t,p,streams):
    """Only rank21 price/funding windows lag; daily risk is unchanged at D."""
    def provider(at,valid,price):
        proof=[settled_sum(s,int(at)) for s in streams]
        adjusted=np.full(5,np.nan);known=price is not None
        if known:
            with np.errstate(over='ignore',invalid='ignore'):
                for a in np.flatnonzero(valid):
                    if proof[a]['value'] is None:known=False
                    else:adjusted[a]=price[a]-proof[a]['value']
            known=bool(known and np.all(np.isfinite(np.asarray(price)[valid])) and np.all(np.isfinite(adjusted[valid])))
        score=np.full(5,np.nan) if price is None else np.asarray(price)
        independent={'status':'SOURCE_NOT_READY_NO_BASKET_IDENTITY_ASSERTION'}
        if known:
            k=int(np.searchsorted(t,at));direct_price=np.full(5,np.nan)
            for a in np.flatnonzero(valid):direct_price[a]=float(p[k-1,a])/float(p[k-22,a])-1.
            sums=[]
            for a,s in enumerate(streams):
                ids=[]
                with localcontext() as ctx:
                    ctx.prec=100;total=Decimal(0)
                    for timestamp,rate in zip(s.times,s.rates):
                        if at-22*DAY<=int(timestamp)<at-DAY:
                            ids.append(int(timestamp));total+=Decimal.from_float(float(rate))
                    sums.append(float(total))
                if valid[a]:
                    assert ids==proof[a]['event_ids']
                    assert abs(sums[-1]-proof[a]['value'])<=2e-15*max(1.,abs(sums[-1]))
                keep=s.times<at-DAY
                prefix=EventStream(s.times[keep],s.rates[keep],s.hours[keep],
                    {d:v for d,v in s.complete_day_event_ids.items() if d<at-DAY},
                    None if s.normalized_hours is None else s.normalized_hours[keep],s.interval_provenance)
                causal=settled_sum(prefix,int(at))
                assert causal['value']==proof[a]['value']
            direct_adjusted=direct_price-np.asarray(sums)
            def basket(values):
                ids=[i for i in range(5) if valid[i] and np.isfinite(values[i])];out=[0.]*5
                if len(ids)<4 or max(values[ids])-min(values[ids])<=1e-12:return out
                order=sorted(ids,key=lambda i:values[i])
                for i in order[:2]:out[i]=-.15
                for i in order[-2:]:out[i]=.15
                return out
            f=originals()
            for values,primary in [(direct_price,score),(direct_adjusted,adjusted)]:
                assert basket(values)==f.market_neutral(primary[None,:],valid[None,:],k=2,gross=.6)[0].tolist(),'INDEPENDENT_NUMERIC_BASKET_DISAGREEMENT'
            independent={'status':'PASS_DIRECT_DECIMAL_SUM_STABLE_BASKET_AND_FUNDING_PREFIX','decimal_sums_float64':sums}
        return {'PRICE_ONLY':score,'FUNDING_ADJUSTED':adjusted},known,{
            'interval_us':[int(at-22*DAY),int(at-DAY)],'funding':proof,
            'independent':independent,
            'PRICE_ONLY_score':score.tolist(),'FUNDING_ADJUSTED_score':adjusted.tolist()}
    return provider
