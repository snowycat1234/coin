"""Compare independently regenerated consumer economic arrays and Parquet values."""
import argparse
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

def main(producer,consumer):
    validation=json.loads((producer/'Y2021/VALIDATION.json').read_text());checked=[]
    for r in validation['derived_artifacts']:
        left=producer/'Y2021'/r['path'];right=consumer/'Y2021'/r['path']
        if left.suffix=='.npz':
            with np.load(left,allow_pickle=False) as a,np.load(right,allow_pickle=False) as b:
                assert a.files==b.files
                for key in a.files:
                    assert a[key].dtype==b[key].dtype and a[key].shape==b[key].shape
                    if a[key].dtype.kind=='f':assert np.array_equal(a[key],b[key],equal_nan=True)
                    else:assert np.array_equal(a[key],b[key])
        else:
            a=pq.read_table(left,use_threads=False).to_pandas(use_threads=False)
            b=pq.read_table(right,use_threads=False).to_pandas(use_threads=False)
            assert a.equals(b),r['path']
        checked.append(r['path'])
    a=json.loads((producer/'Y2021/EPISODES.json').read_text());b=json.loads((consumer/'Y2021/EPISODES.json').read_text())
    assert a==b
    receipt=dict(status='REMOTE_RECOVERED_ORIGINALS_REGENERATE_IDENTICAL_CANONICAL_ECONOMIC_ARTIFACTS',
        canonical_artifact_count=len(checked),artifacts=checked,episode_and_exclusion_records_identical=True,
        actual_active_intervals=a['distinct_eligible_active_intervals'],paid_episode_count=a['terminal_CASH_decisions'],
        model_fits=0,model_inferences=0,backtests=0,wallets=0)
    (consumer/'RESTORATION_VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='artifacts'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--producer',type=Path,required=True);p.add_argument('--consumer',type=Path,required=True)
    a=p.parse_args();main(a.producer,a.consumer)
