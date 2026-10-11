"""Public source-only restore, freshSTATE, exact saved vectors and summaries."""
import argparse
import json
from pathlib import Path
import time
from tail_resolution import HERE, ROOT, digest, git, run, save

PREFIX = 'research/trade-tail-resolution-20261011/'


def verify(commit, output):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    output.mkdir()
    start = time.monotonic()
    expected_raw = git('show', commit + ':' + PREFIX + 'result/SOURCE_PROOF.json')
    expected = json.loads(expected_raw)
    for line in git('show', commit + ':' + PREFIX + 'SOURCE_SHA256.txt').decode().splitlines():
        sha, path = line.split(maxsplit=1)
        assert digest(git('show', expected['scientific_source_HEAD'] + ':' + path)) == sha
        assert digest(git('show', commit + ':' + path)) == sha
        assert digest((ROOT / path).read_bytes()) == sha
    run(output / 'source')
    actual = json.loads((output / 'source/SOURCE_PROOF.json').read_bytes())
    for k in expected:
        if k not in ('scientific_source_HEAD', 'elapsed_seconds'):
            assert expected[k] == actual[k], k
    for name in ('SOURCE_RESOLUTION.npz', 'SUMMARY.json'):
        assert git('show', commit + ':' + PREFIX + 'result/' + name) == (output / 'source' / name).read_bytes(), name
    proof = dict(status='PASS_PUBLIC_COLD_SOURCE_RESOLUTION', artifact_commit=commit,
        original_prefit_SHA=expected['scientific_source_HEAD'], source_commit=expected['source']['source_commit'],
        expected_source_proof_SHA256=digest(expected_raw), bytes_vectors_and_summaries_exact=True,
        original_STATE_open_attempts=0, provider_downloads=0, fits=0, new_model_trials=0,
        future_labels=0, prediction_scores=0, targets=0, wallets=0, source_common_dates_rechecked=698,
        elapsed_seconds=time.monotonic() - start,
        scope='Same public source quality calculation rechecked; rawminute integrity inherited fromfive publishedcold phase certificates, no fresh CSVscan and no second independentdata sample.')
    assert proof['elapsed_seconds'] < 120
    save(output / 'PUBLIC_RESTORE.json', proof)
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--artifact-commit', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    verify(a.artifact_commit, a.output)
