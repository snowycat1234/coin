"""Reconstruct one source sample from public Git in a new STATE, zero fits."""
import argparse
import json
from pathlib import Path
import time
from preflight import HERE,ROOT,git,digest,save,run

PREFIX='research/aggressor-flow-preflight-20261011/'


def verify(commit,output):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    output.mkdir();start=time.monotonic()
    expected_raw=git('show',commit+':'+PREFIX+'result/SOURCE_PREFLIGHT.json')
    expected=json.loads(expected_raw)
    for name in ('preflight.py','PROTOCOL.json'):
        b=git('show',expected['scientific_source_HEAD']+':'+PREFIX+name)
        assert b==git('show',commit+':'+PREFIX+name)==(HERE/name).read_bytes()
    for line in git('show',commit+':'+PREFIX+'SOURCE_SHA256.txt').decode().splitlines():
        sha,p=line.split(maxsplit=1)
        assert digest((ROOT/p).read_bytes())==sha
        assert digest(git('show',expected['scientific_source_HEAD']+':'+p))==sha
    run(output/'source')
    actual=json.loads((output/'source/SOURCE_PREFLIGHT.json').read_bytes())
    for key in expected:
        if key not in ('elapsed_seconds','scientific_source_HEAD'):
            assert expected[key]==actual[key],key
    expected_npz=git('show',commit+':'+PREFIX+'result/SOURCE_FLOW_SAMPLE.npz')
    assert digest(expected_npz)==expected['artifact_SHA256']
    assert expected_npz==(output/'source/SOURCE_FLOW_SAMPLE.npz').read_bytes()
    proof=dict(status='PASS_PUBLIC_COLD_AGGRESSOR_SOURCE_PREFLIGHT',artifact_commit=commit,
        original_prefit_SHA=expected['scientific_source_HEAD'],source_commit=expected['source_commit'],
        expected_source_proof_SHA256=digest(expected_raw),feature_bytes_and_source_summaries_exact=True,
        actual_cold_raw_minutes=44640,original_STATE_open_attempts=0,provider_downloads=0,
        fits=0,future_labels=0,predictive_scores=0,wallets=0,
        scope='One same official rawmonth rechecked for cold source verification, not another scientific model trial. FullCORE5flow or predictive evidence NOT_RUN.',
        elapsed_seconds=time.monotonic()-start,code_SHA256=digest(Path(__file__).read_bytes()))
    assert proof['elapsed_seconds']<120
    save(output/'PUBLIC_RESTORE.json',proof);print(json.dumps(proof,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact-commit',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();verify(a.artifact_commit,a.output)
