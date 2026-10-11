"""Reserve the whole phase before acquisition, including the100MB cumulative cap."""
import argparse
import json
from pathlib import Path
from prepare import PHASES,git,run


def budget(prior_bytes,phase_bytes):
    if prior_bytes<0 or phase_bytes<0 or phase_bytes>35000000 or prior_bytes+phase_bytes>100000000:
        raise ValueError('Frozen per-phase or cumulative source acquisition budget exceeded')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=PHASES,required=True)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--previous',type=Path);p.add_argument('--previous-commit');a=p.parse_args()
    prior=0
    for phase in list(PHASES)[:list(PHASES).index(a.phase)]:
        record=json.loads(git('show',a.source_commit+':research/core5-continuous-risk600-20261011/phases/'+phase+'/RECOVERY.json'))
        prior+=record['new_original_bytes']
    # Reserve35MB accepted sources plus one bounded8MiB in-flight archive. This
    # conservative preflight is stricter than the accepted-byte phase limit.
    reserve=35000000+8*2**20 if a.phase.startswith('Q') else 0
    budget(prior,35000000 if reserve else 0)
    assert prior+reserve<=100000000,'Cumulative in-flight reservation exceeds100MB'
    print('SOURCE_ACQUISITION_PREFLIGHT',dict(prior_public_original_bytes=prior,whole_phase_plus_inflight_reserve=reserve,
        total_reserved=prior+reserve,hard_total_cap=100000000),flush=True)
    run(a.phase,a.state,a.source_commit,a.previous,a.previous_commit)
