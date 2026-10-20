# Published 2023 source recovery

This package recovers only previously published CORE5 2023 research inputs. It is not a strategy test, a wallet checkpoint, or recovery of an interrupted account. It does not establish profitability or native venue economic authority.

The immutable manifest identifies 312 files (158,865,245 bytes): all 239 raw archive parts, the original code closure, source certificates, daily closes and three funding transport parts. Reassembled originals comprise 120 monthly trade/mark archives plus five February 24 daily mark repairs. Each part and original archive was SHA-256 verified; all 125 original ZIPs passed CRC.

Run `python recover_public_cache.py --destination DIRECTORY` for offline verification. Add `--download` to fetch only missing files from the exact public GitHub commit URLs. The script does not overwrite mismatches, retry errors, request credentials, or fall back to other hosts. It never contacts a market-data provider. Access errors stop the operation. Current recovery used the GitHub connector's base64 file route, verified byte-for-byte; the standalone urllib network route has not been live tested here. Its cached-file validation and fail-closed cases have been tested.

Keep this entire small package alongside the downloaded directory; all large inputs already exist at the manifest's public immutable GitHub commits and are not duplicated in this branch. Source reconstruction and the remaining limitations are reported separately. Only 2023 funding columns are projected by an explicit timestamp predicate; unrelated feature members and held-out 2026 values are not inspected.

Generated execution tests in the sibling package are software checks, not substitutes for strategy economics. No old wallet is rerun. No claim is made that the lost 565-day account state was recovered.
