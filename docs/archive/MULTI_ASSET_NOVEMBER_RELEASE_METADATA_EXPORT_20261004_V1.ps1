$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='354967542958004c59a7f8e4b3d2fececf036b63'
$release='docs/archive/MULTI_ASSET_NOVEMBER_RELEASE_USED_METADATA_20261004_V1'
$receipt='reports/GITHUB_MULTI_ASSET_NOVEMBER_SOURCE_BINDING_20261004_V1.json'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/')){throw 'Only STATE metadata'};Join-Path $state $p.Substring(24)}
function CopySmall($src,$rel){if((Get-Item -LiteralPath $src).Length -gt 2000000){throw 'Small metadata only'};$dst=Join-Path $root $rel;if(Test-Path -LiteralPath $dst){if((Hash $src) -ne (Hash $dst)){throw 'Existing bytes differ'}}else{Copy-Item -LiteralPath $src -Destination $dst}}
function GitHash($rel){
 $start=[Diagnostics.ProcessStartInfo]::new('git');$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
 $start.ArgumentList.Add('cat-file');$start.ArgumentList.Add('blob');$start.ArgumentList.Add('HEAD:'+$rel)
 $proc=[Diagnostics.Process]::Start($start);$bytes=[IO.MemoryStream]::new();$proc.StandardOutput.BaseStream.CopyTo($bytes);$err=$proc.StandardError.ReadToEnd();$proc.WaitForExit();if($proc.ExitCode -ne 0){throw $err};[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes.ToArray())).ToLowerInvariant()
}
if((git -C $root rev-parse HEAD) -ne $parent -or (Test-Path (Join-Path $root $receipt))){throw 'Exact parent/exclusive binding'}
if(-not(Test-Path (Join-Path $root $release))){New-Item -ItemType Directory -Path (Join-Path $root $release)|Out-Null}
$roles=@{
 SOURCE='MULTI_ASSET_NOVEMBER_MARKET_SOURCE_20261004_V1';QA='MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_20261004_V2'
 TWO_MARKET='MULTI_ASSET_NOVEMBER_TWO_CONTROL_20261004_V1';EQUAL_MARKET='MULTI_ASSET_NOVEMBER_TEN_EQUAL_20261004_V1';INVERSE_MARKET='MULTI_ASSET_NOVEMBER_TEN_INVERSE_20261004_V1'
 TWO_INDEPENDENT='MULTI_ASSET_NOVEMBER_TWO_CONTROL_INDEPENDENT_20261004_V1';EQUAL_INDEPENDENT='MULTI_ASSET_NOVEMBER_TEN_EQUAL_INDEPENDENT_20261004_V1';INVERSE_INDEPENDENT='MULTI_ASSET_NOVEMBER_TEN_INVERSE_INDEPENDENT_20261004_V1'
 POOL_COMPARISON='MULTI_ASSET_NOVEMBER_POOL_COMPARISON_20261004_V1';ALLOCATION_COMPARISON='MULTI_ASSET_NOVEMBER_ALLOCATION_COMPARISON_20261004_V1'
 FAILURE_RESULT_REGISTRATION='MULTI_ASSET_NOVEMBER_STARTUP_FAILURE_REGISTRATION_20261004_V1'
}
$closed=@{}
foreach($role in $roles.Keys){
 $rel='reports/fast_research/'+$roles[$role]+'.json';$r=Read (Join-Path $root $rel);$id=if($r.binding){$r.binding.task_id}else{$r.task_id}
 $tp=Join-Path $state ('task-progress/task-'+$id+'.json');$t=Read $tp
 if($t.status -ne 'completed' -or $t.exit_code -ne 0){throw ('True closed0 required '+$role)}
 if($role -like '*MARKET' -and ($r.completed_cases -ne 4 -or $r.complete_calendar_cases -ne 4 -or $r.actual_calendar_days -ne 30)){throw 'Four complete November calendars required'}
 if($role -like '*INDEPENDENT' -and ($r.completed_cases_verified -ne 4 -or $r.completed_full_calendar_cases_verified -ne 4 -or $r.maximum_errors.cash -gt 1e-7 -or $r.maximum_errors.ratio -gt 1e-10)){throw 'Independent original tolerances/calendars'}
 CopySmall $tp ($release+'/'+$role+'-TASK.json')
 $proof=@{task_id=$id;actual_exit_code=0;report=$rel;report_sha256=Hash (Join-Path $root $rel);task_archive=$release+'/'+$role+'-TASK.json';task_sha256=Hash $tp}
 if($r.run_dir){$rd=StatePath $r.run_dir;CopySmall (Join-Path $rd 'RUN_BINDING.json') ($release+'/'+$role+'-RUN_BINDING.json');if($role -like '*INDEPENDENT'){CopySmall (Join-Path $rd 'ACTUAL_BINDING.json') ($release+'/'+$role+'-ACTUAL_BINDING.json');$proof.maximum_errors=$r.maximum_errors;$proof.financial_calls=$r.financial_case_calls}}
 $closed[$role]=$proof
}
$q=Read (Join-Path $root 'reports/fast_research/MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_20261004_V2.json')
if($q.newly_verified_files -ne 24 -or $q.reused_accepted_files -ne 6 -or $q.prior_warmup_rows_QA_repeated -ne $false -or $q.prior_warmup_CRC_repeated -ne $false){throw 'Only new24 QA, six accepted metadata reuses'}
CopySmall (Join-Path $state 'd054-multiasset-november-source-acceptance-20261004-v2/INPUT_MANIFEST.json') ($release+'/ACCEPTED-INPUT_MANIFEST.json')
CopySmall (Join-Path $root '.cache/d054_economics_metadata.ps1') 'docs/archive/MULTI_ASSET_NOVEMBER_ECONOMICS_METADATA_20261004_V1.ps1'
CopySmall (Join-Path $root '.cache/d054_record_startup_failure.py') 'docs/archive/MULTI_ASSET_NOVEMBER_STARTUP_FAILURE_REGISTRATION_SOURCE_20261004_V1.py'
CopySmall $PSCommandPath 'docs/archive/MULTI_ASSET_NOVEMBER_RELEASE_METADATA_EXPORT_20261004_V1.ps1'
$tracked=@('README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl','scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_official_transport.ps1','scripts/investment/multi_asset_source_acceptance.py','scripts/investment/multi_asset_financial_audit.py','scripts/investment/compare_multi_asset_portfolios.py')
$new=@(git -C $root ls-files --others --exclude-standard)|Where-Object {$_ -match '^(docs/archive|protocols|reports/fast_research)/MULTI_ASSET_NOVEMBER' -or $_ -eq 'reports/GITHUB_PUBLIC_SMA_POOL_SYNC_VERIFIED_20261004_V1.json'}
$selected=@($tracked+$new|Sort-Object -Unique);$current=@{};foreach($rel in $selected){$current[$rel]=Hash (Join-Path $root $rel)}
$prior=@('AGENTS.md','scripts/investment/multi_asset_portfolio.py','scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_daily.py','scripts/investment/public_sma_pool_target.py','scripts/investment/vol_managed_perpetual_target.py','third_party/jesse_example_smacrossover/smacrossover_original.py','third_party/jesse_example_smacrossover/LICENSE','src/quant/perpetual_account.py','scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py','src/quant/resources.py','src/quant/execution_contract.py','scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py','tools/task_progress/task_progress_sample.py','scripts/research_v7/oracle_flow_ceiling.py','environments/v8/uv.lock','docs/archive/APPEND_ONLY_REGISTRY_GIT_PREFLIGHT_SOURCE_20261003_V2.py','reports/fast_research/MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json','reports/fast_research/MULTI_ASSET_SOURCE_ACCEPTANCE_20261004_V2.json','reports/fast_research/MULTI_ASSET_OCTOBER_SOURCE_ACCEPTANCE_20261004_V1.json','reports/fast_research/MULTI_ASSET_TWO_CONTROL_REPAIRED_20261004.json','reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json','reports/fast_research/MULTI_ASSET_OCTOBER_TWO_CONTROL_20261004_V1.json','reports/fast_research/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json','reports/fast_research/MULTI_ASSET_INVERSE_VOL_SEPTEMBER_20261004_V1.json','reports/fast_research/MULTI_ASSET_INVERSE_VOL_OCTOBER_20261004_V1.json')
$verified=@{};foreach($rel in $prior){$d=Hash (Join-Path $root $rel);if($d -ne (GitHash $rel)){throw ('Prior evidence/helper changed '+$rel)};$verified[$rel]=$d}
$private=Hash (Join-Path $root 'state/dataset_lock.json');if($private -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private SHA guard'}
$v=@{status='CURRENT_MODULE_EXISTING_ACCEPTANCE_METADATA_BINDING_NOT_ADDITIONAL_MARKET_REPLAY';parent_commit=$parent;source_hashes=$current;verified_prior_files=$verified;local_non_git_source_hashes=@{'state/dataset_lock.json'=$private};closed_actual_roles=$closed;selected_module_paths=$selected;new_account_cases=12;independent_cases=12;new_recipes=0;models_fit=0;old_QA_or_accounts_replayed=$false;historical_source_reproduction='Normal code at Git354/0a61/abc/b001; immutable old reports preserved, active code may change';investment='CASH';candidate='NONE';APR='NOT_EVALUABLE';created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
[IO.File]::WriteAllText((Join-Path $root $receipt),($v|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))
git -C $root add -- @selected $receipt
if($LASTEXITCODE -ne 0){throw 'Exact module staging failed'}
[PSCustomObject]@{receipt=$receipt;sha256=Hash (Join-Path $root $receipt);selected_paths=$selected.Count;closed_roles=$closed.Count;private_lock_body_read=$false}
