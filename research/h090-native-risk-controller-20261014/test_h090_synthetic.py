"""STEP1 generated-only regressions. No account, markets or history."""
import unittest,json,hashlib,ast,tempfile,shutil
from pathlib import Path
import numpy as np
import h090_risk_controller as h
import calendar_readiness_v2 as c
D=c.DAY;H=3_600_000_000
HERE=Path(__file__).resolve().parent
def encode(source,interval):
    b=json.dumps(source,sort_keys=True,separators=(',',':'),allow_nan=True).encode()
    manifest={'schema':'H090_REVIEWED_SOURCE_BAR_BINDING_V2','status':'PINNED_ACTUAL_COMPLETE_SOURCE_BARS',
        'source_blob_SHA256':hashlib.sha256(b).hexdigest(),'source_index_SHA256':'0'*64,
        'symbol_order':list(c.CORE5),'signal_interval_minutes':interval,
        'fixture_scope':'GENERATED_SYNTHETIC_ONLY_NOT_REAL_SOURCE_CERTIFICATION'}
    m=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    return c.SourcePacket(b,m,hashlib.sha256(m).hexdigest())
def fixture(t=200*D,interval=1440,daily_end=None):
    end=t//D*D if daily_end is None else daily_end
    def bars(last,step,kind):
        result=[]
        for i in range(200):
            close=last-(199-i)*step
            for j,s in enumerate(c.CORE5):
                result.append(dict(symbol=s,open_us=close-step,close_us=close,available_us=close,
                    close=float(100+j*10+i*.1+np.sin(i+j)),complete=True,imputed=False,
                    actual_source=True,record_locator=f'{kind}/row_{i}_{s}'))
        return result
    source={'symbol_order':list(c.CORE5),'daily_bars':bars(end,D,'daily')}
    if interval==240:source['signal_bars']=bars(t,4*H,'signal')
    return source
def size(source,t=200*D,interval=1440):
    return h.size_h090([.3,-.3,.3,-.3,.3],encode(source,interval),decision_us=t,signal_interval_minutes=interval)
