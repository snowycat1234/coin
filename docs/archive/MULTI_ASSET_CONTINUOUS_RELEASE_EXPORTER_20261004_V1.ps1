$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='90c60204ad9fcd86a3e90c8d318bda8cad7eb0c1'
$release='docs/archive/MULTI_ASSET_CONTINUOUS_RELEASE_METADATA_20261004_V1'
$receipt='reports/GITHUB_MULTI_ASSET_CONTINUOUS_SOURCE_BINDING_20261004_V1.json'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/')){throw 'Only owned STATE metadata'};Join-Path $state $p.Substring(24)}
function CopySmall($src,$rel){if((Get-Item -LiteralPath $src).Length -gt 2000000){throw 'Small metadata only'};$dst=Join-Path $root $rel;if(Test-Path -LiteralPath $dst){if((Hash $src) -ne (Hash $dst)){throw 'Existing bytes differ'}}else{Copy-Item -LiteralPath $src -Destination $dst}}
function GitHash($rel){
 $start=[Diagnostics.ProcessStartInfo]::new('git');$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
 $start.ArgumentList.Add('cat-file');$start.ArgumentList.Add('blob');$start.ArgumentList.Add('HEAD:'+$rel)
 $proc=[Diagnostics.Process]::Start($start);$bytes=[IO.MemoryStream]::new();$proc.StandardOutput.BaseStream.CopyTo($bytes);$err=$proc.StandardError.ReadToEnd();$proc.WaitForExit();if($proc.ExitCode -ne 0){throw $err};[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes.ToArray())).ToLowerInvariant()
}
if((git -C $root rev-parse HEAD) -ne $parent -or (Test-Path (Join-Path $root $receipt))){throw 'Exact parent and exclusive binding required'}
New-Item -ItemType Directory -Path (Join-Path $root $release)|Out-Null
$roles=@{
 INPUT='MULTI_ASSET_CONTINUOUS_91D_INPUT_BINDING_20261004_V1'
 TWO_MARKET='MULTI_ASSET_CONTINUOUS_91D_TWO_CONTROL_20261004_V1';EQUAL_MARKET='MULTI_ASSET_CONTINUOUS_91D_TEN_EQUAL_20261004_V1';INVERSE_MARKET='MULTI_ASSET_CONTINUOUS_91D_TEN_INVERSE_20261004_V1'
 TWO_INDEPENDENT='MULTI_ASSET_CONTINUOUS_91D_TWO_CONTROL_INDEPENDENT_20261004_V2';EQUAL_INDEPENDENT='MULTI_ASSET_CONTINUOUS_91D_TEN_EQUAL_INDEPENDENT_20261004_V2';INVERSE_INDEPENDENT='MULTI_ASSET_CONTINUOUS_91D_TEN_INVERSE_INDEPENDENT_20261004_V2'
 POOL_COMPARISON='MULTI_ASSET_CONTINUOUS_91D_POOL_COMPARISON_20261004_V1';ALLOCATION_COMPARISON='MULTI_ASSET_CONTINUOUS_91D_ALLOCATION_COMPARISON_20261004_V1'
 ENGINE_BOUNDARY='MULTI_ASSET_CONTINUOUS_BOUNDARY_TEST_20261004_V2'
}
$closed=@{};$maxCash=0.;$maxRatio=0.;$mainBytes=0L
foreach($role in $roles.Keys){
 $rel='reports/fast_research/'+$roles[$role]+'.json';$r=Read (Join-Path $root $rel);$id=if($r.binding){$r.binding.task_id}else{$r.task_id}
 $tp=Join-Path $state ('task-progress/task-'+$id+'.json');$t=Read $tp
 if($t.status -ne 'completed' -or $t.exit_code -ne 0){throw ('Actual closed0 required '+$role)}
 if($role -like '*MARKET'){
  if($r.completed_cases -ne 4 -or $r.complete_calendar_cases -ne 4 -or $r.actual_calendar_days -ne 91 -or $r.account_path -ne 'CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D' -or $r.terminal_cash_realized_cases -ne 4){throw 'Four complete continuous calendars and cash realization required'}
  $mainBytes += $r.owned_bytes
 }
 if($role -like '*INDEPENDENT'){
  if($r.completed_cases_verified -ne 4 -or $r.completed_full_calendar_cases_verified -ne 4 -or $r.financial_case_calls -ne 4 -or $r.maximum_errors.cash -gt 1e-7 -or $r.maximum_errors.ratio -gt 1e-10){throw 'Independent calendars and original tolerances required'}
  $maxCash=[Math]::Max($maxCash,$r.maximum_errors.cash);$maxRatio=[Math]::Max($maxRatio,$r.maximum_errors.ratio)
 }
 CopySmall $tp ($release+'/'+$role+'-TASK.json')
 $proof=@{task_id=$id;actual_exit_code=0;report=$rel;report_sha256=Hash (Join-Path $root $rel);task_archive=$release+'/'+$role+'-TASK.json';task_sha256=Hash $tp}
 if($r.run_dir){$rd=StatePath $r.run_dir;foreach($name in 'RUN_BINDING.json','ACTUAL_BINDING.json'){if(Test-Path -LiteralPath (Join-Path $rd $name)){CopySmall (Join-Path $rd $name) ($release+'/'+$role+'-'+$name)}}}
 if($role -like '*INDEPENDENT'){$proof.maximum_errors=$r.maximum_errors;$proof.financial_calls=$r.financial_case_calls}
 $closed[$role]=$proof
}
foreach($role in @{
 FINANCIAL_BOUNDARY=@{id='e77bcafccd7742cb98e24568b98fe869';exit=0}
 LOADER_STATIC_ONLY=@{id='98b02dba2bbc43eba620e2e9fa7d6a6f';exit=0}
 ENGINE_STARTUP_FAILURE=@{id='de16ed27f72f4ddebb4f593c759a24f3';exit=1}
 FINANCIAL_INPUT_FAILURE=@{id='1891299fbf8b45bdb0a6eb8efc9ab4f2';exit=1}
}.GetEnumerator()){
 $tp=Join-Path $state ('task-progress/task-'+$role.Value.id+'.json');$t=Read $tp
 if($t.exit_code -ne $role.Value.exit -or $t.status -notin @('completed','failed')){throw ('Actual task closure required '+$role.Key)}
 CopySmall $tp ($release+'/'+$role.Key+'-TASK.json');$closed[$role.Key]=@{task_id=$role.Value.id;actual_exit_code=$role.Value.exit;task_archive=$release+'/'+$role.Key+'-TASK.json';task_sha256=Hash $tp}
}
CopySmall (Join-Path $state 'd055-continuous-input-binding-20261004-v1/INPUT_MANIFEST.json') ($release+'/ACCEPTED-CONTINUOUS-INPUT_MANIFEST.json')
CopySmall (Join-Path $state 'd055-continuous-loader-static-20261004-v1/AST_COMPILE_ONLY.json') ($release+'/AST-COMPILE-ONLY.json')
CopySmall (Join-Path $state 'd055-continuous-two-control-financial-20261004-v1/ACTUAL_BINDING.json') ($release+'/FAILED-FINANCIAL-ACTUAL_BINDING.json')
CopySmall (Join-Path $state 'd055-continuous-two-control-financial-20261004-v1/RUN_BINDING.json') ($release+'/FAILED-FINANCIAL-RUN_BINDING.json')
CopySmall $PSCommandPath 'docs/archive/MULTI_ASSET_CONTINUOUS_RELEASE_EXPORTER_20261004_V1.ps1'
$manifest=Read (Join-Path $root ($release+'/ACCEPTED-CONTINUOUS-INPUT_MANIFEST.json'))
if((Hash (Join-Path $root ($release+'/ACCEPTED-CONTINUOUS-INPUT_MANIFEST.json'))) -ne '847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50'){throw 'Accepted composite bytes required'}
foreach($ref in $manifest.monthly_manifests){if((Hash (StatePath $ref.path)) -ne $ref.sha256){throw 'Prior accepted monthly metadata changed'}}
$tracked=@('README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl','scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','scripts/investment/compare_multi_asset_portfolios.py')
$new=@(git -C $root ls-files --others --exclude-standard)|Where-Object {$_ -match '^(docs/archive|protocols|reports/fast_research|reports)/MULTI_ASSET_CONTINUOUS' -or $_ -in @('tests/test_multi_asset_continuity.py','tests/test_multi_asset_continuous_20261004.py','reports/GITHUB_MULTI_ASSET_NOVEMBER_SYNC_VERIFIED_20261004_V1.json')}
$selected=@($tracked+$new|Sort-Object -Unique);$current=@{};foreach($rel in $selected){$current[$rel]=Hash (Join-Path $root $rel)}
$prior=@('AGENTS.md','scripts/investment/vol_managed_perpetual_target.py','scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_pool_target.py','scripts/investment/public_sma_daily.py','third_party/jesse_example_smacrossover/smacrossover_original.py','third_party/jesse_example_smacrossover/LICENSE','src/quant/perpetual_account.py','scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py','src/quant/resources.py','src/quant/execution_contract.py','scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py','tools/task_progress/task_progress_sample.py','environments/v8/uv.lock','docs/archive/APPEND_ONLY_REGISTRY_GIT_PREFLIGHT_SOURCE_20261003_V2.py','reports/fast_research/MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json','reports/fast_research/MULTI_ASSET_SOURCE_ACCEPTANCE_20261004_V2.json','reports/fast_research/MULTI_ASSET_OCTOBER_SOURCE_ACCEPTANCE_20261004_V1.json','reports/fast_research/MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_20261004_V2.json','reports/GITHUB_MULTI_ASSET_NOVEMBER_SOURCE_BINDING_20261004_V1.json','reports/GITHUB_MULTI_ASSET_NOVEMBER_STAGED_GATE_20261004_V1.json')
$prior += @(git -C $root ls-files 'reports/fast_research/MULTI_ASSET_NOVEMBER_*' 'protocols/MULTI_ASSET_NOVEMBER_*')
$verified=@{};foreach($rel in ($prior|Sort-Object -Unique)){$d=Hash (Join-Path $root $rel);if($d -ne (GitHash $rel)){throw ('Prior evidence/helper changed '+$rel)};$verified[$rel]=$d}
$private=Hash (Join-Path $root 'state/dataset_lock.json');if($private -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private SHA guard'}
$ownedDirs=@(Get-ChildItem -LiteralPath $state -Directory|Where-Object {$_.Name -like 'd055-*'})
$owned=0L;foreach($dir in $ownedDirs){foreach($file in (Get-ChildItem -LiteralPath $dir.FullName -File -Recurse)){$owned += $file.Length}}
if($owned -gt 1000000000){throw 'D055 total new STATE budget exceeded'}
$v=@{status='CURRENT_MODULE_EXISTING_ACTUAL_ACCEPTANCE_BINDING_NOT_NEW_MARKET_REPLAY';parent_commit=$parent;source_hashes=$current;verified_prior_files=$verified;local_non_git_source_hashes=@{'state/dataset_lock.json'=$private};closed_actual_roles=$closed;selected_module_paths=$selected;new_account_cases=12;independent_cases=12;actual_calendar_days=91;maximum_cash_error_USDT=$maxCash;maximum_ratio_error=$maxRatio;main_output_bytes=$mainBytes;owned_STATE_bytes=$owned;owned_STATE_dirs=@($ownedDirs.Name);new_downloads=0;new_source_QA=0;models_fit=0;old_QA_or_accounts_replayed=$false;original_premarket_financial_source='21097539b1a2ca2c70a9fdc4223c3bcb1a4ed26b4e8cb7baff05708f47d10076';corrected_financial_source='db1332b4a6284aeb6d1caacf2191127b8900eedc340b2d9431e17223c0411339';financial_change='One metadata pool-candidate filter; core financial/target bodies and tolerances unchanged; failed source/report/plan/task retained';investment='CASH';candidate='NONE';APR='NOT_EVALUABLE';created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
[IO.File]::WriteAllText((Join-Path $root $receipt),($v|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))
git -C $root add -- @selected $receipt
if($LASTEXITCODE -ne 0){throw 'Exact module staging failed'}
[PSCustomObject]@{receipt=$receipt;sha256=Hash (Join-Path $root $receipt);selected_paths=$selected.Count;closed_roles=$closed.Count;owned_STATE_bytes=$owned;maximum_cash_error_USDT=$maxCash;private_lock_body_read=$false}
