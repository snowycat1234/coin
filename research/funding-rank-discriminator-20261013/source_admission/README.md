# One funding-adjusted CS21 basket discriminator: additive source admission

Historical evaluation has not started. The original preparation checkpoint at
`fd05331a074f9046c7661ebadd234c3a5002d064` remains unchanged and historically
NO_GO. This additive module restores its missing sources, clarifies interval
provenance, and freezes a guarded one-time runner for independent review.

## Fixed scientific question

At each original weekly rank D, compare simple price return
`close(D−1day)/close(D−22days)−1` with that identical return minus the sum of
actual observed raw funding-rate events in `[D−22days,D−1day)`. Scale one is
conditional on raw fractions. This approximation is not exact funded total
return or PnL. Positive funding reduces the LONG-oriented score and thereby
can favour the same asset for SHORT; no separate short sign reversal exists.
The primary control has exactly the same lag and funding/price readiness.
Original unlagged CS is only descriptive.

Original CORE5 order, all-five real200 CSH admission, current real31 close
support, weekly anchor, stable top2/bottom2 ties, fully tied cash and ±0.15 raw
weights are retained. There is no min4 admission. Full 2021/2023/2024/2025
natural calendars and separate preceding ownership ranks are frozen. An
original-active missing ownership context prevents a no-op conclusion.
Only weekly raw CS basket identity is tested. Daily risk scaling, held target
execution, CSH/HOLD economics, and original-wallet identity are not established.

## What source completeness means

The certificate is conditional completeness relative to the exact SHA-pinned,
retrieved project/archive observation set. It does not independently certify
that the provider omitted no payments. The event calculation clock, actual
charge clock, venue arrival/publication time and funding units remain
uncertified. The 24-hour completed-day availability proxy is an assumption.
Unknown/empty source days are NOT_READY and never become zero funding.

Raw reported interval hours are present only where literal original CSV
provenance was restored (2024 H2). All other raw hours remain unknown; the
sealed normalized/transfer field is retained separately and never substitutes
for raw hours or scales a rate. Exact original observation IDs and declared
retrieved-source coverage govern admission. Known raw hours validate the
preceding interval ending at settlement. No final interval is projected
forward. This explicitly supersedes the older preparation wording requiring
positive raw reported hours for every event, without changing the rank recipe.

## Reproduce preparation without scoring historical baskets

Use existing Python/NumPy. From this module directory run:

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover -s . -p 'test_*.py' -v`

The reviewed original preparation module and its three exact input artifacts
must be restored first. Set `FUNDING_RANK_PREPARATION_DIR` to that module's
directory if it is not the default sibling
`coin_funding_rank_discriminator_20261013`. Place its SHA-pinned three files
under its `inputs_restored` directory, with the original exact local filenames
listed in `SOURCE_REFERENCES.json`. This additive module's
`SOURCE_REFERENCES.json` pins the existing public transfer archive; concatenate
its three verified byteparts into `TEMPORAL_FEATURE_SOURCE.zip` here. The
projected 2021 file and all nine 2024 export payloads are included in this
module. Do not retrieve the larger 2024 wrappers or any provider data.

`python -c 'from bind_sources import inventory; print(inventory())'` rechecks
only source hashes, schemas, original mask/covariance identity and observation
coverage. It computes no historical price/funding score or basket. The full
PyArrow dependency is unnecessary for the runner; independent reconstruction
of the 2021 source projection uses the separately verified official PyArrow
23.0.1 workspace dependency. Its source member hashes and exact column whitelist
are preserved in the projection code/receipt.

## Historical execution gate

Do not run `run_baskets.py` until the final independent source/runner review
passes and the parent provides an exact GO JSON binding the final manifest
and independent review receipt hashes. The program verifies every frozen
file before loading/scoring sources. It fixes numeric threads and hides GPUs
before importing NumPy, pins one CPU, bounds address space/RSS/time/output,
requires zero swap and at least 15 GiB disk reserve, and refuses to overwrite
an attempt. A failed authorized attempt is preserved without automatic retry.

Once separately authorized, the only command is:

`bash run_once.sh PARENT_GO.json ATTEMPT001`

The mandatory wrapper applies a whole-process 120-second timeout, including
imports, source loading and serialization, with TERM then KILL after 5 seconds.
The runner refuses execution without the wrapper's timeout marker.

All four years run together; no adaptive dataset dropping. Direct Decimal
event sums, independent stable signed baskets, and real-source causal prefixes
are checked in the same pass. Expected calculation time is under 120 seconds;
source-only admission took 0.37 seconds and the synthetic tests take under one
second locally. No historical timing or result is inferred from that estimate.

All prior failures remain preserved in the original preparation history and
this module's source-extension logs. Missing common200 outputs have not been
recreated. A basket change supports only a feature-selection question; it
does not predict profitability or authorize wallets/models/holdouts.