class CalendarTests(unittest.TestCase):
    def test_daily_latest200_and_stale201(self):
        source=fixture();w,m,cov=size(source)
        self.assertEqual(m['source_readiness']['return_ends_us'],list(range(171*D,201*D,D)))
        with self.assertRaises(c.SourceReadinessError):size(source,201*D)
    def test_delayed_latest_daily_no_fallback(self):
        source=fixture();source['daily_bars'][-1]['available_us']=200*D+1
        with self.assertRaises(c.SourceReadinessError):size(source)
        source['daily_bars']=source['daily_bars'][:-5]
        with self.assertRaises(c.SourceReadinessError):size(source)
    def test_four_hour_two_hour_arrival_admit_five_hour_reject(self):
        t=200*D+4*H;source=fixture(t,240)
        for r in source['daily_bars'][-5:]:r['available_us']=200*D+2*H
        _,m,_=size(source,t,240);self.assertEqual(m['source_readiness']['derived_return_available_us'][-1],200*D+2*H)
        source['daily_bars'][-1]['available_us']=200*D+5*H
        with self.assertRaises(c.SourceReadinessError):size(source,t,240)
    def test_four_hour_stale_next_day_reject(self):
        t=201*D+4*H;source=fixture(t,240,daily_end=200*D)
        with self.assertRaises(c.SourceReadinessError):size(source,t,240)
    def test_four_hour_20h_midnight_rollover_and_not_four_hour_risk(self):
        for t in (200*D+20*H,201*D):
            _,m,_=size(fixture(t,240),t,240);self.assertEqual(m['source_readiness']['expected_daily_end'],t//D*D)
        source=fixture(200*D+4*H,240)
        for r in source['daily_bars']:
            for k in ['open_us','close_us','available_us']:r[k]+=4*H
        with self.assertRaises(c.SourceReadinessError):size(source,200*D+4*H,240)
    def test_shifted_daily_plus_one_us_and_decision_grid(self):
        source=fixture()
        for r in source['daily_bars']:
            for k in ['open_us','close_us','available_us']:r[k]-=D-1
        with self.assertRaises(c.SourceReadinessError):size(source)
        for t,interval in [(200*D+1,1440),(200*D+H,240),(200*D,60),(200*D,True),(200*D,240.)]:
            with self.assertRaises(c.SourceReadinessError):size(fixture(),t,interval)
    def test_endpoint_availability_dominates_all_ten_observations(self):
        source=fixture();source['daily_bars'][-31*5]['available_us']=200*D
        _,m,_=size(source);av=m['source_readiness']['derived_return_available_us']
        self.assertEqual(av[0],200*D);self.assertEqual(av[1],172*D)
    def test_old_excluded_values_do_not_change_covariance_or_return_hash(self):
        source=fixture();a,ma,ca=size(source)
        for r in source['daily_bars'][:-31*5]:r['close']*=3
        b,mb,cb=size(source)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(ca,cb)
        self.assertEqual(ma['selected_returns_SHA256'],mb['selected_returns_SHA256'])
    def test_bad_rows_missing_duplicate_reordered_and_nonactual(self):
        mutations=[lambda s:s['daily_bars'].pop(),
            lambda s:s['daily_bars'].__setitem__(slice(-5,None),s['daily_bars'][-10:-5]),
            lambda s:s['daily_bars'].__setitem__(slice(0,5),s['daily_bars'][:5][::-1]),
            lambda s:s['daily_bars'][-1].__setitem__('complete',False),
            lambda s:s['daily_bars'][-1].__setitem__('imputed',True),
            lambda s:s['daily_bars'][-1].__setitem__('actual_source',False),
            lambda s:s['daily_bars'][-1].__setitem__('open_us',198*D),
            lambda s:s['daily_bars'][-1].__setitem__('close',0),
            lambda s:s['daily_bars'][-1].__setitem__('close',float('nan')),
            lambda s:s['daily_bars'][-1].__setitem__('close',float('inf')),
            lambda s:s['daily_bars'][-1].__setitem__('close',True),
            lambda s:s['daily_bars'][-1].__setitem__('available_us',199*D),
            lambda s:s['daily_bars'][-1].__setitem__('record_locator','/private/source'),
            lambda s:s.__setitem__('symbol_order',list(c.CORE5[::-1]))]
        for mutate in mutations:
            s=fixture();mutate(s)
            with self.assertRaises(c.SourceReadinessError):size(s)
    def test_int64_bounds_booleans_and_clock_dtypes(self):
        packet=encode(fixture(),1440)
        for t in (-1,True,np.bool_(False),2**63,200*D+0.,'17280000000000'):
            with self.assertRaises(c.SourceReadinessError):h.size_h090([.1]*5,packet,decision_us=t,signal_interval_minutes=1440)
        for value in (True,-1,2**63,200*D+0.):
            source=fixture();source['daily_bars'][-1]['available_us']=value
            with self.assertRaises(c.SourceReadinessError):size(source)
    def test_source_and_manifest_tamper_and_caller_arrays_reject(self):
        packet=encode(fixture(),1440)
        for bad in [c.SourcePacket(packet.source_bytes+b' ',packet.manifest_bytes,packet.approved_manifest_sha256),
                    c.SourcePacket(packet.source_bytes,packet.manifest_bytes+b' ',packet.approved_manifest_sha256),
                    c.SourcePacket(packet.source_bytes,packet.manifest_bytes,'f'*64),np.ones((30,5))]:
            with self.assertRaises(c.SourceReadinessError):h.size_h090([.1]*5,bad,decision_us=200*D,signal_interval_minutes=1440)
        with self.assertRaises(TypeError):h.size_h090([.1]*5,np.ones((30,5)),decision_us=200*D,return_end_us=np.arange(30),available_us=np.arange(30))
    def test_warmup_not_reduced_to31_and_signal_gap(self):
        source=fixture();source['daily_bars']=source['daily_bars'][-31*5:]
        with self.assertRaisesRegex(c.SourceReadinessError,'200'):size(source)
        t=200*D+4*H;source=fixture(t,240);source['signal_bars']=source['signal_bars'][-199*5:]
        with self.assertRaisesRegex(c.SourceReadinessError,'200'):size(source,t,240)
        source=fixture(t,240);source['signal_bars']=source['signal_bars'][:-5]
        with self.assertRaises(c.SourceReadinessError):size(source,t,240)
    def test_source_failure_does_not_touch_inventory_or_finance(self):
        held={'BTCUSDT':'1.23456789'};before=held.copy();source=fixture();source['daily_bars'][-1]['imputed']=True
        with self.assertRaises(c.SourceReadinessError):size(source)
        self.assertEqual(held,before)
        with self.assertRaises(h.RiskGateError):h.require_native_integration()
    def test_malformed_source_and_duplicate_record_identity(self):
        for source in [[],{'symbol_order':list(c.CORE5),'daily_bars':[None]*1000}]:
            with self.assertRaises(c.SourceReadinessError):size(source)
        source=fixture();source['daily_bars'][-1]['record_locator']=source['daily_bars'][0]['record_locator']
        with self.assertRaises(c.SourceReadinessError):size(source)
        packet=encode(fixture(),1440);m=json.loads(packet.manifest_bytes)
        for b in [b'{',b'{"symbol_order":[],"symbol_order":[]}']:
            m['source_blob_SHA256']=hashlib.sha256(b).hexdigest();mb=json.dumps(m).encode()
            bad=c.SourcePacket(b,mb,hashlib.sha256(mb).hexdigest())
            with self.assertRaises(c.SourceReadinessError):h.size_h090([.1]*5,bad,decision_us=200*D,signal_interval_minutes=1440)
    def test_fabricated_return_availability_cannot_override_source(self):
        source=fixture();source['daily_bars'][-1]['available_us']=200*D+1
        source['return_available_us']=[200*D]*30
        source['returns']=[[0]*5]*30
        with self.assertRaises(c.SourceReadinessError):size(source)
    def test_original_control_bitwise_math_and_source_pins(self):
        doc=h.verify_originals(HERE);rec=doc['files']['public_sma_perpetual.py'];tree=ast.parse((HERE/rec['package_path']).read_bytes())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('require','signed_risk_weights')];scope={'np':np}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'whole_file_hash_bound_math_only','exec'),scope)
        rng=np.random.default_rng(77)
        for _ in range(250):
            raw=rng.normal(size=5);returns=rng.normal(0,.02,(40,5));a,ma=scope['signed_risk_weights'](raw,returns);b,mb,_=h._math(raw,returns,.6,.3,.1)
            np.testing.assert_array_equal(a,b);self.assertEqual(ma,mb)
    def test_fixed_h090_math_and_finite_caps(self):
        rng=np.random.default_rng(4)
        for _ in range(250):
            raw=rng.normal(size=5)*5;r=rng.normal(0,.3,(30,5));w,meta,cov=h._math(raw,r,.9,.3,.15)
            self.assertLessEqual(np.abs(w).max(),.3+1e-15);self.assertLessEqual(np.abs(w).sum(),.9+1e-15);self.assertLessEqual(np.sqrt(max(w@cov@w,0)),.15+1e-12)
        for raw in ([float('nan')]*5,[float('inf')]*5):
            with self.assertRaises(h.RiskGateError):h.size_h090(raw,encode(fixture(),1440),decision_us=200*D,signal_interval_minutes=1440)
        for raw in ([.31,0,0,0,0],[.3,.3,.3,.1,0]):
            with self.assertRaises(h.RiskGateError):h.validate_weights(raw)
if __name__=='__main__':unittest.main(verbosity=2)
