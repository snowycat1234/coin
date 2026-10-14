# Public-safe source and synthetic checkpoint

The scientific files and SOURCE_MANIFEST.json are byte-identical to the reviewed
implementation. Its manifest SHA256 is
`11d645f59e1cdec1ee141517d550d514a8ffcbe196ddaf27cfede17b589c9f98`.
The public results, attempts and implementation-review documents are compact
projections. Raw operational receipts remain outside this payload. Their SHA256
identities are recorded without private commands or host paths.

The frozen scientific manifest preserves its original pending-review status.
PUBLIC_IMPLEMENTATION_REVIEW.json and the separately bound public projection
review receipt record the subsequent independent PASS. This is an additive
checkpoint, not a rewrite of an earlier receipt.

## Identity gate before imports

Obtain the trusted PUBLIC_PAYLOAD_MANIFEST.json SHA256 from the immutable
publication receipt or reviewed commit. Do not derive this trusted value from
the same untrusted checkout being verified. Set it as EXPECTED_PUBLIC_MANIFEST_SHA256.
From the module directory:

    python3 verify_public_payload.py --expected-manifest-sha256 "$EXPECTED_PUBLIC_MANIFEST_SHA256"

The gate reads only code and metadata, checks every public file, the unchanged
scientific manifest, exact coverage of eleven external code pins and the pure
candidate AST. It imports no candidate, account or NumPy code and downloads
nothing. A successful default gate does not claim those external pins have
been restored or verified on this computer.

## Cold synthetic validation

Validated runtime: Python 3.12 and NumPy 2.3.5. Use a Linux environment with
resource limits and CPU-affinity support. This package requires no historical
arrays, financial-source copies or market downloads for these commands:

    PYTHONDONTWRITEBYTECODE=1 python3 run_cold_synthetic.py --expected-manifest-sha256 "$EXPECTED_PUBLIC_MANIFEST_SHA256"

The public-safe wrapper verifies identity before candidate execution, checks
the runtime, then runs all 21 candidate tests, the generated separated-extrema
toy and fixed synthetic scaling at 43,212, 86,400 and 172,800 rows. Each process
uses one CPU, one math thread, a 4GB address-space limit, a sampled 2GB RSS stop,
60 CPU seconds and a 120-second wall limit. It refuses to overwrite receipts.
The wrapper has no historical-launch option. Generated receipts contain stage
labels and resource measurements, not executable paths or host identifiers.

For a new explicit rerun, add --receipt-dir cold_synthetic_receipts_attempt002.
The 11 separately generated independent checks reported in the implementation
review are prior review evidence; this cold wrapper does not claim to rerun
those independent checks.

## Full original-code pin preflight

The unchanged preflight.py additionally needs eleven original code/metadata
files. EXTERNAL_CODE_PIN_CATALOG.json names each repository, exact immutable
commit, public repository path, expected SHA256 and destination relative to
the module's parent directory. Restore only these eleven files through an
authorized repository read. Do not restore research result ZIPs, market arrays,
source data, funding tapes or proof documents as part of this code preflight.
Do not flatten or rename the catalog destinations; SOURCE_PINS.json and the
original preflight use those exact relative paths. Check every restored SHA256.

After restoration:

    python3 verify_public_payload.py --expected-manifest-sha256 "$EXPECTED_PUBLIC_MANIFEST_SHA256" --external-pins
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 run_bounded_checks.py

The latter bounded runner performs original pin preflight before the same
candidate tests, toy and scaling. Its locally generated raw resource receipt
contains the executable path; do not upload that raw receipt. The public-safe
cold wrapper is the default portable synthetic validation route.

The cold wrapper uses an explicit runtime mismatch refusal rather than an
optimization-sensitive assert, clears inherited PYTHONOPTIMIZE for all child
commands and disables bytecode writes. For the unchanged original bounded
runner, remove PYTHONOPTIMIZE from the environment before running it so its
original preflight assertions cannot be suppressed.

## Interpretation and later admission

The paired stress assumption preserves within-pair dependence. Independent
maxima are a conservative stress assumption, not an established bug. Observed
joint scenarios can miss unseen simultaneous extremes; no universal hurdle
ordering, false-positive label, profit, learned edge or safety certificate is
claimed. Source-only distinction grants no historical or wallet GO.

2021 remains pending the original funding_raw_union_proof_SHA256,
public_restore_proof_SHA256 and warmup_proof_SHA256 provenance bindings. No proof
is substituted or waived. Later 2023/2024/2025 source scopes require separate
exact proof review and authorization. Locked and unknown holdouts remain closed.
