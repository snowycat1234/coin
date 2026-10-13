# Saved ORIGINAL fine STATIC50 2024 common prefix

This is a read-only export of the original fine-grid STATIC50 / CSH reference, not the guard or coarse arm. It does not re-run or advance any financial account and is not a new strategy result.

The window is 461,448 completed minute closes in (2024-01-01 00:00:00 UTC, 2024-11-16 10:48:00 UTC], with initial capital NAV 10,000 USDT as the drawdown and daily-return anchor. The 2024-11-16 10:49 halt observation is explicitly excluded. All 321 saved minute chunk SHA256 values, shape/dtype, and all 37 saved numeric column fingerprints were independently rechecked. The exact prefix matches the previously reviewed FOLLOW report at commit c63a936b7422f7dbf33f6234acebfb02a3b1f3c6.

Prefix marked NAV is 11514.994096874494 USDT; marked PnL is 1514.994096874494 USDT; completed-minute max drawdown is 0.09976521119170445. This is a marked, unpaid, incomplete-year endpoint. Annual paid return and prefix Decimal NAV are unavailable and remain null. The later halt marked PnL 1512.4794784332314 is not the same-clock prefix.

Minute NAV and risk/cost/exposure aggregates retain exact saved float64 semantics. PREFIX.json provides float.hex encodings, the aggregation rule and all bit fingerprints. Exact Decimal fees, execution cost, funding and fill turnover are independently summed from the saved journal strings through the same endpoint. Turnover is abs(position_delta) times fill_price, matching the frozen account code. The five unowned zero-position funding records contribute exact zero. The exact Decimal cost totals round to precisely the saved float64 cumulative columns. No Decimal prefix NAV is fabricated from the halt snapshot.

Files:
- PREFIX.json: portable metrics, endpoint, numeric semantics, original source/target/code/result hashes
- CHUNKS.json: saved per-chunk SHA/shape/count manifest; its canonical compact sorted JSON SHA is bound in PREFIX.json
- export_prefix.py: standalone read-only reconstruction from the saved workspace, using the reviewed observer algorithm; no financial imports, cold restore or network calls
- README.md: scope and file hashes

Reproduction requires the existing saved local workspace and NumPy. It intentionally does not download missing market data or state. Run:

python export_prefix.py --root /path/to/saved/workspace --output /new/empty/output-directory/PREFIX.json

The output directory must already exist and PREFIX.json and CHUNKS.json must not exist. The script never writes to the original source directories.

Only small synthetic research evidence and code are published. No raw market payload, wallet backup, trade journals, credentials or personal account information are included.

## SHA256

fa9c7a46dd9d9864498e5c0bd920386b7050017e5b5a91083fe01b86bc5852e2  CHUNKS.json
6fc26c921465fc407a152a5e54615168bc20bc1d3dd7aa61a3c24a0c1c8868fe  PREFIX.json
07d116fac09ac2522848a1c909e98c7f3fea32b64e4e775f6c9c22a2970fae87  export_prefix.py
