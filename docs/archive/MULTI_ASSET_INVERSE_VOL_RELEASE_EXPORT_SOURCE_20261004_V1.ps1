$ErrorActionPreference='Stop'
$root='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$release='docs/archive/MULTI_ASSET_INVERSE_VOL_RELEASE_USED_METADATA_20261004_V1'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/')){throw 'Only owned STATE metadata'};Join-Path $state $p.Substring(24)}
function CopySmall($source,$relative){
  if((Get-Item -LiteralPath $source).Length -gt 2000000){throw 'Small metadata only'}
  $dest=Join-Path $root $relative
  if(Test-Path -LiteralPath $dest){if((Hash $source) -ne (Hash $dest)){throw 'Original copy differs'}}
  else{Copy-Item -LiteralPath $source -Destination $dest}
}
function GitHash($relative){
  $start=[Diagnostics.ProcessStartInfo]::new('git')
  $start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
  $start.ArgumentList.Add('cat-file');$start.ArgumentList.Add('blob');$start.ArgumentList.Add('HEAD:'+$relative)
  $proc=[Diagnostics.Process]::Start($start);$stream=[IO.MemoryStream]::new()
  $proc.StandardOutput.BaseStream.CopyTo($stream);$errorText=$proc.StandardError.ReadToEnd();$proc.WaitForExit()
  if($proc.ExitCode -ne 0){throw $errorText}
  [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream.ToArray())).ToLowerInvariant()
}
if((git -C $root rev-parse HEAD) -ne 'abc901fcaa785d26172a0065915af7f64d312216'){throw 'Recheck changed HEAD before module acceptance'}
$receiptRelative='reports/GITHUB_MULTI_ASSET_INVERSE_VOL_SOURCE_BINDING_20261004_V1.json'
if(Test-Path (Join-Path $root $receiptRelative)){throw 'Exclusive module binding'}
New-Item -ItemType Directory -Path (Join-Path $root $release) -ErrorAction Stop | Out-Null
$roles=@{
  SYNTHETIC='reports/fast_research/INVERSE_VOL_PORTFOLIO_TARGET_SYNTHETIC_20261004_V2.json'
  SEPTEMBER_MARKET='reports/fast_research/MULTI_ASSET_INVERSE_VOL_SEPTEMBER_20261004_V1.json'
  OCTOBER_MARKET='reports/fast_research/MULTI_ASSET_INVERSE_VOL_OCTOBER_20261004_V1.json'
  SEPTEMBER_COMPARISON='reports/fast_research/MULTI_ASSET_INVERSE_VOL_SEPTEMBER_COMPARISON_20261004_V1.json'
  OCTOBER_COMPARISON='reports/fast_research/MULTI_ASSET_INVERSE_VOL_OCTOBER_COMPARISON_20261004_V1.json'
}
$closed=@{}
foreach($role in $roles.Keys){
  $r=Read (Join-Path $root $roles[$role]);$id=if($r.binding){$r.binding.task_id}else{$r.task_id}
  $taskpath=Join-Path $state ('task-progress/task-'+$id+'.json');$task=Read $taskpath
  if($task.status -ne 'completed' -or $task.exit_code -ne 0){throw "Real closed0 needed: $role"}
  CopySmall $taskpath ($release+'/'+$role+'-TASK.json')
  if($r.run_dir){CopySmall (Join-Path (StatePath $r.run_dir) 'RUN_BINDING.json') ($release+'/'+$role+'-RUN_BINDING.json')}
  $closed[$role]=@{task_id=$id;actual_exit_code=0;report=$roles[$role];report_sha256=Hash (Join-Path $root $roles[$role]);task_archive=$release+'/'+$role+'-TASK.json';task_sha256=Hash $taskpath}
}
$synthetic=Read (Join-Path $root $roles.SYNTHETIC)
CopySmall (Join-Path (StatePath $synthetic.run_dir) 'junit.xml') ($release+'/SYNTHETIC-JUNIT.xml')
$failed=Read (Join-Path $root 'reports/fast_research/INVERSE_VOL_PORTFOLIO_TARGET_SYNTHETIC_20261004_V1.json')
$failedtask=Read (Join-Path $state ('task-progress/task-'+$failed.binding.task_id+'.json'))
if($failedtask.status -ne 'failed' -or $failedtask.exit_code -ne 1 -or $failed.test_exit_code -ne 2){throw 'Original collection failure must remain failed'}
CopySmall (Join-Path (StatePath $failed.run_dir) 'RUN_BINDING.json') ($release+'/FAILED-SYNTHETIC-RUN_BINDING.json')
CopySmall (Join-Path (StatePath $failed.run_dir) 'junit.xml') ($release+'/FAILED-SYNTHETIC-JUNIT.xml')
foreach($month in @('SEPTEMBER','OCTOBER')){
  $name='reports/fast_research/MULTI_ASSET_INVERSE_VOL_'+$month+'_INDEPENDENT_20261004_V1.json'
  $r=Read (Join-Path $root $name);$task=Read (Join-Path $state ('task-progress/task-'+$r.binding.task_id+'.json'))
  if($task.status -ne 'completed' -or $task.exit_code -ne 0 -or $r.completed_cases_verified -ne 4 -or $r.completed_full_calendar_cases_verified -ne 4 -or $r.maximum_errors.cash -gt 1e-7 -or $r.maximum_errors.ratio -gt 1e-10){throw 'Original tolerance independent evidence required'}
  $closed[$month+'_INDEPENDENT']=@{task_id=$r.binding.task_id;actual_exit_code=0;report=$name;report_sha256=Hash (Join-Path $root $name);case_calls=$r.financial_case_calls;maximum_errors=$r.maximum_errors}
}
CopySmall (Join-Path $root '.cache/d052_freeze_inverse_vol.ps1') 'docs/archive/MULTI_ASSET_INVERSE_VOL_PROTOCOL_METADATA_FREEZER_20261004_V1.ps1'
CopySmall $PSCommandPath 'docs/archive/MULTI_ASSET_INVERSE_VOL_RELEASE_EXPORT_SOURCE_20261004_V1.ps1'
$tracked=@('README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl','scripts/investment/public_sma_perpetual.py','scripts/investment/vol_managed_perpetual_target.py','scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','scripts/investment/compare_multi_asset_portfolios.py')
$new=@(git -C $root ls-files --others --exclude-standard)|Where-Object {$_ -match '^(docs/archive|protocols|reports/fast_research)/(INVERSE_VOL_PORTFOLIO|MULTI_ASSET_INVERSE_VOL)' -or $_ -eq 'tests/test_inverse_vol_portfolio_target.py' -or $_ -eq 'reports/GITHUB_MULTI_ASSET_OCTOBER_SYNC_VERIFIED_20261004_V1.json'}
$selected=@($tracked+$new|Sort-Object -Unique)
$current=@{}
foreach($relative in $selected){$current[$relative]=Hash (Join-Path $root $relative)}
$prior=@('AGENTS.md','src/quant/perpetual_account.py','scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py','scripts/investment/multi_asset_data.py','src/quant/resources.py','src/quant/execution_contract.py','scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py','environments/v8/uv.lock','docs/archive/APPEND_ONLY_REGISTRY_GIT_PREFLIGHT_SOURCE_20261003_V2.py','reports/fast_research/MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json','reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json','reports/fast_research/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json','protocols/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json','protocols/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json')
$verified=@{}
foreach($relative in $prior){$digest=Hash (Join-Path $root $relative);if($digest -ne (GitHash $relative)){throw ('Previously accepted bytes changed: '+$relative)};$verified[$relative]=$digest}
$private=Hash (Join-Path $root 'state/dataset_lock.json')
if($private -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private lock hash guard changed'}
$v=@{status='CURRENT_MODULE_EXISTING_ACCEPTANCE_METADATA_BINDING_NOT_ADDITIONAL_MARKET_REPLAY';parent_commit='abc901fcaa785d26172a0065915af7f64d312216';source_hashes=$current;verified_prior_files=$verified;local_non_git_source_hashes=@{'state/dataset_lock.json'=$private};closed_actual_roles=$closed;selected_module_paths=$selected;historical_source_reproduction='Old normal source bytes at accepted Git abc901f/b00183d; no changed active source required to equal superseded old hashes';original_failed_collection=@{task_id=$failed.binding.task_id;actual_exit_code=1;financial_calls=0;market_arrays=0};independent_cases=8;new_account_cases=8;models_fit=0;old_QA_or_accounts_replayed=$false;investment='CASH';candidate='NONE';APR='NOT_EVALUABLE';created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
[IO.File]::WriteAllText((Join-Path $root $receiptRelative),($v|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))
git -C $root add -- @selected $receiptRelative
if($LASTEXITCODE -ne 0){throw 'Module exact-path stage failed'}
[PSCustomObject]@{receipt=$receiptRelative;sha256=Hash (Join-Path $root $receiptRelative);selected_paths=$selected.Count;closed_roles=$closed.Count;private_lock_body_read=$false;new_account_calls=8;new_independent_calls=8}
