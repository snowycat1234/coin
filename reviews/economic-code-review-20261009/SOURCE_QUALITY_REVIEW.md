# Final bounded source-quality checks

The SOL observations dominating funding/premium variance are authentic extreme
observations in Binance's official public archives. The stored pipeline values
match the raw records, calendar assignment and units; they are not demonstrated
placeholders, scaling mistakes or timestamp conversion errors. No active feature,
normalizer, scaler or training run was changed.

| Field | Observation day, UTC | Available decision, UTC midnight | Exact raw value | Model float32 value |
|---|---|---|---:|---:|
| funding |2022-11-09 |2022-11-10 |-0.05000000 |-0.05000000074505806 |
| funding |2022-11-10 |2022-11-11 |-0.17166137 |-0.171661376953125 |
| funding |2022-11-11 |2022-11-12 |-0.03584739 |-0.035847388207912445 |
| premium |2022-11-08 |2022-11-09 |-0.02045813 |-0.020458130165934563 |
| premium |2022-11-09 |2022-11-10 |-0.17475391 |-0.17475390434265137 |

Funding values are **arithmetic sums of dimensionless per-settlement rate
fractions within the completed UTC day**, not one settlement, an annualized rate,
a per-hour rate, a USDT price or a realized wallet return. On November10 the sum
is -17.166137% from 11 actual events. Six events are -0.02000000 (-2%) each; the
other five rates are -0.00937683, -0.00801579, -0.01610749, -0.01792917 and
-0.00023209. The archive records the interval changing from 8 to 4 to 2 hours.
November9 has four events summing to -5%; November11 has twelve summing to
-3.584739%. Repeated -0.02 entries are consistent with the announced funding cap,
not a missing-value sentinel.

Binance's dated
[November9,2022 announcement](https://www.binance.com/en/support/announcement/detail/e8be17e1e544418490e86723d84759f0)
states SOLUSDT's cap/floor was ±2% with increased settlement frequency starting
at20:00 UTC. It also allows further frequency adjustments without another
announcement. This supports the -0.02000000 → -2% unit interpretation for these
records. We do not change the inherited dataset-wide `UNCONFIRMED` marker: this
check certifies the stated source records, not every historical instrument.

Premium is the **dimensionless premium-index closing value**. It is a price-ratio
measure based on impact prices and the index, as described by
[Binance's formula](https://www.binance.com/en/support/faq/detail/360033525031).
November9's raw close -0.17475391 represents -17.475391%; it is not the funding
fee rate and not a daily average. The official daily premium bar has open
-0.02330991, high -0.01878405 and low -0.25536167, so its extreme close lies
within the recorded OHLC envelope. November8's close is -0.02045813.

## Source identity and minimal reproduction

Only two tiny official raw archives were downloaded, totaling **2708 bytes**:

| Archive | Bytes | SHA256 |
|---|---:|---|
| [SOL November funding](https://data.binance.vision/data/futures/um/monthly/fundingRate/SOLUSDT/SOLUSDT-fundingRate-2022-11.zip) |1620 |`73fbada102584d8e19cb9594f04471f589ff37404b0cf64c0bd7cb4ac4d4a157` |
| [SOL November daily premium](https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/SOLUSDT/1d/SOLUSDT-1d-2022-11.zip) |1088 |`ef4252b8a7bd9f476818bf9d0adcc4b4389e7cebead1d85bf1660fcf2b8e9431` |

Both match the independently fetched official `.CHECKSUM`, and ZIP CRC verifies.
The funding ZIP hash exactly matches the original producer's retained source
receipt in the feature transfer at `d901f130993b6f00ad6479dcc6a04b77627192b8`.
All **165** November raw event timestamps, intervals and rates match the cached
source-bound funding-event Parquet exactly. Summing the decimal CSV rate strings
within each requested day reproduces the retained daily double values within
6e-17 and the model NPZ values exactly after float32 conversion. Integer epoch
milliseconds, including actual 0–27ms settlement offsets, remain unchanged.
Observation day +one day gives the bound feature availability clock exactly.

All **30** official November daily premium closes match the retained source
feature table exactly. This is independent cross-frequency evidence: the original
producer used minute aggregation, while this small check uses the official1d
archive. The original premium minute-object checksum is absent from the compact
transfer, so full original minute-object byte identity is not asserted. The raw
daily close and float32 model value are nevertheless directly verified. No order
book or exchange-account settlement audit is claimed.

The three cached SOL Parquets were read from the already verified2.25MB feature
transfer; their individual hashes were checked against its `MEMBERS.json`.
[`SOURCE_QUALITY.json`](SOURCE_QUALITY.json) preserves those hashes, raw targeted
event strings/clocks, original funding receipt, float32 differences and all
assertion outcomes. [`source_quality_checks.py`](source_quality_checks.py) is the
portable read-only reproducer. It whitelists the relevant retained Parquet fields,
compares decimal source values and asserts source/feature identities. No market
ZIP or Parquet payload is copied into this review branch.

## The five CS warmup rows are now fully resolved

The first five decisions, May1–5,2024, carry the **April29 weekly ranking**.
[`public_cross_section_momentum.py:60–75`](https://github.com/snowycat1234/coin/blob/55ac3d2ee730b1cd1381696330a6abaf1925eb92/scripts/research/public_cross_section_momentum.py#L60)
requires31 contiguous completed closes for that ranking's30-return covariance
context. Its earliest required close is March30. The small `H1_VALIDATE` fragment's
May1 past30 returns reconstruct closes only from April1 onward: **March30 and
March31 are absent from that fragment**. Direct reconstruction therefore clears
the April29 raw target and cannot reproduce those first five held states. This
was a review-fixture warmup limitation, not a native/model input defect.

Those two closes already exist in the hash-verified pre-May feature NPZ. Using
its completed-close matrix plus the existing development append, with genuine
NaNs and the fixed calendar preserved, reproduces **all61 CS target rows exactly,
maximum error0**. The31×5 April29 ranking history is fully observed. No missing
price was padded, forward-filled, inferred or downloaded. The first56-row partial
match and its qualification remain historical test evidence; the full-source
check closes that qualification.

```bash
python source_quality_checks.py \
  --quality-root "$TARGETED_RAW_AND_VERIFIED_SOL_TABLES" \
  --evidence-root "$EXISTING_SMALL_VERIFIED_FEATURES" \
  --native-root "$SIGNAL_SOURCE_55AC3D2" \
  --original-portfolio "$SIGNAL_SOURCE_55AC3D2/modules/transformer_v2/portfolio.py" \
  --output "$NEW_STATE/source-quality.json"
```

The existing one-CPU,2GB,no-swap/no-GPU bounded launcher passed in9.57seconds,
maximum sampled RSS184.8MB. PyArrow CPU/I/O pools and reads were explicitly limited
to one thread. [`SOURCE_QUALITY_RESOURCES.json`](SOURCE_QUALITY_RESOURCES.json)
records the successful run. Zero fits, zero optimizer steps and zero wallet runs.
The bounded review stops here; no clipping or alternative normalization was added.
