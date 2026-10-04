$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='1f40239706162eb92daa8a1e2fa0abb9b59299ed'
$release='docs/archive/MULTI_ASSET_WINTER_RELEASE_METADATA_20261004_V1'
$receipt='reports/GITHUB_MULTI_ASSET_WINTER_SOURCE_BINDING_20261004_V1.json'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read($p){if($p -eq (Join-Path $root 'state/dataset_lock.json')){throw 'Private policy is SHA-only'};if((Get-Item -LiteralPath $p).Length -gt 2000000){throw 'Small JSON only'};Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/') -or $p -match '(^|/)\.\.(/|$)'){throw 'Only owned STATE metadata'};Join-Path $state $p.Substring(24)}
function CopySmall($src,$rel){if((Get-Item -LiteralPath $src).Length -gt 2000000){throw 'Small metadata only'};$dst=Join-Path $root $rel;if(Test-Path -LiteralPath $dst){if((Hash $src) -ne (Hash $dst)){throw 'Existing bytes differ'}}else{Copy-Item -LiteralPath $src -Destination $dst}}
function GitHash($rel){
 $start=[Diagnostics.ProcessStartInfo]::new('git');$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
 $start.ArgumentList.Add('cat-file');$start.ArgumentList.Add('blob');$start.ArgumentList.Add('HEAD:'+$rel)
 $proc=[Diagnostics.Process]::Start($start);$bytes=[IO.MemoryStream]::new();$proc.StandardOutput.BaseStream.CopyTo($bytes);$err=$proc.StandardError.ReadToEnd();$proc.WaitForExit();if($proc.ExitCode -ne 0){throw $err};[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes.ToArray())).ToLowerInvariant()
}
if((git -C $root rev-parse HEAD) -ne $parent -or (Test-Path (Join-Path $root $receipt)) -or (Test-Path (Join-Path $root $release))){throw 'Exact parent and exclusive release required'}
$roles=[ordered]@{
 SOURCE_METADATA='MULTI_ASSET_WINTER_SOURCE_METADATA_20261004_V1'
 QA_METADATA_V2='MULTI_ASSET_WINTER_QA_METADATA_20261004_V2'
 INPUT='MULTI_ASSET_WINTER_INPUT_BINDING_20261004_V3'
 SOURCE='MULTI_ASSET_WINTER_MARKET_SOURCE_20261004_V1';QA_V2='MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V2'
 TWO_MARKET='MULTI_ASSET_WINTER_TWO_CONTROL_20261004_V3';EQUAL_MARKET='MULTI_ASSET_WINTER_TEN_EQUAL_20261004_V3';INVERSE_MARKET='MULTI_ASSET_WINTER_TEN_INVERSE_20261004_V3'
 TWO_INDEPENDENT='MULTI_ASSET_WINTER_TWO_CONTROL_INDEPENDENT_20261004_V1';EQUAL_INDEPENDENT='MULTI_ASSET_WINTER_TEN_EQUAL_INDEPENDENT_20261004_V1';INVERSE_INDEPENDENT='MULTI_ASSET_WINTER_TEN_INVERSE_INDEPENDENT_20261004_V1'
 POOL_COMPARISON='MULTI_ASSET_WINTER_POOL_COMPARISON_20261004_V1';ALLOCATION_COMPARISON='MULTI_ASSET_WINTER_ALLOCATION_COMPARISON_20261004_V1'
}
$closed=@{};$values=@{};$maxCash=0.;$maxRatio=0.;$mainBytes=0L;$cashCases=0
# Gate all actual outcomes first. The exporter does not certify its own live caller.
foreach($role in $roles.Keys){
 $rel='reports/fast_research/'+$roles[$role]+'.json';$r=Read (Join-Path $root $rel);$id=if($r.binding){$r.binding.task_id}else{$r.task_id}
 if($id -notmatch '^[0-9a-f]{32}$'){throw ('Actual task identity '+$role)}
 $tp=Join-Path $state ('task-progress/task-'+$id+'.json');$t=Read $tp
 if($t.id -ne $id -or $t.status -ne 'completed' -or $t.exit_code -ne 0 -or -not $t.ended_at){throw ('Actual closed0 required '+$role)}
 $metadataStatuses=@{SOURCE_METADATA='READY_FIXED_WINTER_SOURCE_PROTOCOL_NOT_DOWNLOADED_OR_ACCEPTED';QA_METADATA_V2='READY_D056_WINTER_QA_PROTOCOL_SOURCE_CLOSED0_QA_NOT_RUN';INPUT='BOUND_ACCEPTED_WINTER90_SOURCE_FOR_THREE_UNCHANGED_HOLD_RECIPES_NOT_MARKET_RESULTS'}
 if($metadataStatuses.ContainsKey($role) -and $r.status -ne $metadataStatuses[$role]){throw ('Actual metadata outcome required '+$role)}
 if($role -like '*MARKET'){
  if($r.status -ne 'COMPLETE_PREDECLARED_PORTFOLIO_CASES_NOT_CROSS_POOL_COMPARISON_OR_APR' -or $r.required_cases -ne 4 -or $r.completed_cases -ne 4 -or $r.complete_calendar_cases -ne 4 -or $r.calendar_complete_cases -ne 4 -or $r.actual_calendar_days -ne 90 -or $r.account_path -ne 'CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D' -or $r.initial_capital_per_comparison_account_USDT -ne 10000){throw 'Four complete winter90 shared-wallet calendars required'}
  if($r.candidate -ne 'NONE' -or $r.investment -ne 'CASH' -or $r.long_term_APR -ne 'NOT_EVALUABLE' -or $r.funding_unit_certified -ne $false -or $r.native_filters_certified -ne $false -or $r.orders_sent -ne 0 -or $r.GPU -ne 0 -or $r.locked_consumed -ne $false){throw 'Conditional development scope only'}
  if($r.terminal_cash_realized_cases -lt 0 -or $r.terminal_cash_realized_cases -gt 4 -or $r.marked_NAV_includes_unrealized -ne $true -or ($r.terminal_cash_realized_cases -lt 4 -and $r.liquidated_portfolio_return -ne 'NOT_EVALUABLE')){throw 'Truthful marked NAV versus liquidated return scope required'}
  foreach($c in $r.cases){if($c.summary.completed_minutes -ne 129600 -or $c.summary.required_minutes -ne 129600 -or $c.summary.daily_metrics.days -ne 90){throw 'No incomplete prefix promoted to full winter'}}
  $mainBytes += $r.owned_bytes;$cashCases += $r.terminal_cash_realized_cases
 }
 if($role -like '*INDEPENDENT'){
  if($r.status -ne 'PASS_CONFIGURED_N_SHARED_PERPETUAL_RECORDED_ACCOUNTING_AND_TARGET_SCOPE_NOT_NATIVE_OR_APR' -or $r.required_cases -ne 4 -or $r.completed_cases_verified -ne 4 -or $r.completed_full_calendar_cases_verified -ne 4 -or $r.financial_case_calls -ne 4 -or $r.incomplete_or_halted_cases_verified -ne 0 -or $r.tolerances.cash_USDT -ne 1e-7 -or $r.tolerances.ratio -ne 1e-10){throw 'Independent complete calendars and original financial tolerances required'}
  $ce=[double]$r.maximum_errors.cash;$re=[double]$r.maximum_errors.ratio
  if(-not [double]::IsFinite($ce) -or -not [double]::IsFinite($re) -or $ce -lt 0 -or $re -lt 0 -or $ce -gt 1e-7 -or $re -gt 1e-10){throw 'Actual finite independent errors required'}
  $maxCash=[Math]::Max($maxCash,$ce);$maxRatio=[Math]::Max($maxRatio,$re)
 }
 if($role -like '*COMPARISON' -and ($r.status -ne 'COMPLETE_SAVED_MULTI_ASSET_PAIRED_COMPARISON_NOT_APR' -or $r.pairs.Count -ne 4 -or $r.actual_days -ne 90 -or $r.initial_capital_USDT -ne 10000 -or $r.candidate -ne 'NONE' -or $r.investment -ne 'CASH' -or $r.long_term_APR -ne 'NOT_EVALUABLE')){throw 'Four saved complete-quarter money/risk contrasts required'}
 if($role -eq 'SOURCE' -and ($r.status -ne 'COMPLETE_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_PENDING_ACCEPTANCE' -or $r.actual_exit_code -ne 0 -or $r.source_only -ne $true -or $r.completed_source_files -ne 90 -or $r.new_market_files -ne 72 -or $r.reused_market_files -ne 18)){throw 'Source-only 72 new plus18 accepted descriptor reuse required'}
 if($role -eq 'QA_V2' -and ($r.status -ne 'PASS_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ONLY' -or $r.actual_exit_code -ne 0 -or $r.source_only -ne $true -or $r.completed_files -ne 90 -or $r.newly_verified_files -ne 72 -or $r.reused_accepted_files -ne 18 -or $r.prior_warmup_rows_QA_repeated -ne $false -or $r.prior_warmup_CRC_repeated -ne $false)){throw 'One first QA of72 plus18 accepted metadata, no repeated warm QA required'}
 $limit=if($role -like '*MARKET'){@{owned=250000000;rss=3000000000;wall=1800}}elseif($role -like '*INDEPENDENT'){@{owned=100000;rss=1500000000;wall=1800}}elseif($role -eq 'SOURCE'){@{owned=300000000;rss=1000000000;wall=1800}}elseif($role -eq 'QA_V2'){@{owned=5000000;rss=1000000000;wall=1200}}else{$null}
 if($role -eq 'TWO_MARKET'){$limit.owned=100000000}
 if($limit){
  $resourceKeys=if($role -eq 'QA_V2'){@('peak_RSS_bytes','elapsed_seconds')}else{@('owned_bytes','peak_RSS_bytes','elapsed_seconds')}
  foreach($key in $resourceKeys){if(-not $r.ContainsKey($key) -or -not [double]::IsFinite([double]$r[$key]) -or [double]$r[$key] -lt 0){throw ('Actual finite resource field '+$role+'/'+$key)}}
  $phaseOwned=if($role -eq 'QA_V2'){[long](Get-ChildItem -LiteralPath (StatePath $r.run_dir) -File -Recurse|Measure-Object -Property Length -Sum).Sum}else{$r.owned_bytes}
  if($phaseOwned -gt $limit.owned -or $r.peak_RSS_bytes -gt $limit.rss -or $r.elapsed_seconds -gt $limit.wall){throw ('Finite phase budget exceeded '+$role)}
  foreach($rs in @($r.resources_before,$r.resources_after)){if(-not $rs -or $rs.ram_limit_bytes -gt 5000000000 -or $rs.ram_current_bytes -gt 5000000000 -or $rs.swap_bytes -ne 0 -or $rs.gpu_used -ne $false){throw 'Original shared5GB/swap0/GPU0 resource scope required'}}
 }
 $values[$role]=@{report=$r;rel=$rel;task=$t;task_path=$tp;id=$id}
}
$manifestPath=Join-Path $state 'd056-multiasset-winter-source-acceptance-20261004-v2/INPUT_MANIFEST.json';$manifest=Read $manifestPath
if($manifest.status -ne 'PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS' -or $manifest.days -ne 90 -or $manifest.market_records.Count -ne 90 -or $manifest.daily_records.Count -ne 70 -or $manifest.warmup_minute_records.Count -ne 30 -or $manifest.normalized_source_hashes.Count -ne 190 -or $manifest.source_acceptance.sha256 -ne (Hash (Join-Path $root $values.QA_V2.rel)) -or $values.INPUT.report.manifest.sha256 -ne (Hash $manifestPath)){throw 'Actual accepted190 manifest must match QA and pre-account input binding'}
New-Item -ItemType Directory -Path (Join-Path $root $release)|Out-Null
foreach($role in $roles.Keys){
 $value=$values[$role];$r=$value.report;CopySmall $value.task_path ($release+'/'+$role+'-TASK.json')
 $proof=@{task_id=$value.id;actual_exit_code=0;report=$value.rel;report_sha256=Hash (Join-Path $root $value.rel);task_archive=$release+'/'+$role+'-TASK.json';task_sha256=Hash $value.task_path}
 if($r.run_dir){$rd=StatePath $r.run_dir;foreach($name in 'RUN_BINDING.json','ACTUAL_BINDING.json'){if(Test-Path -LiteralPath (Join-Path $rd $name)){CopySmall (Join-Path $rd $name) ($release+'/'+$role+'-'+$name)}}
  if($r.run_binding_sha256 -and (Hash (Join-Path $rd 'RUN_BINDING.json')) -ne $r.run_binding_sha256){throw 'Actual RUN_BINDING bytes changed'}
 }
 if($role -like '*INDEPENDENT'){$proof.maximum_errors=$r.maximum_errors;$proof.financial_calls=$r.financial_case_calls}
 $closed[$role]=$proof
}
foreach($entry in @{
 LOADER_STATIC_ONLY=@{id='0aa1afc1478948c8b88930b5f03333f5';exit=0}
 WINTER_BOUNDARY=@{id='3edf4581a4f145459686300f29c85896';exit=0}
 QA_STARTUP_FAILURE=@{id='1b5caa0e7bde427e99a607bf59d8b882';exit=1}
 QA_PRIOR_DESCRIPTOR_FAILURE=@{id='faae23f4c0404115a864b1a087b25902';exit=1}
 MAIN_METADATA_FAILURE=@{id='8f77bce420cc42f6a70f040c52b2673e';exit=1}
 INPUT_BOUNDARY_FAILURE=@{id='e56bc3a29c574a7eb2cc10c634468668';exit=1}
 REGISTRY_STARTUP_FAILURE=@{id='9a3e156302964250bdb3ad458f347d6f';exit=1}
}.GetEnumerator()){
 $tp=Join-Path $state ('task-progress/task-'+$entry.Value.id+'.json');$t=Read $tp;$expectedStatus=if($entry.Value.exit -eq 0){'completed'}else{'failed'}
 if($t.id -ne $entry.Value.id -or $t.status -ne $expectedStatus -or $t.exit_code -ne $entry.Value.exit -or -not $t.ended_at){throw ('Actual task closure required '+$entry.Key)}
 CopySmall $tp ($release+'/'+$entry.Key+'-TASK.json');$closed[$entry.Key]=@{task_id=$t.id;actual_exit_code=$t.exit_code;task_archive=$release+'/'+$entry.Key+'-TASK.json';task_sha256=Hash $tp}
}
CopySmall $manifestPath ($release+'/ACCEPTED-WINTER-INPUT_MANIFEST.json')
CopySmall (Join-Path $state 'd056-winter-loader-static-20261004-v1/AST_COMPILE_ONLY.json') ($release+'/AST-COMPILE-ONLY.json')
foreach($name in 'RUN_BINDING.json'){CopySmall (Join-Path $state ('d056-multiasset-winter-source-acceptance-20261004-v1/'+$name)) ($release+'/FAILED-QA-'+$name)}
CopySmall (Join-Path $state 'd056-winter-two-control-20261004-v1/RUN_BINDING.json') ($release+'/FAILED-INPUT-BOUNDARY-RUN_BINDING.json')
CopySmall (Join-Path $state 'd056-winter-two-control-20261004-v2/RUN_BINDING.json') ($release+'/FAILED-REGISTRY-STARTUP-RUN_BINDING.json')
CopySmall $PSCommandPath 'docs/archive/MULTI_ASSET_WINTER_RELEASE_EXPORTER_20261004_V1.ps1'
$metadataBytes=0L;foreach($f in (Get-ChildItem -LiteralPath (Join-Path $root $release) -File)){$metadataBytes += $f.Length};if($metadataBytes -gt 2000000){throw 'Dedicated metadata snapshot exceeds2MB; no market artifacts may be exported'}
$tracked=@('README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl','scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_source_acceptance.py','scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','scripts/investment/compare_multi_asset_portfolios.py','scripts/investment/multi_asset_official_transport.ps1')
$postproofs=@('reports/GITHUB_MULTI_ASSET_CONTINUOUS_SYNC_VERIFIED_20261004_V1.json','reports/GITHUB_MULTI_ASSET_CONTINUOUS_SYNC_VERIFIED_20261004_V2.json','reports/MULTI_ASSET_CONTINUOUS_FINAL_RESOURCE_20261004_V1.json')
$new=@(git -C $root ls-files --others --exclude-standard)|Where-Object {$_ -match '^(docs/archive|protocols|reports/fast_research|reports)/MULTI_ASSET_WINTER' -or $_ -eq 'tests/test_multi_asset_winter_quarter_20261004.py' -or $_ -in $postproofs}
$selected=@($tracked+$new+$postproofs|Sort-Object -Unique);$current=@{};foreach($rel in $selected){$current[$rel]=Hash (Join-Path $root $rel)}
$prior=@('AGENTS.md','scripts/investment/vol_managed_perpetual_target.py','scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_pool_target.py','scripts/investment/public_sma_daily.py','third_party/jesse_example_smacrossover/smacrossover_original.py','third_party/jesse_example_smacrossover/LICENSE','src/quant/perpetual_account.py','scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py','src/quant/resources.py','src/quant/execution_contract.py','scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py','tools/task_progress/task_progress_sample.py','environments/v8/uv.lock','docs/archive/APPEND_ONLY_REGISTRY_GIT_PREFLIGHT_SOURCE_20261003_V2.py','reports/fast_research/MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json','reports/fast_research/MULTI_ASSET_SOURCE_ACCEPTANCE_20261004_V2.json','reports/fast_research/MULTI_ASSET_OCTOBER_SOURCE_ACCEPTANCE_20261004_V1.json','reports/fast_research/MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_20261004_V2.json','reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json','reports/fast_research/PERPETUAL_303_SOURCE_INDEPENDENT_20261003_V1.json','reports/fast_research/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json')
$prior += @(git -C $root ls-files 'reports/fast_research/MULTI_ASSET_CONTINUOUS_*' 'protocols/MULTI_ASSET_CONTINUOUS_*' 'docs/archive/MULTI_ASSET_CONTINUOUS_*' 'reports/GITHUB_MULTI_ASSET_CONTINUOUS_*' 'reports/MULTI_ASSET_CONTINUOUS_*' 'tests/test_multi_asset_contin*')
$verified=@{};foreach($rel in ($prior|Sort-Object -Unique)){$d=Hash (Join-Path $root $rel);if($d -ne (GitHash $rel)){throw ('Prior evidence/helper changed '+$rel)};$verified[$rel]=$d}
$private=Hash (Join-Path $root 'state/dataset_lock.json');if($private -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private SHA guard'}
$ownedDirs=@(Get-ChildItem -LiteralPath $state -Directory|Where-Object {$_.Name -like 'd056-*'})
$owned=0L;foreach($dir in $ownedDirs){foreach($file in (Get-ChildItem -LiteralPath $dir.FullName -File -Recurse)){$owned += $file.Length}}
if($owned -gt 1000000000){throw 'D056 total new STATE budget exceeded'}
$v=@{status='CURRENT_MODULE_EXISTING_ACTUAL_ACCEPTANCE_BINDING_NOT_NEW_MARKET_REPLAY';parent_commit=$parent;source_hashes=$current;verified_prior_files=$verified;local_non_git_source_hashes=@{'state/dataset_lock.json'=$private};closed_actual_roles=$closed;selected_module_paths=$selected;new_account_cases=12;independent_cases=12;actual_calendar_days=90;account_path='CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D';maximum_cash_error_USDT=$maxCash;maximum_ratio_error=$maxRatio;main_output_bytes=$mainBytes;terminal_cash_realized_cases=$cashCases;marked_NAV_includes_unrealized=$true;owned_STATE_bytes=$owned;owned_STATE_dirs=@($ownedDirs.Name);release_metadata_bytes=$metadataBytes;new_source_files=72;accepted_source_descriptor_reuses=18;first_format_QA_files=72;accepted_warmup_hash_reuses=100;models_fit=0;old_QA_or_accounts_replayed=$false;investment='CASH';candidate='NONE';APR='NOT_EVALUABLE';funding_unit_certified=$false;native_certified=$false;exporter_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED';git_staging_performed=$false;created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
[IO.File]::WriteAllText((Join-Path $root $receipt),($v|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))
[PSCustomObject]@{receipt=$receipt;sha256=Hash (Join-Path $root $receipt);selected_paths=$selected.Count;closed_roles=$closed.Count;owned_STATE_bytes=$owned;release_metadata_bytes=$metadataBytes;private_lock_body_read=$false;git_staging_performed=$false}
