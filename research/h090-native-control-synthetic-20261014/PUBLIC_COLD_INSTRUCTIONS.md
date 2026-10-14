# H090 exact frozen generated-control checkpoint

The immutable original SOURCE_FREEZE.json SHA256 is cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f. Original FINAL_MANIFEST.json SHA256 is e5db09f4052773e67137f708218a54547ba8e478a3acc4ef0b56a28aab2129be. Frozen science is unchanged. FINAL_MANIFEST describes the original native local files; PUBLIC_PAYLOAD_MANIFEST describes this transport. Do not substitute one for the other.

This cold scope is generated-only execution, with checksum-only byte access to two already-public 2023/2025 development target archives totaling 50,586 bytes. It is not fully source-free. The archives are reused by existing immutable public Git blob identity, with no new NPZ upload. They are never loaded with np.load or parsed into archive members or target arrays. Their presence satisfies the unchanged original code-closure hash checks. This does not waive historical admission, authorize a historical wallet, or expose unknown/locked holdouts. Historical, full-restore/fork and finite-program GO remain false.

Python 3.12.14, NumPy 2.3.5, Polars 1.44.2 and PyArrow 23.0.1 are exact producer receipt versions. The original COLD_RUN/README use the broader phrase Python3.12; this operational wrapper requires the actual exact producer version. No runtime installation or network request is made by cold execution. Obtain those official packages in your normal virtual environment before running. If packages are supplied in additional site-packages directories, pass each explicit directory with --runtime-site. These are portable runtime locations, not project source or history roots.

Run from this restored module directory, substituting the externally verified PUBLIC_PAYLOAD_MANIFEST SHA256:

    python -B -E run_public_cold.py --expected-manifest-sha256 PUBLIC_MANIFEST_SHA256 --receipt-dir cold_receipts_new --runtime-site /your/official/polars/site-packages --runtime-site /your/official/pyarrow/site-packages

Omit --runtime-site flags when exact official packages are installed in the interpreter's normal site-packages. The receipt directory must not exist. The wrapper drops inherited Python optimization/import-path settings for its child commands, checks exact runtime versions and optimization_level=0, runs the immutable source loader audit, then run_checks.py with the exact externally bound freeze. All 51 distinct generated tests and eight fresh journals must pass. Each fresh journal and SUMMARY.json must equal its decompressed saved native body byte for byte. Frozen source identities are checked again afterward.

The unmodified entry points are:

    python -B run_verified.py --freeze-sha cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f tests
    python -B run_verified.py --freeze-sha cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f generated --receipt-dir generated_receipts_new
    python -B run_checks.py --freeze-sha cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f --receipt-dir bounded_receipts_new

Use the pinned interpreter and explicit official runtime sites for those direct commands. The separate wrapper supplies those paths via a newly constructed PYTHONPATH, rather than inheriting a caller's path settings. It does not rewrite, stub or relax original science, dependency checks or source-loader rules.

saved_generated_journals/GENERATED_JOURNALS.tar.gz contains the eight native JSON journals and their native SUMMARY.json, losslessly compressed. JOURNAL_BODY_MANIFEST records exact native SHA256, Git blob SHA1, sizes and original aliases. No recomputation or reformatting was used for saved bodies.

bounded_receipts_001/PUBLIC_RECEIPT.json is an explicitly labeled path-only projection of the original RECEIPT.json: only the private interpreter string is replaced by $PYTHON_EXECUTABLE. PUBLIC_NATIVE_TEST_RESULTS_001.txt replaces two private workspace prefixes and adds a clear projection label; all failure types, assertions, stack suffixes and outcomes are preserved. PUBLIC_PROJECTION_MAP records original and projected identities and exact substitutions. Original raw path-bearing receipts stay private. Exact reversal requires the privately retained original prefix/interpreter string, and was checked before staging. BOUNDED_RUN_001.txt is an exact original alias of the path-bearing receipt and is represented by that same projection.

ATTEMPTS, source-normalization patch/receipts, the original producer receipt and failed separate-reviewer status remain unchanged. PUBLIC_PARENT_FINANCIAL_REVIEW is the accepted corrected parent financial review, including additional generated Decimal cash/funding/fee checks. It is not a successful separate reviewer-agent run. Producer checks and parent checks do not imply historical or profitability certification.
