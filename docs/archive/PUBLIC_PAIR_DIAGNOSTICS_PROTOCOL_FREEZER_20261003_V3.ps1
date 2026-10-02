$ErrorActionPreference='Stop'
$root='D:\codex\coin'
function TaskHash([string]$n){(Get-FileHash -LiteralPath (Join-Path $root $n) -Algorithm SHA256).Hash.ToLowerInvariant()}
function J([string]$n){Get-Content -LiteralPath (Join-Path $root $n) -Raw | ConvertFrom-Json}
function X([string]$n,$v){$p=Join-Path $root $n;if(Test-Path -LiteralPath $p){throw "Exclusive output exists: $n"};[IO.File]::WriteAllText($p,(($v|ConvertTo-Json -Depth 40)+"`n"),[Text.UTF8Encoding]::new($false))}
$source='scripts/investment/public_pair_diagnostics_v2.py'
$archive='docs/archive/PUBLIC_PAIR_DIAGNOSTICS_PROTOCOL_FREEZER_20261003_V3.ps1'
if ((TaskHash $archive) -ne (TaskHash '.cache/d036_public_pair_protocol_freezer_20261003_v3.ps1')) {throw 'Freezer archive bytes differ'}
$prior=J 'docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_PRIOR_BINDINGS_20261003_V1.json'
$fixed=[ordered]@{}
foreach($n in @($source,$archive,'scripts/investment/public_pair_diagnostics.py','protocols/PUBLIC_PAIR_COMPLEMENTARITY_20261003_V1.json','docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_PRIOR_BINDINGS_20261003_V1.json','docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_ARTIFACT_RECON_20261003_V1.md','docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_METHOD_REVIEW_20261003_V1.md','scripts/research_v8/registry.py','scripts/research_v7/oracle_flow_ceiling.py','src/quant/resources.py','src/quant/disk.py','src/quant/paths.py','environments/v8/uv.lock','protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json','state/dataset_lock.json')){$fixed[$n]=TaskHash $n}
foreach($group in @('producers','independents','roots','protocols_by_producer')){foreach($property in $prior.$group.PSObject.Properties){$entry=$property.Value;if((TaskHash $entry.path) -ne $entry.sha256){throw "Prior binding changed: $($entry.path)"};$v=J $entry.path;if($entry.required_status -and $v.status -ne $entry.required_status){throw "Unexpected prior status: $($entry.path)"};$fixed[$entry.path]=$entry.sha256}}
$strategies=@{P='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER';H='COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'}
$cases=@(
 [ordered]@{id='CONT547';start='2024-01-01';end_exclusive='2025-07-01';days=547;minutes=787680;P='PUBLIC_LONG_547D_ACTUAL_20261003_V1';H='PUBLIC_LONG_547D_ACTUAL_20261003_V1'},
 [ordered]@{id='CONT122';start='2025-08-01';end_exclusive='2025-12-01';days=122;minutes=175680;P='BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2';H='PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1'},
 [ordered]@{id='CONT90';start='2025-12-01';end_exclusive='2026-03-01';days=90;minutes=129600;P='BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2';H='PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1'}
)
$periods=@();$inputBytes=0
foreach($case in $cases){
 $legs=[ordered]@{}
 foreach($leg in @('P','H')){
  $path='reports/fast_research/'+$case[$leg]+'.json';$r=J $path
  if($fixed[$path] -ne (TaskHash $path)){throw 'Producer missing from prior frozen bindings'}
  $f=@($r.folds|Where-Object {$_.fold -eq $case.id})
  if($f.Count -ne 1 -or $f[0].days -ne $case.days){throw 'Exact whole-window producer'}
  $row=@($f[0].results|Where-Object {$_.strategy -eq $strategies[$leg] -and $_.spread_bps -eq 8})
  if($row.Count -ne 1 -or $row[0].nominal_roundtrip_bps -ne 36 -or $row[0].summary.initial_nav -ne 10000){throw 'One native-fee conservative case'}
  $summary=$row[0].summary
  if($summary.fee_settlement_version -ne 'BYBIT_SPOT_RECEIVED_ASSET_V1' -or $summary.bybit_fee_profile_sha256 -ne $fixed['protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json'] -or $summary.derived_AST_SHA256 -ne '39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73'){throw 'Fixed native Spot settlement identity'}
  $artifacts=[ordered]@{}
  foreach($name in @('daily_nav.parquet','minute_nav_inventory.parquet')){
   $a=$row[0].artifacts.$name
   $artifacts[$name]=[ordered]@{path=$row[0].directory+'/'+$name;sha256=$a.sha256;bytes=$a.bytes;rows=$(if($name -eq 'daily_nav.parquet'){$case.days}else{$case.minutes})}
   $inputBytes += $a.bytes
  }
  $legs[$leg]=[ordered]@{strategy=$strategies[$leg];producer_path=$path;producer_sha256=$fixed[$path];artifacts=$artifacts}
 }
 $periods += [ordered]@{id=$case.id;start=$case.start;end_exclusive=$case.end_exclusive;days=$case.days;minutes=$case.minutes;initial_nav=10000;legs=$legs}
}
$fee='protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json';$env='environments/v8/uv.lock'
$spec=[ordered]@{
 classification='SCREENING_SAVED_LEDGER_COMPLEMENTARITY_NOT_ENSEMBLE'
 created_utc=[DateTime]::UtcNow.ToString('o')
 original_head=(git -C $root rev-parse HEAD).Trim()
 research_question='Do two fixed public strategies with common 2h entry but different exits have genuinely complementary net losses and marked exposure in three seen independent periods?'
 frozen_sources=$fixed
 periods=$periods
 fee_profile=[ordered]@{path=$fee;sha256=$fixed[$fee];market_type='SPOT';fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1';fee_bps_per_side=10;half_spread_bps_per_side=4;slippage_bps_per_side=4;nominal_roundtrip_bps=36;data_venue='Binance';fee_reference_venue='Bybit';native_market_certified=$false}
 environment=[ordered]@{sys_prefix='/home/xflops/coin-state/v8-clean-env-20261002-v2';lock_path=$env;lock_sha256=$fixed[$env];ram_limit_bytes=5000000000;swap_bytes=0;GPU=0}
 budgets=[ordered]@{new_owned_bytes=5000000;module_combined_STATE_bytes=5000000;peak_RSS_bytes=1000000000;wall_seconds=300;additional_market_copy_bytes=0;input_bytes=$inputBytes;input_files=12}
 calculation_rules=[ordered]@{cash_tolerance=0.0000001;ratio_tolerance=0.000000000001;tail_fraction=0.10;tail_count='ceil(.10*N), signed net USDT delta ascending, stable UTC-date tie break';tail_overlap='intersection count / k, not Jaccard; fewer than k real negative days => UNKNOWN, never PASS';tail_offset='other-leg signed net USDT delta sum on fixed own-tail dates; >=0 at unmodified point, disclose rounding-sensitive within cash tolerance; cash protection not profitable hedge';daily='NAV delta from previous daily NAV, first previous=10000; net return=delta/previous; daily date maps to following UTC00:00 exclusive close';exposure='each window sum(min(wP,wH))/sum(max(wP,wH)) across minutes and symbols; w=actual marked_notional/NAV; both zero add nothing; denominator0 =>UNKNOWN; strict positive dust counted and disclosed';undefined='Zero variance correlation or empty denominator is UNKNOWN and never PASS; no NaN-to-zero substitutions';cost='saved accepted fill-time fee and execution costs, same received quantities; not rerun counterfactual';no_ensemble_NAV=$true;periods_independent=$true}
 decision_rule=[ordered]@{
  purpose='Only decide whether a new fixed50/50 target shared10k account is worth one causal true-cost replay; not investment adoption or significance'
  next_unique_combination='fixed50/50 P/TaskHash target weights before common risk engine; never average historical NAV or allocate to winner months'
  criteria='ALL'
  later_period_daily_PnL_Pearson_max_exclusive=0.80
  later_period_worst10pct_tail_overlap_max_exclusive=0.70
  offset_condition='In at least two periods, including at least one later period, one leg has other_leg_tail_net_PnL>=0 on its own worst10pct days'
  every_period_weighted_min_max_exposure_overlap_max_exclusive=0.80
  failure_action='PAUSE_THIS_SAME_ENTRY_PAIR_COMBINATION_PRESERVE_PUBLIC_STRATEGIES'
  reopen='Different causal entry information or truly later comparable-cost risk evidence of net-loss diversification; no retrospective threshold relaxation'
  candidate_status='NO_QUALIFIED_CANDIDATE'
 }
 run_dir='/home/xflops/coin-state/d036-public-pair-diagnostics-20261003-v2'
 output_path='reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ACTUAL_20261003_V2.json'
 expected_scientific_runs=1
 models_fit=0
 orders_sent=0
 locked_consumed=$false
 unseen_qualification=$false
 native_market_certified=$false
 accounts_stitched=$false
 historical_source_task_metadata='Use original exact producer/audit facts, no retrofit unknown source task IDs'
}
X 'protocols/PUBLIC_PAIR_COMPLEMENTARITY_20261003_V2.json' $spec
[pscustomobject]@{protocol='protocols/PUBLIC_PAIR_COMPLEMENTARITY_20261003_V2.json';sha256=TaskHash 'protocols/PUBLIC_PAIR_COMPLEMENTARITY_20261003_V2.json';source_sha256=TaskHash $source;input_files=12;input_bytes=$inputBytes;array_files_read=$false}|ConvertTo-Json -Compress
