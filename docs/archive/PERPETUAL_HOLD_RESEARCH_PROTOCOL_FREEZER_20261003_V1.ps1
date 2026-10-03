param([ValidateSet('Smoke','Market')][string]$Phase)
$ErrorActionPreference='Stop';$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$p){(Get-FileHash -LiteralPath (Join-Path $root $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$p){Get-Content (Join-Path $root $p) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function WriteNew([string]$p,$v){if(Test-Path $p){throw "Exclusive path $p"};[IO.File]::WriteAllText((Join-Path $root $p),($v|ConvertTo-Json -Depth 50)+"`n",$enc)}
$old=ReadJson 'protocols/PERPETUAL_213_RESEARCH_20261003_V1.json';$hashes=[ordered]@{}
foreach($p in $old.frozen_sources.Keys){if((Digest $p) -ne $old.frozen_sources[$p]){throw "Old frozen dependency $p"};$hashes[$p]=$old.frozen_sources[$p]}
foreach($p in @('scripts/investment/perpetual_hold_research.py','scripts/investment/vol_managed_perpetual_target.py','tests/test_vol_managed_perpetual_target.py','docs/archive/PERPETUAL_HOLD_RESEARCH_SOURCE_20261003_V1.py','docs/archive/VOL_MANAGED_PERPETUAL_TARGET_SOURCE_20261003_V1.py','docs/archive/VOL_MANAGED_PERPETUAL_TARGET_TEST_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_HOLD_RESEARCH_PROTOCOL_FREEZER_20261003_V1.ps1','scripts/investment/perpetual_hold_source_reuse.py','docs/archive/PERPETUAL_HOLD_SOURCE_REUSE_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_HOLD_SOURCE_REUSE_FREEZER_20261003_V1.ps1','protocols/PERPETUAL_HOLD_SOURCE_REUSE_BINDING_20261003_V1.json','reports/fast_research/PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json','reports/fast_research/PERPETUAL_HOLD_INPUT_BINDING_20261003_V1.json','reports/fast_research/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json','reports/fast_research/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_20261003_V1.json')){$hashes[$p]=Digest $p}
$source=ReadJson 'reports/fast_research/PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json'
if($source.status -ne 'PASS_D044_EXISTING_ACCEPTED_SOURCE_ONLY_NO_REPEATED_QA'){throw 'Accepted input reuse only'}
$rules=[ordered]@{}
foreach($k in $old.rules.Keys){if($k -notin @('period_id','score_start','score_end_exclusive','strategy_design','fresh_flat_each_strategy_direction','no_saved_old_financial_accounts_replayed','signal_histories','conditional_unit_scenarios_are_sensitivity_not_HPO','original_547D_source_completed')){$rules[$k]=$old.rules[$k]}}
$rules.modes=@('LONG_ONLY');$rules.signal='CONSTANT_LONG_RAW_POINT3_EACH_ASSET_NO_ALPHA_FILTER'
$rules.strategy_id='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE';$rules.planned_selectors=12;$rules.planned_trading_account_simulations=12;$rules.planned_constant_cash_baselines=0
$rules.signal_and_risk_timeframe_minutes=1440;$rules.raw_targets=@(0.3,0.3);$rules.minimum_completed_available_daily_history=200
$rules.risk_histories='SAME30_COMPLETED_UTC_DAILY_RETURN_COVARIANCE';$rules.old_Spot_EWMA_reference_replicated=$false;$rules.original_SMA_alpha_hooks_used=$false
$rules.old_accounts_or_source_QA_replayed=$false;$rules.classification='THREE_INDEPENDENT_SEEN_DEVELOPMENT_WINDOWS';$rules.funding_unit_conditions_not_HPO=$true;$rules.original_547D_source_failure_preserved=$true;$rules.realized_risk_equalized=$false
if($Phase -eq 'Smoke'){
 $plan=[ordered]@{frozen_sources=$hashes;tests=@('tests/test_vol_managed_perpetual_target.py');calculation_rules=$rules;fee_profile='UNCHANGED_BYBIT_VIP0_PERPETUAL_TAKER_5P5BP_AND_BASE27_STRESS43_CONDITIONAL_FUNDS';created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_HOLD_TARGET_TEST_20261003_V1.json';WriteNew $dest $plan
}else{
 $smoke='reports/fast_research/PERPETUAL_HOLD_TARGET_SMOKE_20261003_V1.json';$v=ReadJson $smoke
 if($v.status -ne 'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' -or $v.test_exit_code -ne 0){throw 'New actual target test pass required'}
 foreach($p in @($smoke,'protocols/PERPETUAL_HOLD_TARGET_TEST_20261003_V1.json')){$hashes[$p]=Digest $p}
 $manifest='reports/fast_research/PERPETUAL_HOLD_INPUT_BINDING_20261003_V1.json';$sourcepath='reports/fast_research/PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json'
 $plan=[ordered]@{contract_id='D044_THREE_SEEN_USDM_PAST30_COVARIANCE_HOLD_REFERENCE_V1';rules=$rules;period_ids=@('213D','122D','90D');cost_scenarios=$old.cost_scenarios;unit_scenarios=$old.unit_scenarios;frozen_sources=$hashes;environment=$old.environment;
 input_manifest=@{path=$manifest;sha256=(Digest $manifest);required_status='BOUND_D044_THREE_PREVIOUSLY_ACCEPTED_USDM_WINDOWS_NOT_ECONOMICS'};
 trade_source_acceptance=@{path=$sourcepath;sha256=(Digest $sourcepath);required_status=$source.status};
 required_smoke_receipt=@{path=$smoke;sha256=(Digest $smoke);required_status=$v.status};
 run_dir='/home/xflops/coin-state/d044-perpetual-hold-research-20261003-v1';output_path='reports/fast_research/PERPETUAL_HOLD_RESEARCH_ACTUAL_20261003_V1.json';budgets=@{new_owned_bytes=1000000000;peak_RSS_bytes=3000000000;wall_seconds=3600};created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_HOLD_RESEARCH_20261003_V1.json';WriteNew $dest $plan
}
[pscustomobject]@{phase=$Phase;path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
