"""Generated-only math and identity tests. No native account or market input."""
import ast,hashlib,json,unittest,tempfile,shutil
from pathlib import Path
import numpy as np
import h090_risk_controller as h
HERE=Path(__file__).resolve().parent

def fixture(n=30,scale=.01):
    rng=np.random.default_rng(20261014)
    r=rng.normal(0,scale,(n,5))
    ends=np.arange(1,n+1,dtype=np.int64)*h.DAY_US
    return r,ends,ends.copy(),int(ends[-1])

def call(raw,r=None,ends=None,known=None,decision=None,**kwargs):
    if r is None:r,ends,known,decision=fixture()
    return h.size_h090(raw,r,decision_us=decision,return_end_us=ends,available_us=known,**kwargs)

def original_math_oracle():
    """Execute only the exact hash-checked require/signed_risk_weights AST nodes.
    No import or invocation of original strategy/fixed_targets/account code.
    This is a partial math oracle, NEVER native engine/freeze certification.
    """
    doc=h.verify_originals(HERE);rec=doc['files']['public_sma_perpetual.py']
    source=(HERE/rec['package_path']).read_bytes()
    assert hashlib.sha256(source).hexdigest()==rec['SHA256']
    tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('require','signed_risk_weights')]
    if len(nodes)!=2:raise ValueError('EXACT_ORIGINAL_MATH_SYMBOLS_REQUIRED')
    scope={'np':np};exec(compile(ast.Module(body=nodes,type_ignores=[]),'hash_bound_original_math_only','exec'),scope)
    return scope['signed_risk_weights']

