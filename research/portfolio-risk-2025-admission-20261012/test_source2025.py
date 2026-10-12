"""Identity and causal extension tests, without financial account construction."""
import numpy as np
import polars as pl
from source2025 import causal_inputs,targets

def test_full2025_original_targets_and_exact_causal_prefix():
 t,p,d,saved,past,bars=causal_inputs();out,cov,proof=targets(t,p,d,saved,past,bars)
 assert len(d)==365 and len(proof)==365 and cov.shape==(365,5,5)
 cut=d[181];keep=t<=cut;ids=d<=cut
 alt,altcov,_=targets(t[keep],p[keep],d[ids],saved[ids],past[ids],bars.filter(pl.col('available_us')<=cut))
 np.testing.assert_array_equal(altcov,cov[ids])
 for a,w in out.items():
  np.testing.assert_array_equal(alt[a],w[ids]);assert np.abs(w).max()<=.3+1e-12 and np.abs(w).sum(1).max()<=.6+1e-12
 assert all(r['past_returns']==30 for r in proof)
