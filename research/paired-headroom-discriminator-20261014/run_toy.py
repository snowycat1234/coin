"""Generate synthetic inputs in memory. There is no historical input option."""
from __future__ import annotations
import json
import numpy as np
from paired_buffer import MINUTE, WINDOW, features, at
from vendor import headroom_buffer as original


def separated_extrema_toy():
    n = WINDOW + 12
    clocks = np.arange(n, dtype=np.int64)*MINUTE
    marks = np.ones(n, np.float64)*100
    # An early 20% mark shock and a separate later 10% execution gap.
    marks[100:105] = 120
    opens = np.r_[marks[0], marks[:-1]].copy()
    opens[200] *= 1.10
    i = WINDOW
    paired = features(clocks, marks, opens)
    legacy = original.features(clocks, marks, opens)
    q, equity, mark = -1., 25., float(marks[i])
    old = original.assess(q, equity, mark,
                          **{k: float(legacy[k][i]) for k in
                             ('a_down', 'a_up', 'g_down', 'g_up')})
    new = at(paired, i, q, equity, mark)
    aligned = at(paired, i, q, equity, mark, arm='aligned_independent')
    return {'scope': 'SYNTHETIC_ONLY_NO_HISTORY_OR_WALLET',
            'signal_close_us': int(clocks[i]+MINUTE),
            'original_independent_trigger': bool(old['trigger']),
            'paired_trigger': new['trigger'],
            'aligned_independent_trigger': aligned['trigger'],
            'original_required_equity': float(equity-old['buffered_headroom']),
            'paired_required_equity': new['required_isolated_equity'],
            'aligned_independent_required_equity': aligned['required_isolated_equity'],
            'alignment_only_required_equity_difference': float(equity-old['buffered_headroom'])-aligned['required_isolated_equity'],
            'coupling_only_required_equity_difference': aligned['required_isolated_equity']-new['required_isolated_equity'],
            'warning': 'Joint pairing constrains the stress assumption and lowers '
                       'the hurdle in this toy. Unseen co-occurring extremes remain '
                       'possible; unconditional hurdle ordering is not asserted.',
            'historical_array_reads': 0, 'account_imports': 0,
            'wallets': 0, 'financial_advances': 0, 'market_requests': 0}


if __name__ == '__main__':
    print(json.dumps(separated_extrema_toy(), indent=2, sort_keys=True))
