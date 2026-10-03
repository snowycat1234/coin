param([ValidateSet('SEPTEMBER','OCTOBER')][string]$Month)
$ErrorActionPreference='Stop'
$root='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/')){throw 'Owned metadata only'};Join-Path $state $p.Substring(24)}
$name='PUBLIC_SMA_POOL_'+$Month+'_20261004_V1.json'
$actual=Read (Join-Path $root ('reports/fast_research/'+$name))
$id=$actual.binding.task_id
$taskpath=Join-Path $state ('task-progress/task-'+$id+'.json')
$task=Read $taskpath
if($task.status -ne 'completed' -or $task.exit_code -ne 0 -or $actual.completed_cases -ne 4 -or $actual.complete_calendar_cases -ne 4){throw 'New producer must really finish before audit binding'}
$plan=Read (Join-Path $root ('docs/archive/MULTI_ASSET_INVERSE_VOL_'+$Month+'_INDEPENDENT_USED_METADATA_20261004_V1/ACTUAL_BINDING.json'))
$plan.Remove('metadata_freezer_task_id')
$plan.Remove('inverse_is_not_ERC')
$plan.source_hashes.Remove('docs/archive/MULTI_ASSET_INVERSE_VOL_AUDIT_BINDER_20261004_V1.py')
$plan.checker_sha256=Hash (Join-Path $root 'scripts/investment/multi_asset_financial_audit.py')
if($plan.checker_sha256 -ne '82f461e8956eb8ebd797c2f7e824b1f6d22dba74f74b2ab1fd716c8d1cedf7c4'){throw 'Pre-market independent reference changed'}
$plan.source_hashes['scripts/investment/multi_asset_financial_audit.py']=$plan.checker_sha256
foreach($path in $plan.source_hashes.Keys){if((Hash (Join-Path $root $path)) -ne $plan.source_hashes[$path]){throw ('Accepted helper changed: '+$path)}}
$plan.protocol_path='protocols/'+$name
$plan.protocol_sha256=Hash (Join-Path $root $plan.protocol_path)
$plan.actual_report='reports/fast_research/'+$name
$plan.actual_report_sha256=Hash (Join-Path $root $plan.actual_report)
$plan.actual_task_id=$id
$plan.actual_closed_task=@{path='/home/xflops/coin-state/task-progress/task-'+$id+'.json';sha256=Hash $taskpath;task=$task}
$plan.producer_run_binding_sha256=Hash (Join-Path (StatePath $actual.run_dir) 'RUN_BINDING.json')
$plan.allocation='EQUAL'
$plan.strategy='COIN_JESSE_SMA50_200_1D_USDM_CONFIGURED_POOL_ADAPTER'
$plan.reused_financial_span_metadata=$plan.complete_financial_span_compiled_before_arrays
$plan.Remove('complete_financial_span_compiled_before_arrays')
$plan.metadata_scope='Accepted same-month calendar and unchanged financial span metadata reused; new checker calls prepare_financial before new payload and reports its actual derivation. Independent scalar SMA reference is new and pre-market pinned.'
$plan.created_utc=[DateTimeOffset]::UtcNow.ToString('o')
$dir=Join-Path $state ('d053-public-sma-pool-'+$Month.ToLowerInvariant()+'-financial-20261004-v1')
if(Test-Path -LiteralPath $dir){throw 'Exclusive new audit directory required'}
New-Item -ItemType Directory -Path $dir|Out-Null
[IO.File]::WriteAllText((Join-Path $dir 'ACTUAL_BINDING.json'),($plan|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))
[PSCustomObject]@{month=$Month;actual_task=$id;actual_sha256=$plan.actual_report_sha256;plan_sha256=Hash (Join-Path $dir 'ACTUAL_BINDING.json');checker_sha256=$plan.checker_sha256;new_arrays_read=$false}
