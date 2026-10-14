"""Fixed generated synthetic scaling sizes, no market/ledger input paths."""
from __future__ import annotations
import json
import resource
import time
import numpy as np
from paired_buffer import MINUTE, features


def main():
    rows=[]
    for size in (43212,86400,172800):
        t=np.arange(size,dtype=np.int64)*MINUTE
        # Deterministic, positive, synthetic path. No random fit or price source.
        phase=np.arange(size,dtype=np.float64)
        marks=100*np.exp(.02*np.sin(phase/201)+.01*np.cos(phase/47))
        opens=np.r_[marks[0],marks[:-1]]*np.exp(.001*np.sin(phase/29))
        began=time.perf_counter();out=features(t,marks,opens);elapsed=time.perf_counter()-began
        rows.append({'synthetic_rows':size,'elapsed_seconds':elapsed,
                     'input_array_bytes':t.nbytes+marks.nbytes+opens.nbytes,
                     'output_array_bytes':sum(x.nbytes for x in out.values()),
                     'ready_rows':int(np.count_nonzero(out['ready'])),
                     'process_peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
    print(json.dumps({'status':'MEASURED_SYNTHETIC_SCALING_ONLY',
                      'algorithm':'O(N) exact pair coefficients plus monotone deque; no scenarios dropped',
                      'sizes':rows,'not_historical_runtime_forecast':True,
                      'historical_array_reads':0,'historical_wallets':0,'market_requests':0},
                     indent=2,sort_keys=True))


if __name__=='__main__':main()
