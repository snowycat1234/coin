import gzip, hashlib, json
import numpy as np
import pytest
from risk_budget import allocate, scale, DAY, ARMS
from compact_state import checkpoint, restore_snapshot, original_npz

def test_fixed_budget_uses_signed_cross_covariance_and_caps_without_changing_direction():
    c=np.eye(5);c[0,1]=c[1,0]=.8
    w=np.array([.04,-.04,0,0,0]);out,p=scale(w,c)
    assert p['risk_target_met'] and not p['cap_bound'];assert abs(p['post_sigma']-.10)<1e-12
    np.testing.assert_allclose(out,w*p['factor']);assert np.sign(out).tolist()==np.sign(w).tolist()
    same=np.array([.04,.04,0,0,0]);_,q=scale(same,c);assert p['factor']>q['factor']
    out,p=scale(np.array([.10]*5),np.eye(5)*.0001)
    assert p['cap_bound'] and not p['risk_target_met'] and p['shortfall']>0 and np.abs(out).sum()<=.6+1e-12
    out,p=scale(np.array([.29,.01,0,0,0]),np.eye(5)*.0001)
    assert p['cap_bound'] and abs(out[0]-.3)<1e-12 and np.abs(out).sum()<.6

def test_existing_target_already_at_budget_or_bound_is_reused_bit_exact():
    w=np.array([.15,.15,-.15,-.15,0.]);out,p=scale(w,np.eye(5)*(.1/.3)**2)
    assert p['risk_target_met'];np.testing.assert_array_equal(out,w)
    out,p=scale(w,np.eye(5)*.01)
    assert p['cap_bound'];np.testing.assert_array_equal(out,w)

def test_zero_intent_remains_cash_invalid_or_degenerate_context_cannot_force_exposure():
    out,p=scale(np.zeros(5),np.eye(5));assert not out.any() and p['reason']=='INTRINSIC_CASH'
    with pytest.raises(ValueError,match='degenerate'):scale(np.array([.1,0,0,0,0]),np.zeros((5,5)))
    with pytest.raises(ValueError,match='safety caps'):scale(np.array([.31,0,0,0,0]),np.eye(5))
    with pytest.raises(ValueError,match='Nonnegative'):scale(np.array([.1,0,0,0,0]),-np.eye(5))

def test_future_suffix_invariance_missing_history_rejected_and_same_budget_is_forecast_only():
    rng=np.random.default_rng(811732);t=np.arange(100)*DAY;p=100*np.exp(np.cumsum(rng.normal(0,.01,(100,5)),axis=0));d=t[30:]
    cs=np.tile([.03,.03,-.03,-.03,0],(len(d),1));hold=np.tile([.03]*5,(len(d),1));base=dict(CS_MATCHED=cs,VOL_MATCHED=hold,STATIC50=.5*cs+.5*hold)
    out,cov,proof=allocate(t,p,d,base);future=p.copy();future[70:]*=np.arange(2,7);alt,altcov,altproof=allocate(t,future,d,base)
    for arm in ARMS:np.testing.assert_array_equal(out[arm][:40],alt[arm][:40])
    np.testing.assert_array_equal(cov[:40],altcov[:40]);assert proof[:40]==altproof[:40]
    assert all(row['last_price_available_us']==row['decision_us'] and row['past_returns']==30 for row in proof)
    broken=p.copy();broken[10,0]=np.nan
    with pytest.raises(ValueError,match='imputed'):allocate(t,broken,d,base)

def test_compact_storage_restores_original_npz_bytes_and_detects_binding_or_corruption(tmp_path):
    rng=np.random.default_rng(7);array=rng.normal(size=(1440,36)).astype(np.float64)
    class SyntheticSnapshot:
        minute_chunks=[array];rows_written=1440;cursor=DAY;stop=None
        def state_hash(self):return 'synthetic-state'
        def snapshot(self):return dict(account={'identity':'synthetic-no-financial-claims'},minute_chunks=[a.tolist() for a in self.minute_chunks])
    pointer=checkpoint(tmp_path,SyntheticSnapshot(),{'arm':'fixture'});snap,p=restore_snapshot(tmp_path,{'arm':'fixture'})
    np.testing.assert_array_equal(snap['minute_chunks'][0],array);assert snap['account']=={'identity':'synthetic-no-financial-claims'}
    assert p['chunks'][0]['original_NPZ_SHA256']==hashlib.sha256(original_npz(array)).hexdigest()
    with pytest.raises(AssertionError):restore_snapshot(tmp_path,{'arm':'wrong'})
    path=tmp_path/p['chunks'][0]['path'];path.write_bytes(path.read_bytes()+b'corrupt')
    with pytest.raises(AssertionError):restore_snapshot(tmp_path,{'arm':'fixture'})

def test_real_native_snapshot_factory_remains_original_grid_contract(tmp_path):
    from driver import native, Closing, SYMBOLS
    daily=native.pl.DataFrame(dict(symbol=list(SYMBOLS),close_us=[0]*5,close=[100.]*5));win=dict(start=0,end=DAY,symbols=SYMBOLS,daily=daily,blocks=lambda:iter(()))
    sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],account_factory=Closing)
    binding={'arm':'synthetic-native'};checkpoint(tmp_path,sim,binding);snap,p=restore_snapshot(tmp_path,binding)
    again=native.NativeDailySimulator.from_snapshot(snap,win,account_class=Closing)
    assert again.state_hash()==sim.state_hash()==p['state_hash'] and again.account.snapshot()==sim.account.snapshot()
    assert Closing.execute_fill is __import__('grid_account').Fine.execute_fill
    with pytest.raises(ValueError,match='version'):native.NativeDailySimulator.from_snapshot(snap,win)
