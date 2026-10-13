# Fixed four-arm original 2021 strategy comparison

All four original 2021 fine-grid cases are retained, including economic halts and unavailable cases. Report creates zero wallets, advances zero financial steps and reruns zero controls.

Each arm uses its own independent 10,000 USDT one-way wallet. All rows come from one authorized run state; no reused comparator wallets.

| Arm | Class | Minutes | Marked PnL USDT | Paid PnL USDT | Minute DD | Full daily vol | Observed daily vol | Worst 30 complete days |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| STATIC50 | FULL_PAID_FLAT | 525600/525600 | 2499.489571 | 2499.489571 | 5.112714% | 9.026628% | 9.026628% | -3.274850% |
| SMA200_10PCT | FULL_PAID_FLAT | 525600/525600 | 1449.431934 | 1449.431934 | 10.685211% | 12.222489% | 12.222489% | -6.037196% |
| EXACTHALF | FULL_PAID_FLAT | 525600/525600 | 2047.333835 | 2047.333835 | 6.349391% | 9.280826% | 9.280826% | -4.168215% |
| VOL_MATCHED | FULL_PAID_FLAT | 525600/525600 | 1748.957132 | 1748.957132 | 6.890807% | 9.347177% | 9.347177% | -5.029364% |

| Arm | Mean/max target gross | Mean/max actual gross | Mean actual signed net/max absolute | Mean L1 target gap | Turnover USDT | Fees USDT | Execution cost USDT | Funding USDT | Trade legs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| STATIC50 | 0.167604/0.537177 | 0.165762/0.538906 | 0.063495/0.176911 | 0.004981 | 113203.474841 | 62.261911 | 90.564585 | -168.941192 | 1231 |
| SMA200_10PCT | 0.167022/0.459714 | 0.165280/0.518173 | 0.073798/0.190299 | 0.005114 | 136511.647553 | 75.081406 | 109.210599 | -367.180414 | 1465 |
| EXACTHALF | 0.123027/0.465806 | 0.121571/0.462700 | 0.068649/0.148447 | 0.003977 | 112876.658195 | 62.082162 | 90.302904 | -265.467724 | 1401 |
| VOL_MATCHED | 0.085371/0.186569 | 0.084162/0.187474 | 0.084162/0.187474 | 0.002805 | 18168.234346 | 9.992529 | 14.535890 | -261.446177 | 903 |

Target statistics use all 365 frozen decisions. Actual exposure statistics use the observed completed-minute horizon. Neither equates target gross with actual gross or realized risk.

## Saved account details

STATIC50: account ACTIVE; completion COMPLETE_CONDITIONAL_ACCOUNT; halts 0; stop_us None; exact flat true; residual gross USDT 0.000000; residual signed marked USDT per symbol {"BTCUSDT":0.0,"DOGEUSDT":0.0,"ETHUSDT":0.0,"SOLUSDT":0.0,"XRPUSDT":0.0}.
Exact terminal quantities {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}; rejections {"BELOW_MIN_NOTIONAL_OR_CAPACITY":5677,"FIVE_ATTEMPTS_EXPIRED":1370,"PARTIAL":1180}; journals {"breaches":0,"extrema":3,"funding":5475,"rejections":8227,"trades":1231}.
Existing execution-cost components: half-spread 45.282293 USDT; slippage 45.282293 USDT. No additional charge.
SMA200_10PCT: account ACTIVE; completion COMPLETE_CONDITIONAL_ACCOUNT; halts 0; stop_us None; exact flat true; residual gross USDT 0.000000; residual signed marked USDT per symbol {"BTCUSDT":0.0,"DOGEUSDT":0.0,"ETHUSDT":0.0,"SOLUSDT":0.0,"XRPUSDT":0.0}.
Exact terminal quantities {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}; rejections {"BELOW_MIN_NOTIONAL_OR_CAPACITY":7150,"FIVE_ATTEMPTS_EXPIRED":1709,"PARTIAL":1402}; journals {"breaches":0,"extrema":3,"funding":5475,"rejections":10261,"trades":1465}.
Existing execution-cost components: half-spread 54.605299 USDT; slippage 54.605299 USDT. No additional charge.
EXACTHALF: account ACTIVE; completion COMPLETE_CONDITIONAL_ACCOUNT; halts 0; stop_us None; exact flat true; residual gross USDT 0.000000; residual signed marked USDT per symbol {"BTCUSDT":0.0,"DOGEUSDT":0.0,"ETHUSDT":0.0,"SOLUSDT":0.0,"XRPUSDT":0.0}.
Exact terminal quantities {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}; rejections {"BELOW_MIN_NOTIONAL_OR_CAPACITY":7228,"FIVE_ATTEMPTS_EXPIRED":1709,"PARTIAL":1317}; journals {"breaches":0,"extrema":3,"funding":5475,"rejections":10254,"trades":1401}.
Existing execution-cost components: half-spread 45.151452 USDT; slippage 45.151452 USDT. No additional charge.
VOL_MATCHED: account ACTIVE; completion COMPLETE_CONDITIONAL_ACCOUNT; halts 0; stop_us None; exact flat true; residual gross USDT 0.000000; residual signed marked USDT per symbol {"BTCUSDT":0.0,"DOGEUSDT":0.0,"ETHUSDT":0.0,"SOLUSDT":0.0,"XRPUSDT":0.0}.
Exact terminal quantities {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}; rejections {"BELOW_MIN_NOTIONAL_OR_CAPACITY":5953,"FIVE_ATTEMPTS_EXPIRED":1370,"PARTIAL":898}; journals {"breaches":0,"extrema":3,"funding":5475,"rejections":8221,"trades":903}.
Existing execution-cost components: half-spread 7.267945 USDT; slippage 7.267945 USDT. No additional charge.

