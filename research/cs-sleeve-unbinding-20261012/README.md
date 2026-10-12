One fixed CS long/short unbinding mechanism probe. This is an adaptation of the existing selector, not the paper LSTM reproduction or fresh out-of-sample evidence.

Exactly one Ridge(alpha=30), two utility outputs, old A46 features/181 training dates/scaler and original CASH/VOL/CS budget retained. Natural chronological internal Jan1-Sep13 2022; label true maturity before Sep15. No old59 outcome tuning, 2023/24 parsing, forced shorts, leverage redistribution or fee/risk/terminal relaxation. Two controls match allocated CS gross before VOL netting and risk; realized exposure need not match.

Source and protocol are frozen and published before fitting. Four focused tests pass, including missing decision/past-day refusal. Independent read-only review is recorded in evidence/PREFIT_REVIEW.json. See PROTOCOL.json for fixed information/economic gates and finite conditional native probe. Results will be appended separately; old January account is never rerun.

Actual source06f2f3dd90ad11e65a883f319d3cdb6e0cbdb109; resultc29a7c66af3f930da7902c35aeea2819f2344aa2. One fit,181actual positive-loss dates,256natural internal dates/245common mature outcomes. MSE worse train-mean by.2141%; paired95CI crosses zero. Independent-minus-grossmatched paid utility+.000104669,95CI[−.0000488623,+.000275904], both mean utilities negative. Both fixed gates FAIL: STOP_FIXED_SLEEVE_INCREMENT_GATE,0new native accounts. More negative target dates170vs160 is not proof of profit, independent riskmax7.822%vs6.389% is not matched risk. No retries or threshold/config changes.

Observed scientific pipeline.856642s including .004348s single Ridge fit; cold.889525s,0fits/0wallets. Result/checkpoint/181train-loss IDs/256predictions and targets/245paid references perarm are public. Exact zero-fit cold verification of all report/CSV/NPZ bytes passes.

Pandas emits an integer-cast warning on filling missing role maturities with int64max through a float series. Unknown dates are explicitly excluded by role membership, so they cannot enter the maturity mask; all selected role clocks are finite exactly represented values. The warning and original frozen source are preserved; no scientific result changed.

Minimal restore from this branch:

    COIN_CPD_STATE=/workspace/sleeve-repro QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/sleeve-repro bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/cs-sleeve-unbinding-20261012/run.py --state /workspace/sleeve-repro/COLD --source-commit 06f2f3dd90ad11e65a883f319d3cdb6e0cbdb109 --expected-commit c29a7c66af3f930da7902c35aeea2819f2344aa2

Historical raw funding units/charge mark/MMR/venue arrival authority remain conditional. This experiment did not pass the predictor/ranking gate, so native fee/slippage/funding/available-mask/risk/terminal modules are NOT_RUN here, rather than invented as realized results. Original January account remains independently reusable and unpaid.