class Tests(unittest.TestCase):
    def test_fixed_descriptor_and_integration_no_go(self):
        self.assertEqual((h.H090.gross_cap,h.H090.asset_cap,h.H090.annual_vol_target),(.9,.3,.15))
        for kw in ({'gross_cap':1.},{'annual_vol_target':.2},{'automatic_topup':True},{'asset_cap':.31},{'isolated_leverage':True}):
            with self.assertRaises(h.RiskGateError):h.H090Descriptor(**kw)
        with self.assertRaisesRegex(h.RiskGateError,'9000_8500_1000'):h.require_native_integration()

    def test_original_control_math_bitwise_parity(self):
        oracle=original_math_oracle();rng=np.random.default_rng(77)
        # Original .30/.60/.10 math; includes requested <=.10 control input subset.
        for i in range(250):
            raw=rng.uniform(-(.10 if i<125 else 2),(.10 if i<125 else 2),5)
            returns=rng.normal(0,(.005 if i%2 else .2),(40,5))
            want,meta=oracle(raw,returns);got,details,_=h._math(raw,returns,.60,.30,.10)
            np.testing.assert_array_equal(got,want);self.assertEqual(meta,details)
            if i<125:self.assertLessEqual(np.abs(got).max(),.10)

    def test_fixed_caps_signed_gross_and_no_upscale(self):
        r,e,k,d=fixture(scale=0.)
        w,_,_=call([10,-10,10,-10,10],r,e,k,d)
        self.assertLessEqual(np.abs(w).sum(),.9);self.assertLessEqual(np.abs(w).max(),.3)
        self.assertGreater(np.abs(w).sum(),.6)  # demonstrates native gross guard blocker
        w,_,_=call([.3,-.3,0,0,0],r,e,k,d)
        self.assertEqual(float(w.sum()),0);self.assertEqual(float(np.abs(w).sum()),.6)
        w,_,_=call([.01,-.02,0,0,0],r,e,k,d);np.testing.assert_array_equal(w,[.01,-.02,0,0,0])

    def test_high_volatility_scales_to_point15(self):
        r,e,k,d=fixture(scale=.5);w,meta,cov=call([.3]*5,r,e,k,d)
        self.assertGreater(meta['unscaled_signed_covariance_annual_vol'],.15)
        self.assertAlmostEqual(np.sqrt(w@cov@w),.15,places=12)
        self.assertFalse(w.flags.writeable);self.assertFalse(cov.flags.writeable)

    def test_causal_time_availability_order_and_daily_completeness(self):
        r,e,k,d=fixture();call([.1]*5,r,e,k,d)
        for kwargs in ({'decision':d-1},{'known':k+1},{'ends':e[::-1]},{'known':k-1},{'ends':np.r_[e[:-1],e[-2]]},{'ends':e.astype(float)},{'decision':True}):
            args=dict(r=r,ends=e,known=k,decision=d);args.update(kwargs)
            with self.assertRaises(h.RiskGateError):call([.1]*5,**args)
        gap=e.copy();gap[0]-=1
        with self.assertRaises(h.RiskGateError):call([.1]*5,r,gap,k,d)
        for key in ['symbols','covariance_symbol_order']:
            with self.assertRaises(h.RiskGateError):call([.1]*5,**{key:h.CORE5[::-1]})

    def test_bad_weights_returns_and_output_caps_reject(self):
        for raw in ([np.nan]*5,[np.inf]*5,[True]*5,['.1']*5,[.1]*4):
            with self.assertRaises(h.RiskGateError):call(raw)
        r,e,k,d=fixture()
        for bad in [r[:29],np.full((30,5),np.nan),np.full((30,5),np.inf),np.full((30,5),1e308)]:
            with self.assertRaises(h.RiskGateError):call([.1]*5,bad,e[:len(bad)],k[:len(bad)],d)
        for w in [[.31,0,0,0,0],[.3,.3,.3,.001,0],[np.nan]*5]:
            with self.assertRaises(h.RiskGateError):h.validate_weights(w)

    def test_last30_covariance_deterministic_and_inputs_unchanged(self):
        r,e,k,d=fixture(40);before=r.copy();raw=np.array([.3,-.2,.1,0,.05]);raw_before=raw.copy()
        a,ma,ca=call(raw,r,e,k,d);b,mb,cb=call(raw,r,e,k,d)
        np.testing.assert_array_equal(a,b);self.assertEqual(ma,mb);np.testing.assert_array_equal(ca,cb)
        np.testing.assert_array_equal(ca,np.cov(r[-30:],rowvar=False,ddof=1)*365)
        r[:10]*=20;c,_,cc=call(raw,r,e,k,d);np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(ca,cc)
        np.testing.assert_array_equal(raw,raw_before);np.testing.assert_array_equal(before[10:],r[10:])

    def test_singular_covariance_and_adverse_random_vectors(self):
        r,e,k,d=fixture();r[:]=r[:,0,None]
        for raw in ([.3,-.3,0,0,0],[.3]*5,[0]*5):
            w,meta,cov=call(raw,r,e,k,d);self.assertTrue(np.isfinite(w).all());self.assertLessEqual(np.sqrt(max(w@cov@w,0)),.15+1e-12)
        rng=np.random.default_rng(4)
        for _ in range(250):
            r=rng.normal(size=(30,5))*rng.uniform(0,1);raw=rng.normal(size=5)*5
            w,meta,cov=call(raw,r,e,k,d);h.validate_weights(w);self.assertLessEqual(np.sqrt(max(w@cov@w,0)),.15+1e-12)
            self.assertTrue(np.all(np.sign(w)==np.sign(raw)))

    def test_all_original_hashes_and_tamper_fail(self):
        doc=h.verify_originals(HERE);self.assertEqual(len(doc['files']),4)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);shutil.copyfile(HERE/'SOURCE_PINS.json',root/'SOURCE_PINS.json')
            for rec in doc['files'].values():
                p=root/rec['package_path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/rec['package_path'],p)
            h.verify_originals(root)
            p=root/doc['files']['resumable_perpetual.py']['package_path'];p.write_bytes(p.read_bytes()+b'\n')
            with self.assertRaises(h.RiskGateError):h.verify_originals(root)
            tampered=json.loads((root/'SOURCE_PINS.json').read_text());tampered['files']['resumable_perpetual.py']['SHA256']=hashlib.sha256(p.read_bytes()).hexdigest();(root/'SOURCE_PINS.json').write_text(json.dumps(tampered))
            with self.assertRaisesRegex(h.RiskGateError,'MANIFEST_PIN_TAMPER'):h.verify_originals(root)

if __name__=='__main__':unittest.main(verbosity=2)