## All six pairwise contrasts

Every contrast is b minus a. Paid cash and annual paid-return deltas require both complete paid-flat wallets on the same full calendar.

SMA200_10PCT_minus_STATIC50: paid cash delta -1050.057637 USDT; annual paid-return delta -10.500576%; same-full-calendar marked delta -1050.057637 USDT.
Full frozen schedule target deltas {"active_symbol_day_cells":339,"cash_days":-91,"max_abs_signed_target_net":0.023193999467863297,"max_target_gross":-0.0774637793669754,"mean_signed_target_net":0.010835458132855982,"mean_target_gross":-0.0005820433087879717}. These are descriptive target deltas, independent of actual wallet horizons.
Same-full-calendar observed deltas {"annual_daily_vol":0.031958611179478014,"execution_cost_USDT":18.646013143889988,"fees_USDT":12.819494991703486,"funding_USDT":-198.239221717243,"gross_fill_turnover_USDT":23308.17271218814,"half_spread_cost_USDT":9.323006571944994,"halt_count":0,"marked_PnL_USDT":-1050.0576369155542,"max_actual_abs_signed_net":0.013387707644429175,"max_actual_gross":-0.0207329416572819,"mean_actual_gross":-0.0004819189490523901,"mean_actual_signed_net":0.01030261496786121,"mean_l1_target_weight_gap":0.00013235218832986784,"minute_drawdown":0.055724964547728795,"risk_reduction_signal_count":0,"slippage_cost_USDT":9.323006571944994,"terminal_residual_gross_notional_USDT":0.0,"trade_legs":234,"worst_observed_30_complete_days":-0.027623466227046478}.
Same-full-calendar rejection-count deltas {"BELOW_MIN_NOTIONAL_OR_CAPACITY":1473,"FIVE_ATTEMPTS_EXPIRED":339,"PARTIAL":222}; exact terminal quantity deltas {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}.
Matched daily volatility scope SAME_FULL_CALENDAR: a/b 9.026628%/12.222489%; b-a 3.195861%.

EXACTHALF_minus_STATIC50: paid cash delta -452.155736 USDT; annual paid-return delta -4.521557%; same-full-calendar marked delta -452.155736 USDT.
Full frozen schedule target deltas {"active_symbol_day_cells":339,"cash_days":-91,"max_abs_signed_target_net":-0.002621487949751755,"max_target_gross":-0.07137160107724899,"mean_signed_target_net":0.005417729066427984,"mean_target_gross":-0.044577007593645204}. These are descriptive target deltas, independent of actual wallet horizons.
Same-full-calendar observed deltas {"annual_daily_vol":0.002541985818203016,"execution_cost_USDT":-0.2616812018790142,"fees_USDT":-0.17974915521275392,"funding_USDT":-96.52653177185059,"gross_fill_turnover_USDT":-326.81664584137616,"half_spread_cost_USDT":-0.1308406009395071,"halt_count":0,"marked_PnL_USDT":-452.15573564297847,"max_actual_abs_signed_net":-0.02846474766462445,"max_actual_gross":-0.07620584342772424,"mean_actual_gross":-0.04419100138942289,"mean_actual_signed_net":0.00515384811306252,"mean_l1_target_weight_gap":-0.0010039103469373532,"minute_drawdown":0.012366769614428619,"risk_reduction_signal_count":0,"slippage_cost_USDT":-0.1308406009395071,"terminal_residual_gross_notional_USDT":0.0,"trade_legs":170,"worst_observed_30_complete_days":-0.008933648680225503}.
Same-full-calendar rejection-count deltas {"BELOW_MIN_NOTIONAL_OR_CAPACITY":1551,"FIVE_ATTEMPTS_EXPIRED":339,"PARTIAL":137}; exact terminal quantity deltas {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}.
Matched daily volatility scope SAME_FULL_CALENDAR: a/b 9.026628%/9.280826%; b-a 0.254199%.

