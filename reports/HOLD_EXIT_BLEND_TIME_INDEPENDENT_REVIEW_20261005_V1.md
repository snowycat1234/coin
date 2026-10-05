# D074独立限定复核

实际helper SHA 1b6e5ec7d53d75c173b77c20795ea735bb0338fa21e4007330adb04838074ded；实际RESULT SHA 57345578e63f47e953f1487c7fde77521c62e38b5bdd3860fc0590d1ce16f1f3；task c67e3900f7e04d929e476d369d1202f2 exit0。

PASS：8×303正确UTC端点、完整10k及终现金桥；60位Decimal直接log/PnL、40月/12段/4总桥；所有每日峰/首次水下/谷/恢复/末端及右删失、日波动/MDD；手算初始capital峰和相等恢复；111 toy抽样独立索引及分位数。误差上限 {"terminal_NAV_USDT": 0.0, "net_PnL_USDT": 7.958078640513122e-13, "log_telescoping": 0.0, "episode_NAV_USDT": 0.0, "episode_depth_fraction": 5.551115123125783e-17, "actual_daily_volatility": 9.71445146547012e-17, "actual_daily_MDD": 5.551115123125783e-17, "reported_daily_MDD": 5.551115123125783e-17, "reported_actual_volatility": 9.71445146547012e-17, "segment_increment_USDT": 0.0, "segment_log_increment": 1.4051260155412137e-15, "slice_start_NAV_USDT": 0.0, "slice_end_NAV_USDT": 0.0, "slice_net_USDT": 0.0, "slice_account_log": 1.4432899320127035e-15, "slice_actual_return": 1.5543122344752192e-15, "paired_terminal_log": 0.0, "month_out_USDT": 0.0, "reported_mean_log": 1.937323169048195e-18, "toy_circular_percentile": 4.163336342344337e-17}。

限定：不新市场重放/target重算/实测原生产品；不独立重估24k经验bootstrap端点，只有配置/区间身份及toy kernel核验；不校正选择偏差，不认证资金单位、历史native成本、匹配风险alpha或长期APR。独立helper由子agent作者写，主模块由root写；root仅实际运行与封存。作者任务在交付草稿后遇额度限制，不把草稿当实际通过，实际证据来自本机真实exit0。
