# Frozen forecast economic relevance diagnostic

One read-only comparison of the existing fixed21-day CORE5 market-return
forecasts against subsequent VOL-minus-SHORT and VOL-minus-CS outcomes in all
four original folds. Positive forecast favors VOL; zero is the fixed sign
threshold. No fit, retuning, threshold search, data download, model inference,
new economic rollout, or selector change.

Outcomes are NAV[k+21]/NAV[k]−1 on each frozen continuous standalone control
wallet, with its inherited holdings, ramp, all saved costs/funding, eligibility
and endogenous risk reductions. They are daily surrogate marked subperiod
returns, not fresh21-day accounts, switching profits or native execution.

The original wallet has62 active intervals and a paid terminal close. Starts
0…41 support42 full21-active-interval windows. Start42 has20 active intervals
plus paidclose; report it separately, retaining all43 original starts and the
original disjoint starts0/21/42. The full-active disjoint subset is0/21 only.
Forecast labels use completed daily closes; saved wallets use00:01 execution
marks. No outcome-selected exclusions. Statistical effectiveN remains unknown.

Pearson, Spearman with average tie ranks, and sign agreement are reported per
fold. Exact contrast ties are counted and excluded from sign denominators.
Comparisons are the frozen causal prefix-mean forecast, constant VOL, constant
other, and uninformed fair-sign expected50%. Constant correlation is undefined.
No pooled inference or p-values; two or three disjoint spans are extremely few.

Executable: `READ_ECONOMIC_RELEVANCE.py --root CHECKOUT --output NEW_OUTPUT`
through the existing bounded resource guard. Python3.12, installed NumPy2.5.3;
pytest9.1.1/Ruff0.16.9 for the focused tests. No dependency installation.
Source and input hashes, maturity/fidelity audit and fixed choices are recorded
in [PROTOCOL.json](PROTOCOL.json) before any association calculation.
