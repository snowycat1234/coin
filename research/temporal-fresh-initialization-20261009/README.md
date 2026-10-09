# Fresh versus warm initialization — one fixed 512-update ablation

Exactly one fresh 13,699-parameter expanded-pool/current-expert GRU on the original
778 complete training dates (five independent natural wallets, 54/88/62/144/430).
Same date-weighted objective v2, seed20261009, dropout0.1, feature batch32, Adam and
caps/ramp/costs/funding/paid closure. Prefix recomputation exactly reproduces the
existing 907-row scaler, including provenance/arrays/counts. No design change.

Exact warm control: `GRU64_WEIGHT_DATE` at
`d3d57332ca45b7a4443108db21f46abad0e1ac99`. A separate copied-weight probe matches
all778 training requests bitwise and reproduces terminal loss
−0.001113022412191139 exactly. Actual fit loads a brand-new model, empty Adam and
fresh Python/NumPy/Torch RNG using the same recipe as the three fresh folds.
Fresh initial TRAIN loss −0.000059412735472286. This compares initialization
regimes: warm base Adam1292/new heads512 versus fresh all512; lifetime optimizer
and data exposure differ. It does not isolate initial weights alone.

Protocol, complete binding/source identities, initial checkpoint/model/Adam/RNG
and scaler are frozen here before any optimizer update. TRAIN diagnostics at
0/128/256/512; checkpoint every completed update. Bounded 1200s slices resume
the same run up to512, never restart a recipe or continue beyond512.

Terminal512 must be frozen before economic scoring. Export actual61 E6 requests
with complete source/model/scaler/current18expert-input/clock handoff first.
May–June is explicitly seen development, not out of sample. Native replay is
owned by the separate executor; no market downloads or additional wallets here.
The three native fold outcomes were +581.51/+735.22/−30.15 USDT versus fixed
VOL50/CS50 −403.86/+949.18/+393.97; this initialization test follows that mixed
transfer evidence without claiming universal selector failure.

Executable module and dependency recipe:
[modules/temporal_fresh_initialization](../../modules/temporal_fresh_initialization/README.md).
12 focused tests and Ruff pass; original reused source bytes remain exact.
[comparability](COMPARABILITY.json), [protocol](PROTOCOL.json),
[initial readiness](READY.json), [receipt](PREFIT_RECEIPT.json).
