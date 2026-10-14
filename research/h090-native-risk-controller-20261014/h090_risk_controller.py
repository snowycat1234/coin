"""Source-only H090 sizing adapter. No account, scheduler or strategy execution."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import numpy as np

CORE5=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY_US=86_400_000_000

class RiskGateError(ValueError):
    pass

@dataclass(frozen=True)
class H090Descriptor:
    version:str='H090_NATIVE_RISK_SOURCE_ONLY_V1'
    gross_cap:float=0.90
    asset_cap:float=0.30
    annual_vol_target:float=0.15
    covariance_observations:int=30
    covariance_ddof:int=1
    annualization_days:int=365
    isolated_leverage:int=1
    automatic_topup:bool=False
    def __post_init__(self):
        expected=('H090_NATIVE_RISK_SOURCE_ONLY_V1',.90,.30,.15,30,1,365,1,False)
        actual=tuple(getattr(self,k) for k in self.__dataclass_fields__)
        if actual!=expected or type(self.automatic_topup) is not bool or any(type(getattr(self,k)) is not int for k in ('covariance_observations','covariance_ddof','annualization_days','isolated_leverage')):
            raise RiskGateError('FIXED_H090_DESCRIPTOR_REQUIRED')

H090=H090Descriptor()
EXPECTED_ORIGINAL_SHA256={'resumable_perpetual.py': '318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585', 'public_sma_perpetual.py': 'c9fe8a916f300e91396dba70948ab44348b947ec333d7c82b8429db36e064e18', 'bybit_cost_inputs.py': 'e8a135fcf87903fafb5f1c4028246f80b4b2044e45844842dba603cdc1df091c', 'execution_contract.py': 'b7fc110d84240233611e2f7e7360c1b7cc5c92308f842a796560964db33f97d1'}

def _clock(value,name):
    if not isinstance(value,(int,np.integer)) or isinstance(value,(bool,np.bool_)) or value<0:
        raise RiskGateError('INVALID_CLOCK:'+name)
    return int(value)

def validate_weights(weights, *, symbols=CORE5):
    if tuple(symbols)!=CORE5:raise RiskGateError('EXACT_CORE5_ORDER_REQUIRED')
    a=np.asarray(weights)
    if a.dtype.kind not in 'fi' or a.shape!=(5,):raise RiskGateError('FIVE_NUMERIC_WEIGHTS_REQUIRED')
    a=np.asarray(a,dtype=np.float64)
    if not np.isfinite(a).all():raise RiskGateError('NONFINITE_WEIGHTS')
    if np.abs(a).max()>.30 or np.abs(a).sum()>.90:
        raise RiskGateError('H090_TARGET_CAP_EXCEEDED')
    return a

def _math(raw,returns,gross_cap,asset_cap,vol_target):
    """Original clip -> gross shrink -> signed covariance -> vol shrink order."""
    w=np.asarray(raw,dtype=np.float64).copy()
    r=np.asarray(returns,dtype=np.float64)
    if w.ndim!=1 or not len(w) or not np.isfinite(w).all() or r.ndim!=2 or r.shape[1]!=len(w) or r.shape[0]<30 or not np.isfinite(r).all():
        raise RiskGateError('FINITE_ORDERED_COMPLETE30_REQUIRED')
    w=np.clip(w,-asset_cap,asset_cap)
    gross=float(np.abs(w).sum())
    if gross>gross_cap:w*=gross_cap/gross
    with np.errstate(over='ignore',invalid='ignore'):
        covariance=np.atleast_2d(np.cov(r[-30:],rowvar=False,ddof=1))*365
        variance=float(w@covariance@w)
    if not np.isfinite(covariance).all() or not np.isfinite(variance) or variance < -1e-15:
        raise RiskGateError('INVALID_COVARIANCE_RISK')
    sigma=float(np.sqrt(max(variance,0.)))
    if sigma>vol_target:w*=vol_target/sigma
    return w,dict(unscaled_signed_covariance_annual_vol=sigma,
        net_target_weight=float(w.sum()),gross_target_weight=float(np.abs(w).sum()),
        covariance_observations=30,covariance_assets=len(w),past_only=True),covariance

def size_h090(raw, past_returns, *, decision_us, return_end_us, available_us,
              symbols=CORE5, covariance_symbol_order=CORE5):
    """Input is a signal vector, not generated strategy targets or an account.

    Each daily return must end and be available at or before decision_us.
    Equality admits only a fully completed logically available bar. No clock
    shift is introduced; caller remains responsible for truthful provenance.
    The newest30 observations must be consecutive complete daily returns.
    """
    decision=_clock(decision_us,'decision_us')
    if tuple(symbols)!=CORE5 or tuple(covariance_symbol_order)!=CORE5:
        raise RiskGateError('EXACT_CORE5_COVARIANCE_ORDER_REQUIRED')
    a=np.asarray(raw);r=np.asarray(past_returns)
    if a.dtype.kind not in 'fi' or a.shape!=(5,) or r.dtype.kind not in 'fi' or r.ndim!=2 or r.shape[1]!=5 or r.shape[0]<30:
        raise RiskGateError('NUMERIC_CORE5_COMPLETE30_REQUIRED')
    ends=np.asarray(return_end_us);known=np.asarray(available_us)
    if ends.dtype.kind not in 'iu' or known.dtype.kind not in 'iu' or ends.shape!=(r.shape[0],) or known.shape!=ends.shape:
        raise RiskGateError('EXACT_RETURN_PROVENANCE_CLOCKS_REQUIRED')
    if np.any(ends<0) or np.any(known<ends) or np.any(known>decision) or np.any(ends>decision):
        raise RiskGateError('FUTURE_OR_UNAVAILABLE_COVARIANCE')
    if np.any(ends[1:]<=ends[:-1]) or any(int(ends[i+1])-int(ends[i])!=DAY_US for i in range(len(ends)-30,len(ends)-1)):
        raise RiskGateError('COMPLETE_CONSECUTIVE_DAILY_RETURNS_REQUIRED')
    w,details,cov=_math(a,r,.90,.30,.15)
    # Floating point multiplication can overshoot a decimal cap by one ULP.
    # Shrink uniformly; never replace a cap with a tolerance or upsize a signal.
    if np.abs(w).sum()>.90:w*=np.nextafter(.90,0.)/float(np.abs(w).sum())
    validate_weights(w)
    sigma_after=float(np.sqrt(max(float(w@cov@w),0.)))
    if np.isfinite(sigma_after) and sigma_after>.15:
        w*=np.nextafter(.15,0.)/sigma_after
        sigma_after=float(np.sqrt(max(float(w@cov@w),0.)))
    if not np.isfinite(sigma_after) or sigma_after>.15:
        raise RiskGateError('POST_SCALE_VOLATILITY_INVALID')
    selected=np.ascontiguousarray(r[-30:],dtype='<f8')
    cov=np.array(cov,copy=True);cov.setflags(write=False);w.setflags(write=False)
    details.update(net_target_weight=float(w.sum()),gross_target_weight=float(np.abs(w).sum()),risk_version=H090.version,annual_vol_target=.15,
        annual_vol_after_scaling=sigma_after,decision_us=decision,
        last_return_end_us=int(ends[-1]),last_available_us=int(known[-1]),
        selected_returns_SHA256=hashlib.sha256(selected.tobytes()).hexdigest(),
        covariance_symbol_order=list(CORE5),financial_execution='NO_GO_SOURCE_ONLY')
    return w,details,cov

def verify_originals(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    doc=json.loads((root/'SOURCE_PINS.json').read_text())
    if set(doc['files'])!=set(EXPECTED_ORIGINAL_SHA256):raise RiskGateError('EXACT_ORIGINAL_CLOSURE_REQUIRED')
    for name,rec in doc['files'].items():
        if rec['SHA256']!=EXPECTED_ORIGINAL_SHA256[name]:raise RiskGateError('ORIGINAL_MANIFEST_PIN_TAMPER')
        rel=Path(rec['package_path'])
        if rel.is_absolute() or '..' in rel.parts:raise RiskGateError('UNSAFE_SOURCE_PATH')
        p=root/rel
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=rec['SHA256']:
            raise RiskGateError('ORIGINAL_CODE_IDENTITY_MISMATCH')
    return doc

def require_native_integration():
    raise RiskGateError('NO_GO_NATIVE_H090_SCHEDULER_ACCOUNT_FREEZE_AND_9000_8500_1000_INTEGRATION_NOT_CERTIFIED')
