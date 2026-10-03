$ErrorActionPreference='Stop'
$root='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
function Hash($p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
function Read($p) { Get-Content -LiteralPath $p -Raw | ConvertFrom-Json -AsHashtable -DateKind String }
function WriteNew($p,$v) {
  if(Test-Path -LiteralPath $p){throw "Exclusive new artifact already exists: $p"}
  [IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 70)+"`n",[Text.UTF8Encoding]::new($false))
}
$testRel='reports/fast_research/INVERSE_VOL_PORTFOLIO_TARGET_SYNTHETIC_20261004_V2.json'
$test=Read (Join-Path $root $testRel)
$task=Read (Join-Path $state ('task-progress/task-'+$test.binding.task_id+'.json'))
if($task.status -ne 'completed' -or $task.exit_code -ne 0 -or $test.test_exit_code -ne 0 -or $test.status -ne 'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'){throw 'New synthetic target case must truly pass first'}
$baseline=@{
  SEPTEMBER='MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json'
  OCTOBER='MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json'
}
foreach($month in @('SEPTEMBER','OCTOBER')) {
  $p=Read (Join-Path $root ('protocols/'+$baseline[$month]))
  $p.experiment_id='D052-INVERSE-VOL-'+$month+'-20261004'
  $p.strategy='COIN_PAST30_INVERSE_VOL_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
  $p.allocation='INVERSE_VOL_30D'
  $p.budget=@{owned_bytes=100000000;wall_seconds=1800;peak_RSS_bytes=3000000000}
  foreach($name in @($p.source_hashes.Keys)){$p.source_hashes[$name]=Hash (Join-Path $root $name)}
  foreach($name in @('prior_failure','precedent','prior_new_entry_validation','warmup','period_days','selection_rule','fits')){
    $p.Remove($name) | Out-Null
  }
  $p.question='One allocation factor: same fixed July pool, past30 inverse sample volatility vs saved equal; full capital, costs, signed covariance and execution unchanged'
  $p.success_rule='Eight new accounts across two separate months; correct causal targets, shared-wallet evidence and saved allocation contrasts; no requirement of positive return'
  $p.stopping_rule='Preserve missing/insolvency/budget/ledger failures; calendar marked NAV is distinct from cash-realized return; original five exit attempts unchanged'
  $p.models_fit=0
  $p.data_role_note='Only LIQUIDITY_TEN actually executed; original two-asset and equal accounts reused from saved evidence, no new data or old QA replay'
  $p.baseline=@{path='reports/fast_research/'+$baseline[$month];sha256=Hash (Join-Path $root ('reports/fast_research/'+$baseline[$month]));replayed=$false}
  $p.target_validation=@{path=$testRel;sha256=Hash (Join-Path $root $testRel);task_id=$test.binding.task_id;actual_exit_code=0}
  $p.research_budget=@{total_new_STATE_bytes=300000000;actual_account_calls=8;new_recipes=1;models_fit=0;HPO=0;GPU=0;shared_RAM_hard_bytes=4999999488}
  $p.data_role='SEEN_DEVELOPMENT_SAME_ACCEPTED_INPUT'
  $out=Join-Path $root ('protocols/MULTI_ASSET_INVERSE_VOL_'+$month+'_20261004_V1.json')
  WriteNew $out $p
  [PSCustomObject]@{month=$month;protocol_sha256=Hash $out;manifest=$p.data_manifest.sha256;target_case_task=$test.binding.task_id}
}
