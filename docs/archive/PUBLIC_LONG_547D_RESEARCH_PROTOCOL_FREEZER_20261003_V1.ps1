$ErrorActionPreference='Stop'
Set-Location 'D:/codex/coin'
function Digest([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
$sourcePath='reports/fast_research/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json'
$receipt=Get-Content -LiteralPath $sourcePath -Raw | ConvertFrom-Json -AsHashtable
if ($receipt.status -ne 'PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR' -or $receipt.source_files -ne 38 -or $receipt.actual_minute_rows -ne 1664640) { throw 'Actual exclusive38 source receipt required' }
$s=Get-Content -LiteralPath 'protocols/PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_V1.json' -Raw | ConvertFrom-Json -AsHashtable
$before=Digest 'protocols/PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_V1.json'
foreach ($key in @('reused_minute_input','reused_reference_report','reused_target_inputs','paired_control_reference','preceding_failure','smoke_pytest_expression')) { $s.Remove($key) }
$allowedCommon='3dfa0e3176791980de51e5bc990b1998f93eb24c02bdc1261a074eab92fb52f1'
foreach ($p in @($s.frozen_sources.Keys)) {
  $actual=Digest $p
  if ($p -eq 'scripts/investment/compare_simple_strategies.py') { if ($actual -ne $allowedCommon) { throw 'Unexpected accepted common source' }; $s.frozen_sources[$p]=$actual }
  elseif ($actual -ne $s.frozen_sources[$p]) { throw "Frozen parent bytes changed: $p" }
}
$s.contract_id='PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1'
$s.parent_protocol=@{path='protocols/PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_V1.json';sha256=$before;role='Reuse original native settlement/risk/public hooks; no old account replay'}
$s.classification='PREVIOUSLY_SEEN_547D_BINANCE_SPOT_BYBIT_VIP0_COUNTERFACTUAL_SCREENING_NOT_UNSEEN'
$s.primary_reference='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
$s.primary_selection_reason='Fixed public reference, one existing hybrid challenger, CASH; full long path falsification, no search'
$s.source_receipt=$sourcePath; $s.source_receipt_sha256=Digest $sourcePath
$s.source_scope='DEC2023_JUN2025'
$s.source_calendar=@('2023-12') + @(1..12 | ForEach-Object { '2024-{0:d2}' -f $_ }) + @(1..6 | ForEach-Object { '2025-{0:d2}' -f $_ })
$s.source_days_per_symbol=578
$s.folds=@(@{id='CONT547';period_start='2024-01-01';period_end_exclusive='2025-07-01'})
$s.strategy_ids=@('CASH','COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER','COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER')
$s.planned_ledgers=3; $s.warmup_days=31
$s.maximum_wall_seconds=1800; $s.maximum_new_owned_bytes=370000000
$s.module_combined_STATE_budget_bytes=400000000
$s.module_subbudgets=@{source=10000000;research=370000000;synthetic=10000000;independent_and_root=10000000}
$s.costs.spread_bps=@(8); $s.costs.nominal_roundtrip_bps=@(36)
$s.strategy_rules=@{PUBLIC_2H='Pinned MIT prior20 Donchian/SMA200 complete closed2h entry and exit; original COIN .3 long sizing';HYBRID='Same pinned closed2h entry, existing prior20 complete closed1h exit; jointly changes exit horizon/frequency';CASH='Existing fixed zero target';causality='Complete causal200-bar warmup only; same past30day/min20 causal risk, 1minute+1us execution, past capacity and lots';terminal='Original costed terminal zero target; residual dust marked, never discarded';selection='Three predefined full547day accounts, one spread8 cost, zero model fits/HPO or monthly account reset'}
$s.required_smoke_receipt='reports/fast_research/PUBLIC_LONG_547D_BOUNDARY_TINY_20261003_V1.json'
$s.smoke_test_path='tests/test_public_long_development_adapter.py'
$s.research_question='Does the frozen public2h or existing hybrid retain any net economic advantage over CASH across full547days after unchanged Bybit VIP0 costs and causal common risk?'
$s.return_reporting='Single continuous547day account per strategy; no monthly selection/reset/curve stitching; descriptive CAGR is not future APR'
$s.continuity_invariants=@{fees='Bybit VIP0 Spot10bp/side received asset; slip4bp/side/fullspread8bp';cash_reset='Only Jan1 once per new account';warmup='2023-12-01..<2024-01-01, no warmup capital or fills';dates='2024-01-01..<2025-07-01';source='Exact38 current byte identities matched to sealed oldQA, newly read immutable Arrow for original engine';model_fit=0}
$s.limitations=@('Previously used training/test historical span, development SCREENING only; not new OOS or native Bybit execution','Binance normalized minute OHLC/previous-minute quote-volume capacity proxies; actual BBO/depth/filters/account fee not proven','Current fixed Bybit VIP0 fees are counterfactual on history; buy base/sell quote settlement reused','Common caps and volatility mechanism are equal rules, not equal realized risk; original compressed intent risk scaling and passive cap drift retained','Minute close/daily MDD reported separately; all-event MDD is not established by minute observations alone','Gross same-net-received-quantity diagnostic plus fees/spread/slippage bridge is not a fee-free re-simulated account','Original forced terminal target/latency/lot/capacity can leave marked positive dust','547day descriptive CAGR and Sharpe do not establish sustainable long-term APR; locked and future eligibility remain untouched')
$s.created_before_new_economics_utc=[DateTime]::UtcNow.ToString('o')
$s.actual_freeze_git_commit=(git rev-parse HEAD).Trim()
$s.fixed_budget_reason='Original immutable IPC estimated160.45MB from accepted440640row42471691B metadata; original IO preserved'
foreach ($p in @('scripts/investment/public_long_development_adapter.py','tests/test_public_long_development_adapter.py',$sourcePath,'scripts/investment/public_long_source_reuse.py','protocols/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json','reports/fast_research/PUBLIC_LONG_DEVELOPMENT_STATIC_REUSE_20261003_V1.json','docs/archive/PUBLIC_LONG_547D_RESEARCH_PROTOCOL_FREEZER_20261003_V1.ps1')) { $s.frozen_sources[$p]=Digest $p }
$out='protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json'
if (Test-Path -LiteralPath $out) { throw 'Exclusive new protocol required' }
[IO.File]::WriteAllText((Join-Path (Get-Location) $out),($s | ConvertTo-Json -Depth 35)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
@{path=$out;sha256=Digest $out;source_sha256=$s.source_receipt_sha256;source_count=38;planned_ledgers=3;head=$s.actual_freeze_git_commit} | ConvertTo-Json