VOL_MATCHED_minus_STATIC50: paid cash delta -750.532438 USDT; annual paid-return delta -7.505324%; same-full-calendar marked delta -750.532438 USDT.
Full frozen schedule target deltas {"active_symbol_day_cells":0,"cash_days":0,"max_abs_signed_target_net":0.040928118178334305,"max_target_gross":-0.3506080711942463,"mean_signed_target_net":0.021341236921644427,"mean_target_gross":-0.08223285234124171}. These are descriptive target deltas, independent of actual wallet horizons.
Same-full-calendar observed deltas {"annual_daily_vol":0.0032054905509183856,"execution_cost_USDT":-76.02869564452223,"fees_USDT":-52.26938227237519,"funding_USDT":-92.50498481535865,"gross_fill_turnover_USDT":-95035.24049522761,"half_spread_cost_USDT":-38.014347822261115,"halt_count":0,"marked_PnL_USDT":-750.5324383488203,"max_actual_abs_signed_net":0.010562496603053195,"max_actual_gross":-0.35143190463206747,"mean_actual_gross":-0.08159979759970903,"mean_actual_signed_net":0.020666823876697646,"mean_l1_target_weight_gap":-0.0021759106846501474,"minute_drawdown":0.017780925562682848,"risk_reduction_signal_count":0,"slippage_cost_USDT":-38.014347822261115,"terminal_residual_gross_notional_USDT":0.0,"trade_legs":-328,"worst_observed_30_complete_days":-0.017545145310294497}.
Same-full-calendar rejection-count deltas {"BELOW_MIN_NOTIONAL_OR_CAPACITY":276,"FIVE_ATTEMPTS_EXPIRED":0,"PARTIAL":-282}; exact terminal quantity deltas {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}.
Matched daily volatility scope SAME_FULL_CALENDAR: a/b 9.026628%/9.347177%; b-a 0.320549%.

EXACTHALF_minus_SMA200_10PCT: paid cash delta 597.901901 USDT; annual paid-return delta 5.979019%; same-full-calendar marked delta 597.901901 USDT.
Full frozen schedule target deltas {"active_symbol_day_cells":0,"cash_days":0,"max_abs_signed_target_net":-0.02581548741761505,"max_target_gross":0.006092178289726413,"mean_signed_target_net":-0.005417729066427998,"mean_target_gross":-0.04399496428485723}. These are descriptive target deltas, independent of actual wallet horizons.
Same-full-calendar observed deltas {"annual_daily_vol":-0.029416625361274998,"execution_cost_USDT":-18.907694345769002,"fees_USDT":-12.99924414691624,"funding_USDT":101.71268994539241,"gross_fill_turnover_USDT":-23634.989358029517,"half_spread_cost_USDT":-9.453847172884501,"halt_count":0,"marked_PnL_USDT":597.9019012725757,"max_actual_abs_signed_net":-0.04185245530905363,"max_actual_gross":-0.05547290177044234,"mean_actual_gross":-0.0437090824403705,"mean_actual_signed_net":-0.005148766854798689,"mean_l1_target_weight_gap":-0.001136262535267221,"minute_drawdown":-0.043358194933300176,"risk_reduction_signal_count":0,"slippage_cost_USDT":-9.453847172884501,"terminal_residual_gross_notional_USDT":0.0,"trade_legs":-64,"worst_observed_30_complete_days":0.018689817546820975}.
Same-full-calendar rejection-count deltas {"BELOW_MIN_NOTIONAL_OR_CAPACITY":78,"FIVE_ATTEMPTS_EXPIRED":0,"PARTIAL":-85}; exact terminal quantity deltas {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}.
Matched daily volatility scope SAME_FULL_CALENDAR: a/b 12.222489%/9.280826%; b-a -2.941663%.

