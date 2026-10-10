"""Strict prototype import identity requires one recovery path per process."""
import json
import subprocess
import sys
from pathlib import Path

root=Path('/workspace/coin-temporal')
state=Path('/workspace/coin-state/work/temporal-two-expert-20261009/selected-refit')
jobs=[('refit2','modules/temporal_selected_refit'),('Q4synthetic6','modules/temporal_q4_reserved'),
      ('Q4economics2','research/temporal-selected-refit-q4-20261010/test_q4_economics.py')]
records=[]
for name,target in jobs:
    result=subprocess.run([sys.executable,'-m','pytest',target,'-q',
        '--basetemp='+str(state/('isolated-'+name)),
        '--junitxml='+str(state/(name+'_TEST.xml'))],cwd=root,capture_output=True,text=True)
    record=dict(group=name,target=target,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
    records.append(record)
    print(json.dumps(record),flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
with (state/'ISOLATED10_TEST_RECEIPT.json').open('x') as stream:
    stream.write(json.dumps(dict(status='PASS',total_tests=10,isolated_processes=3,groups=records,
        combined_attempt='9passed1fixture_error; same immutable prototype imported from two recovery paths; guard preserved',
        real_training_fits=0,reserve_model_scores=0,reserve_economic_wallets=0),indent=2)+'\n')
