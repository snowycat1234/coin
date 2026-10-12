Exact read-only bridge of the already published January31-day account. No account replay or new model/provider use. Source442479a395931acbbf93a85ac14481a6861538a4; result46610b98e39866ecead364080b6c895932e434d9.

Both independent Decimal NAV formulas pass: midprice bridge0E-35, fill-basis bridge2.385e-37USDT. Joint marked net22.0673 = LONG−197.2453 + SHORT219.3126USDT; the short contribution is not a separately tradable counterfactual. DOGE_LONG−122.9317 and BTC_LONG−50.5282 dominate loss. Fees4.66036/execution6.77866/fundingcash−.959649 remain charged. Remaining DOGE836.89824019 is marked118.4615148USDT; paid-flat gate remains failed.

Actual meanlong7.81884%/short4.92795%, maximumgross21.0085%. Tracking L1allminutes.321033%NAV/afterfiveattempts.084853%; includes price/NAVdrift and latency, not isolated execution PnL. Of151expired requests,118have substep remainders and33at least one step. Terminal five actual paid partial closes end with executable-sized DOGE, not free closure.

Two focused counterexamples pass. Fresh public restore reproduces RESULT and all CSVs exactly,0models/0wallets; evidence retains the first wrong-SHA command failure and the corrected exactSHA successful receipt.

Minimal restore from this branch:

    COIN_CPD_STATE=/workspace/drag-repro QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/drag-repro bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/short-account-drag-20261012/run.py --state /workspace/drag-repro/COLD --source-commit 442479a395931acbbf93a85ac14481a6861538a4 --expected-commit 46610b98e39866ecead364080b6c895932e434d9