VOL_MATCHED_minus_SMA200_10PCT: paid cash delta 299.525199 USDT; annual paid-return delta 2.995252%; same-full-calendar marked delta 299.525199 USDT.
Full frozen schedule target deltas {"active_symbol_day_cells":-339,"cash_days":91,"max_abs_signed_target_net":0.01773411871047101,"max_target_gross":-0.27314429182727096,"mean_signed_target_net":0.010505778788788445,"mean_target_gross":-0.08165080903245374}. These are descriptive target deltas, independent of actual wallet horizons.
Same-full-calendar observed deltas {"annual_daily_vol":-0.028753120628559628,"execution_cost_USDT":-94.67470878841222,"fees_USDT":-65.08887726407868,"funding_USDT":105.73423690188434,"gross_fill_turnover_USDT":-118343.41320741575,"half_spread_cost_USDT":-47.33735439420611,"halt_count":0,"marked_PnL_USDT":299.52519856673393,"max_actual_abs_signed_net":-0.00282521104137598,"max_actual_gross":-0.33069896297478557,"mean_actual_gross":-0.08111787865065664,"mean_actual_signed_net":0.010364208908836436,"mean_l1_target_weight_gap":-0.0023082628729800153,"minute_drawdown":-0.03794403898504595,"risk_reduction_signal_count":0,"slippage_cost_USDT":-47.33735439420611,"terminal_residual_gross_notional_USDT":0.0,"trade_legs":-562,"worst_observed_30_complete_days":0.010078320916751982}.
Same-full-calendar rejection-count deltas {"BELOW_MIN_NOTIONAL_OR_CAPACITY":-1197,"FIVE_ATTEMPTS_EXPIRED":-339,"PARTIAL":-504}; exact terminal quantity deltas {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}.
Matched daily volatility scope SAME_FULL_CALENDAR: a/b 12.222489%/9.347177%; b-a -2.875312%.

VOL_MATCHED_minus_EXACTHALF: paid cash delta -298.376703 USDT; annual paid-return delta -2.983767%; same-full-calendar marked delta -298.376703 USDT.
Full frozen schedule target deltas {"active_symbol_day_cells":-339,"cash_days":91,"max_abs_signed_target_net":0.04354960612808606,"max_target_gross":-0.27923647011699737,"mean_signed_target_net":0.015923507855216443,"mean_target_gross":-0.037655844747596506}. These are descriptive target deltas, independent of actual wallet horizons.
Same-full-calendar observed deltas {"annual_daily_vol":0.0006635047327153698,"execution_cost_USDT":-75.76701444264322,"fees_USDT":-52.089633117162435,"funding_USDT":4.021546956491932,"gross_fill_turnover_USDT":-94708.42384938624,"half_spread_cost_USDT":-37.88350722132161,"halt_count":0,"marked_PnL_USDT":-298.3767027058418,"max_actual_abs_signed_net":0.03902724426767765,"max_actual_gross":-0.27522606120434323,"mean_actual_gross":-0.037408796210286144,"mean_actual_signed_net":0.015512975763635126,"mean_l1_target_weight_gap":-0.0011720003377127942,"minute_drawdown":0.005414155948254229,"risk_reduction_signal_count":0,"slippage_cost_USDT":-37.88350722132161,"terminal_residual_gross_notional_USDT":0.0,"trade_legs":-498,"worst_observed_30_complete_days":-0.008611496630068993}.
Same-full-calendar rejection-count deltas {"BELOW_MIN_NOTIONAL_OR_CAPACITY":-1275,"FIVE_ATTEMPTS_EXPIRED":-339,"PARTIAL":-419}; exact terminal quantity deltas {"BTCUSDT":"0E-8","DOGEUSDT":"0E-8","ETHUSDT":"0E-8","SOLUSDT":"0E-8","XRPUSDT":"0E-8"}.
Matched daily volatility scope SAME_FULL_CALENDAR: a/b 9.280826%/9.347177%; b-a 0.066350%.

Four-way common completed-minute prefix: 525600. It excludes post-minute halt marks and contains no full-year or paid-profit claim.

## Original target admission and interpretation

STATIC50 keeps its first 91 daily decisions, January 1 through April 1, in cash. SMA200_10PCT retains original masks: 25 days with 3 eligible assets, 66 days with 4, and 274 days with 5. EXACTHALF is the bit-exact half-STATIC50 plus half-SMA schedule; its first 91 decisions are half-SMA. All 365 decisions remain, with no final forced-cash target.
UTC completed-day NAV simple returns, initial NAV 10000; sample std ddof=1 times sqrt(365). Observed-prefix volatility uses complete UTC days only and is not a full-year estimate. Worst 30-day returns use 30 complete UTC days, excluding incomplete days.
Small or economically material exact terminal residue remains marked-only unless the complete account is exactly flat and terminal cash is realized. No free terminal flattening.
Funding retains the raw-fraction interpretation and unchanged signed economics of the frozen run. Funding units and source provenance remain conditional.
Seen development replication only. This is not OOS evidence, native quantity-resolution certification, venue-validated fills, alpha or promised APR. All prior strategy STOP statuses remain.
Half-spread and slippage split the existing execution cost equally under the unchanged BASE27 4bp+4bp assumption; this is arithmetic attribution, not additional charging.
Binance observations, derived-mark overlay and assumed Bybit costs/fine grid retain their existing qualifications.
