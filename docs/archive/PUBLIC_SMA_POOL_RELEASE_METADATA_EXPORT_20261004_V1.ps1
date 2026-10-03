$ErrorActionPreference='Stop'
$root='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$release='docs/archive/PUBLIC_SMA_POOL_RELEASE_USED_METADATA_20261004_V1'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/')){throw 'Only owned STATE metadata'};Join-Path $state $p.Substring(24)}
function CopySmall($src,$rel){if((Get-Item -LiteralPath $src).Length -gt 2000000){throw 'Small metadata only'};$dst=Join-Path $root $rel;if(Test-Path -LiteralPath $dst){throw 'Exclusive metadata archive'};Copy-Item -LiteralPath $src -Destination $dst}
function GitHash($rel){
 $start=[Diagnostics.ProcessStartInfo]::new('git');$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
 foreach($arg in @('cat-file','blob','HEAD:'+$rel)){$start.ArgumentList.Add($arg)}
 $proc=[Diagnostics.Process]::Start($start);$bytes=[IO.MemoryStream]::new();$proc.StandardOutput.BaseStream.CopyTo($bytes);$err=$proc.StandardError.ReadToEnd();$proc.WaitForExit();if($proc.ExitCode -ne 0){throw $err};[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes.ToArray())).ToLowerInvariant()
}
$parent='0a61e25b23b02475d3ebcb101b05813f2ef86ea5'
if((git -C $root rev-parse HEAD) -ne $parent){throw 'Current HEAD changed'}
$receipt='reports/GITHUB_PUBLIC_SMA_POOL_SOURCE_BINDING_20261004_V1.json'
if(Test-Path (Join-Path $root $receipt)){throw 'Exclusive source binding'}
New-Item -ItemType Directory -Path (Join-Path $root $release) -ErrorAction Stop|Out-Null
$roles=@{SYNTHETIC='PUBLIC_SMA_POOL_TARGET_SYNTHETIC';PROGRESS_SYNTHETIC='TASK_PROGRESS_STACK_SAMPLER_PUBLISHERS_SYNTHETIC';SEPTEMBER_MARKET='PUBLIC_SMA_POOL_SEPTEMBER';OCTOBER_MARKET='PUBLIC_SMA_POOL_OCTOBER';SEPTEMBER_COMPARISON='PUBLIC_SMA_POOL_SEPTEMBER_COMPARISON';OCTOBER_COMPARISON='PUBLIC_SMA_POOL_OCTOBER_COMPARISON';SEPTEMBER_INDEPENDENT='PUBLIC_SMA_POOL_SEPTEMBER_INDEPENDENT';OCTOBER_INDEPENDENT='PUBLIC_SMA_POOL_OCTOBER_INDEPENDENT'}
$closed=@{}
foreach($role in $roles.Keys){
 $rel='reports/fast_research/'+$roles[$role]+'_20261004_V1.json';$r=Read (Join-Path $root $rel)
 $id=if($r.binding){$r.binding.task_id}else{$r.task_id};$tp=Join-Path $state ('task-progress/task-'+$id+'.json');$t=Read $tp
 if($t.status -ne 'completed' -or $t.exit_code -ne 0){throw ('Actual closed0 required: '+$role)}
 if($role -like '*INDEPENDENT' -and ($r.completed_cases_verified -ne 4 -or $r.completed_full_calendar_cases_verified -ne 4 -or $r.maximum_errors.cash -gt 1e-7 -or $r.maximum_errors.ratio -gt 1e-10)){throw 'Independent original tolerance and four calendars required'}
 CopySmall $tp ($release+'/'+$role+'-TASK.json')
 $proof=@{task_id=$id;actual_exit_code=0;report=$rel;report_sha256=Hash (Join-Path $root $rel);task_archive=$release+'/'+$role+'-TASK.json';task_sha256=Hash $tp}
 if($r.run_dir){
   $rd=StatePath $r.run_dir;CopySmall (Join-Path $rd 'RUN_BINDING.json') ($release+'/'+$role+'-RUN_BINDING.json')
   if($role -like '*SYNTHETIC'){CopySmall (Join-Path $rd 'junit.xml') ($release+'/'+$role+'-JUNIT.xml')}
   if($role -like '*INDEPENDENT'){CopySmall (Join-Path $rd 'ACTUAL_BINDING.json') ($release+'/'+$role+'-ACTUAL_BINDING.json');$proof.maximum_errors=$r.maximum_errors;$proof.financial_calls=$r.financial_case_calls}
 }
 $closed[$role]=$proof
}
CopySmall (Join-Path $root '.cache/d053_bind_financial.ps1') 'docs/archive/PUBLIC_SMA_POOL_FINANCIAL_METADATA_BINDER_20261004_V1.ps1'
CopySmall $PSCommandPath 'docs/archive/PUBLIC_SMA_POOL_RELEASE_METADATA_EXPORT_20261004_V1.ps1'
$tracked=@('README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl','scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','scripts/investment/compare_multi_asset_portfolios.py','tools/task_progress/task_progress_sample.py')
$new=@(git -C $root ls-files --others --exclude-standard)|Where-Object {$_ -match '^(docs/archive|protocols|reports/fast_research)/(PUBLIC_SMA_POOL|TASK_PROGRESS_STACK_SAMPLER|TASK_PROGRESS_DISK_PUBLICATION_CORRECTION|OPEN_SOURCE_REGISTRY_PRE_PUBLIC_SMA_POOL)' -or $_ -in @('scripts/investment/public_sma_pool_target.py','tests/test_public_sma_pool_target.py','tests/test_task_progress_sampler_publishers.py','reports/GITHUB_MULTI_ASSET_INVERSE_VOL_SYNC_VERIFIED_20261004_V1.json')}
$selected=@($tracked+$new|Sort-Object -Unique)
$current=@{};foreach($rel in $selected){$current[$rel]=Hash (Join-Path $root $rel)}
$prior=@('AGENTS.md','scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_daily.py','scripts/investment/vol_managed_perpetual_target.py','third_party/jesse_example_smacrossover/smacrossover_original.py','third_party/jesse_example_smacrossover/LICENSE','src/quant/perpetual_account.py','scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py','scripts/investment/multi_asset_data.py','src/quant/resources.py','src/quant/execution_contract.py','scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py','scripts/research_v7/oracle_flow_ceiling.py','environments/v8/uv.lock','docs/archive/APPEND_ONLY_REGISTRY_GIT_PREFLIGHT_SOURCE_20261003_V2.py','reports/fast_research/MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json','reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json','reports/fast_research/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json','protocols/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json','protocols/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json')
$verified=@{};foreach($rel in $prior){$d=Hash (Join-Path $root $rel);if($d -ne (GitHash $rel)){throw ('Previously accepted bytes changed: '+$rel)};$verified[$rel]=$d}
$private=Hash (Join-Path $root 'state/dataset_lock.json');if($private -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private lock guard'}
$sma=Read (Join-Path $root 'reports/fast_research/PUBLIC_SMA_POOL_OCTOBER_20261004_V1.json')
if($sma.terminal_cash_realized_cases -ne 0 -or $sma.liquidated_portfolio_return -ne 'NOT_EVALUABLE'){throw 'Actual October terminal scope must remain NE'}
$v=@{status='CURRENT_MODULE_EXISTING_ACCEPTANCE_METADATA_BINDING_NOT_ADDITIONAL_MARKET_REPLAY';parent_commit=$parent;source_hashes=$current;verified_prior_files=$verified;local_non_git_source_hashes=@{'state/dataset_lock.json'=$private};closed_actual_roles=$closed;selected_module_paths=$selected;new_account_cases=8;independent_cases=8;models_fit=0;old_QA_or_accounts_replayed=$false;historical_source_reproduction='Old normal code via accepted Git0a61/abc901f/b00183d; current active source may differ without rewriting historical experiments';october_calendar_cases=4;october_cash_cases=0;october_liquidated_return='NOT_EVALUABLE';investment='CASH';candidate='NONE';APR='NOT_EVALUABLE';created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
[IO.File]::WriteAllText((Join-Path $root $receipt),($v|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))
git -C $root add -- @selected $receipt
if($LASTEXITCODE -ne 0){throw 'Exact module paths stage failed'}
[PSCustomObject]@{receipt=$receipt;sha256=Hash (Join-Path $root $receipt);selected_paths=$selected.Count;closed_roles=$closed.Count;private_lock_body_read=$false;October_cash_NE=$true}
