# One fresh512 versus exact warm control

The prescribed fresh initialization fit is complete: 13,699 parameters, original
778 chronological training dates in five natural wallets, exact prefix-fitted
907-row scaler, fixedseed20261009, same date-weighted charged objectivev2 and
512 updates. No architecture/objective/data/normalization difference; the
comparability audit matched all778 copied-weight requests bitwise and reproduced
the warm terminal objective exactly. Initial snapshot/source/protocol were
public and verified at `34c73c2d28947d7847a11a8c9f15ba24bccdd860` before fitting.
No failure, new seed, retry, sweep, download or continuation beyond512.

| Metric | Fresh initialization | Exact warm control |
|---|---:|---:|
| TRAIN loss at stage start | -5.94127354723e-05 | -0.000940114983823 |
| TRAIN terminal loss | -0.00110658319896 | -0.00111302241219 |
| Seen May–June PnL, 10k wallet | -364.71 | -502.47 |
| Seen maximum drawdown | 4.204% | 5.665% |
| Mean request CASH/VOL/CS/SHORT | 0.938%/40.605%/19.614%/38.843% | 0.154%/49.676%/37.371%/12.799% |
| Base/head Adam age | 512/512 | 1292/512 |

PnL difference fresh−warm: +137.76 USDT;
this is a comparison difference, not an additional account profit. Both are
seen-development approximate daily-boundary executions, not out of sample or
native financial qualification. The warm comparator is pinned directly to
`d3d57332ca45b7a4443108db21f46abad0e1ac99`, model
`7b0f0a6c58fec8efd2aacec5c5abd41ec2aca68fa4c27432a9770b59acb594fd`.
This compares prescribed initialization regimes with different model/Adam/RNG
and lifetime data/optimizer exposure; it does not isolate initial weights alone.

Fresh terminal TRAIN loss is only 0.58% worse in absolute-loss magnitude than
warm, yet the seen allocation changes materially. Seen CASH request mean rises
from 0.154% to 0.938%, and SHORT rises from
12.799% to 38.843%. The investment gate exceeds0.99 on
52.46% of fresh decisions
versus100% warm; its derivative is below0.001 on0% versus49.18%. Fresh TRAIN
mean CASH is 6.024%, but seen
mean CASH remains under1%. Fresh has reduced cash-gate saturation without
learning enough cash use to avoid the seen-period loss. Improvement is partial:
both absolute PnLs remain negative. Initialization/history regime sensitivity is
supported by this pair; generalization and pure weights-only attribution are not.

Fresh seen gates:
- r: mean 0.392459, above0.99 0.00%, below0.01 45.90%, derivative<0.001 42.62%.
- s: mean 0.990617, above0.99 52.46%, below0.01 0.00%, derivative<0.001 0.00%.
- w: mean 0.586245, above0.99 26.23%, below0.01 34.43%, derivative<0.001 0.00%.

`s` invests, `w` divides VOL/CS within the non-short pair, and `r` allocates
SHORT within invested budget. Request means are before the unchanged ramp/risk
mapper, and can differ from paid executed exposure. Full TRAIN/seen gate
statistics and mapped-budget means are retained in RESULT.json. Fresh allocated
gross max 0.328540, per-asset max
0.120079; fees 15.611169, spread
11.353474, slippage 11.353474, funding -3.387279.
Risk events0; paid terminal CASH verified. Fixed512 is an endpoint, not a
convergence certificate. The mixed three native fold results remain the evidence
for conditional signal with period instability; this seen ablation cannot
establish generalization or impossibility.

Terminal512 was frozen and complete native61 E6 requests were published/read
back before this score. Separate executor owns native replay; no native wallets
were run here. [native61 bundle](native61-requests/EXP_FRESH_DATE_512/MANIFEST.json),
[result](RESULT.json), [receipt](RECEIPT.json), [prefit audit](COMPARABILITY.json),
[executable source and dependency recipe](../../modules/temporal_fresh_initialization/README.md).
12 focused tests/Ruff pass; all source bytes remain identical to prefit publication.
