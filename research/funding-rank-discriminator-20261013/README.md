# Frozen source-only preparation, historical stage not started

One lagged21day simple-price-return minus actual settled-rate-sum candidate,
one exact same-lag price control, original weekly CORE5 basket rule and original
all-five CSH admission. No wallets, models, future utilities or PnL evaluation.

Current preparation:
-19 synthetic tests passed in0.043seconds, including asynchronous variable
  ending intervals, missing final events, no source authority, causality,
  stable ties, funding signs and overflow without a four-asset fallback.
-474794 bytes restored from three exact public artifacts with SHA256/member
  checks.2021 original200-close mask is bit-exact against the saved source
  certificate.2024 original covariance is bit-exact from the verified same
  close cube. All four complete price calendars and original admission masks
  are usable. These are source checks, zero historical basket evaluations.
-2023 and2025 close cubes have differing earlier source revisions; preserve
  the original separate pinned source per year. Do not substitute or stitch.
-2023/2025 sealed raw event members are present; event-source completeness
  certificates need final independent admission.2021/2024 funding not restored.
  No historical run is authorized or ready yet.

Run synthetic preparation only from this published module directory:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover \
      -s . -p test_core.py -v

To reproduce price/mask admission, place the three existing SHA-pinned artifacts
from SOURCE_REFERENCES.json under inputs_restored/ using the exact local names
FUNDING_DIRECTION_INPUTS.zip, CORE5_WARMUP_MASKS.npz and Y2024_TARGETS.npz.
These public inputs are reused by identity, not republished in this checkpoint.

The price-admission script already produced PRICE_MASK_ADMISSION_RECEIPT.json.
It refuses to overwrite that receipt. Its only computation is source/mask/
covariance identity, not new target evaluation. Failure history and original
borrowed-function provenance are retained in ATTEMPTS.json.

Core takes immutable original CSH masks and a separately admitted source
certificate giving the exact complete-day observed event IDs. It does not
invent completeness from forward projected intervals or infer missing funding
as zero. Conditional24h availability is not historical publication certification.

Next checkpoint is independent preparation review. Only after complete bounded
funding-source admission and a final sealed runner may the parent authorize one
full2021/23/24/25 basket-only pass. Expected pure calculation is well under the
120second ceiling; source restoration remains incomplete, so that is not an ETA
for finishing source admission. A no-op conclusion requires complete admitted
support and exact candidate/control signed baskets, not merely unchanged total
rank order at a subset of dates.
