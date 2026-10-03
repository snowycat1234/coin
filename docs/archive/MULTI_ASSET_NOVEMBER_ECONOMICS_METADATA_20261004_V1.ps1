param([ValidateSet('Freeze','Bind')][string]$Operation,[ValidateSet('TWO_CONTROL','TEN_EQUAL','TEN_INVERSE')][string]$Recipe)
$ErrorActionPreference='Stop'
$root='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/')){throw 'STATE metadata only'};Join-Path $state $p.Substring(24)}
function WriteNew($p,$v){if(Test-Path -LiteralPath $p){throw 'Exclusive new metadata required'};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 50)+"`n",[Text.UTF8Encoding]::new($false))}
$prefix='MULTI_ASSET_NOVEMBER_'
$suffix='_20261004_V1.json'
$qaPath='reports/fast_research/MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_20261004_V2.json'
$qa=Read (Join-Path $root $qaPath)
$qaTask=Read (Join-Path $state ('task-progress/task-'+$qa.binding.task_id+'.json'))
if($qa.status -ne 'PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY' -or $qa.actual_exit_code -ne 0 -or $qaTask.status -ne 'completed' -or $qaTask.exit_code -ne 0){throw 'New November source QA must actually close0'}
$manifest='/home/xflops/coin-state/d054-multiasset-november-source-acceptance-20261004-v2/INPUT_MANIFEST.json'
$checker='fa274a6000622f6606bea953b995fb734d1892d55707b5b67ee1a7c3dce26e47'
if((Hash (Join-Path $root 'scripts/investment/multi_asset_financial_audit.py')) -ne $checker){throw 'Prospective independent source changed'}
if($Operation -eq 'Freeze'){
  $original=Read (Join-Path $root 'protocols/PUBLIC_SMA_POOL_OCTOBER_20261004_V1.json')
  $expected=$original.source_hashes
  $expected['scripts/investment/multi_asset_data.py']='663b6dd3b59711da32a44a71a771b7d8f3195f4b36a59d3761baa3e7f54db7d8'
  foreach($p in $expected.Keys){if((Hash (Join-Path $root $p)) -ne $expected[$p]){throw ('Active source changed: '+$p)}}
  foreach($r in @('TWO_CONTROL','TEN_EQUAL','TEN_INVERSE')){
    $inverse=$r -eq 'TEN_INVERSE'
    $spec=@{
      experiment_id='D054-NOVEMBER-'+$r+'-20261004';initial_capital_USDT=10000
      strategy=$(if($inverse){'COIN_PAST30_INVERSE_VOL_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'}else{'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'})
      allocation=$(if($inverse){'INVERSE_VOL_30D'}else{'EQUAL'});signal='CONSTANT_LONG_NOT_SMA_ALPHA'
      pools=$original.pools;start='2024-11-01T00:00:00+00:00';end_exclusive='2024-12-01T00:00:00+00:00';period_days=30
      data_manifest=@{path=$manifest;sha256=Hash (StatePath $manifest)};data_role='SEEN_DEVELOPMENT_COMMON_ACCEPTED_TEN_MANIFEST'
      data_role_note='BTCETH is a subset of the same accepted November10 input. Three fresh shared10k accounts, not summed/stiched; old Sep/Oct only saved references.'
      source_hashes=$expected;budget=@{owned_bytes=100000000;wall_seconds=1800;peak_RSS_bytes=3000000000}
      question='Fixed next full November month: pool effect TWO equal vsTEN equal and allocation effect TEN equal vsTEN inverse; same costs, caps and capital; actual risk reported'
      success_rule='12 new accounts and12 independent recorded-finance/target checks; truthful full calendar, marked inventory and cash-realization scopes; positive result not required'
      stopping_rule='Retain missing/insolvency/budget/ledger/exit failure; no cost/date/pool/risk/parameter or original5 exit-attempt change after results'
      warmup='Accepted Feb-Aug70 daily plus Sep10 and Oct10 trade1m, causally reduced full daily; no gaps or new warm download'
      selection_rule='Same frozen July liquidity/200 continuous warmup pool; no return reselection'
      pool_receipt=$original.pool_receipt;source_acceptance=@{path=$qaPath;sha256=Hash (Join-Path $root $qaPath);exit_code=0;task_id=$qa.binding.task_id}
      independent_reference_pre_market_sha256=$checker;models_fit=0;HPO=0;seen_development_only=$true
      limits='D40GB/shared5GB/swap0/GPU0/full10k/assetabs.3/gross.6/isolated1x; no keys/orders/locked'
      research_budget=@{new_actual_accounts=12;new_independent_accounts=12;new_recipes=0;models_fit=0;HPO=0;total_new_STATE_bytes=1000000000}
      created_utc=[DateTimeOffset]::UtcNow.ToString('o')
    }
    $p=Join-Path $root ('protocols/'+$prefix+$r+$suffix);WriteNew $p $spec
    [PSCustomObject]@{recipe=$r;protocol_sha256=Hash $p;manifest_sha256=$spec.data_manifest.sha256;source_pins=$expected.Count}
  }
}else{
  if(-not $Recipe){throw 'One recipe required'}
  $name=$prefix+$Recipe+$suffix
  $actual=Read (Join-Path $root ('reports/fast_research/'+$name))
  $id=$actual.binding.task_id;$taskPath=Join-Path $state ('task-progress/task-'+$id+'.json');$task=Read $taskPath
  if($task.status -ne 'completed' -or $task.exit_code -ne 0 -or $actual.completed_cases -ne 4 -or $actual.complete_calendar_cases -ne 4){throw 'New producer must actually finish before independent binding'}
  $old=Read (Join-Path $root 'docs/archive/PUBLIC_SMA_POOL_RELEASE_USED_METADATA_20261004_V1/OCTOBER_INDEPENDENT-ACTUAL_BINDING.json')
  $pins=$old.source_hashes;$pins['scripts/investment/multi_asset_financial_audit.py']=$checker
  foreach($p in $pins.Keys){if((Hash (Join-Path $root $p)) -ne $pins[$p]){throw ('Independent helper changed: '+$p)}}
  $spec=Read (Join-Path $root ('protocols/'+$name))
  $plan=@{
    ready_to_execute=$true;checker_sha256=$checker;source_hashes=$pins;source_archives=@{}
    protocol_path='protocols/'+$name;protocol_sha256=Hash (Join-Path $root ('protocols/'+$name))
    actual_report='reports/fast_research/'+$name;actual_report_sha256=Hash (Join-Path $root ('reports/fast_research/'+$name));actual_task_id=$id
    actual_closed_task=@{path='/home/xflops/coin-state/task-progress/task-'+$id+'.json';sha256=Hash $taskPath;task=$task}
    producer_run_binding_sha256=Hash (Join-Path (StatePath $actual.run_dir) 'RUN_BINDING.json')
    required_scope=@{start=$spec.start;end_exclusive=$spec.end_exclusive;start_us=1730419200000000;end_us=1733011200000000;period_days=30;score_month='2024-11';period_id='2024-11_30D';seen_development=$true}
    tolerances=@{cash_USDT=1e-7;ratio=1e-10};budgets=@{new_owned_bytes=5000000;wall_seconds=1200;peak_RSS_bytes=1000000000}
    allocation=$spec.allocation;strategy=$spec.strategy;old_QA_or_accounts_replayed=$false
    audit_scope='COMPLETE_MONTH_MARKED_NAV_WITH_ACTUAL_TERMINAL_INVENTORY_CASH_REALIZATION_SEPARATE'
    metadata_scope='New producer closed0, new prebound scope; actual checker derives financial reference before this new payload. No claimed new metadata compile.'
    investment_qualification_pass=$false;created_utc=[DateTimeOffset]::UtcNow.ToString('o')
  }
  $dir=Join-Path $state ('d054-november-'+$Recipe.ToLowerInvariant().Replace('_','-')+'-financial-20261004-v1')
  if(Test-Path -LiteralPath $dir){throw 'Exclusive new finance directory'};New-Item -ItemType Directory -Path $dir|Out-Null
  WriteNew (Join-Path $dir 'ACTUAL_BINDING.json') $plan
  [PSCustomObject]@{recipe=$Recipe;actual_task=$id;actual_sha256=$plan.actual_report_sha256;plan_sha256=Hash (Join-Path $dir 'ACTUAL_BINDING.json');checker_sha256=$checker}
}
