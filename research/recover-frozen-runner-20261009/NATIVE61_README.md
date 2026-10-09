# Original native61 data recovery and bounded validation

May 1–July 1 exclusive, 2024, CORE5 in BTC/ETH/SOL/XRP/DOGE order.
This is already-seen chronological development. There is no model fitting,
threshold change, recipe search, new exchange download or hourly synthesis.

`NATIVE61_INPUT_IDENTITIES.json` binds the original public H1 archive, all70
normalized files and the exact offline normalizer. All11 public parts, ZIP CRC
and292 manifest members were checked. All60 monthly minute Parquets regenerated
byte-exact under pandas2.2.3/pyarrow23.0.1. May–June is complete:305 asset-days,
87,840 minutes per asset,878,400 trade+mark rows and915 signed funding events.
Original public archive/checksum and retrieval evidence stays in external STATE.
Raw market archives are referenced rather than uploaded again.

The two frozen1024-head requests are read only from public commit
`d76b946d460e630e12f5b0ac320891f41d6f41e4`, path
`research/two-expert-exact-recovery-20261009/coin_two_expert_native61_request_handoff_20261009.zip`.
Its46,164 bytes SHA256 is
`92c8e4ab2accea0f8e16ca790c7f50111e909c7e42294ddffb3afc43769e61b1`.
This payload is not republished, and its cancelled branch update is not retried.
All61 budgets and signed fractions for each head passed the restored original
E5 mapper with exactly zero error; original H1 expert/covariance/price arrays and
causal clocks match. `NATIVE61_PREFLIGHT.json` records the completed gates.

`NATIVE61_PLAN.json` freezes four serial, independent fresh10,000-USDT wallets:
NO_CASH, WITH_CASH, fixed50/50 VOL/CSMOM, and CASH.5/VOL.25/CSMOM.25.
Original controls' audited journal bodies were not recovered; transcribed
numbers do not stand in for new financial evidence. The user separately
authorized these two fresh references after the data/mapper gates.

Original financial engine SHA318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585
is unchanged. Only signed NAV fractions enter its own .99×currentNAV/completed
daily-close quantity construction. Original guard-OFF, BASE27, funding1,
isolated1x/MMR.005, dailyL1.1, risk/capacity/latency/expiry and paid terminal
closure conventions remain. Each wallet has one CPU,6GB address-space cap,
600-second wall/CPU cap and15GiB disk reserve. Historical venue/account rules
remain conditional and uncertified.

Recovery uses existing pinned Git objects only:

```bash
python recover_h1.py --repo COIN_SOURCE --state EXTERNAL_STATE --normalize
python native61.py check --state EXTERNAL_STATE --handoff RESTORED_HANDOFF --output EXTERNAL_STATE/h1_validation/PREFLIGHT61.json
python native61.py run --state EXTERNAL_STATE --handoff RESTORED_HANDOFF --output FRESH_ACCOUNT_DIR --policy NO_CASH --plan-commit PUBLISHED_PLAN_COMMIT
python verify_native61.py --directory FRESH_ACCOUNT_DIR --state EXTERNAL_STATE --write
```

Use `requirements-native61.txt` and set one numerical-library thread. The
original helper refuses changed existing tables. `native61.py` blocks network
connections; output prefixes and actual timing/RSS receipts survive failures.
`verify_native61.py` reuses the original independent Decimal journal auditor;
optional actual-input checks add fee/friction/mark/shared-quote/funding checks.
No verifier independently rebuilds all order intents.
